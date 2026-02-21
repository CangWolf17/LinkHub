"""
模块 D: 自动化安装中枢 (Auto-Installer Router)

职责:
  - 接收前端拖拽上传的压缩包
  - 在白名单目录下创建专属文件夹并解压
  - 启发式寻址：扫描解压目录寻找核心可执行文件
  - 调用模块 C 生成软件描述
  - 调用模块 B 写入数据库
  - 将信息写入 ChromaDB 向量库供语义搜索

Pipeline: 接收文件 → 解压 → 启发式寻址 → LLM 描述 → 入库 → 返回结果
"""

import json
import logging
import os
import shutil
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    ALLOWED_EXECUTABLE_SUFFIXES,
    DEFAULT_ALLOWED_DIRS,
    EXE_PRIORITY_KEYWORDS,
)
from app.core.crypto import decrypt_value
from app.core.database import get_db
from app.core.vector_store import get_software_collection
from app.models.models import PortableSoftware, SystemSetting
from app.schemas.installer_schemas import InstallerUploadResponse, ScanDirsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/installer", tags=["Auto-Installer"])

# ── 内部工具函数 ─────────────────────────────────────────


async def _get_install_base_dir(db: AsyncSession) -> Path:
    """
    获取软件安装基础目录。
    优先使用 system_settings 中 allowed_dirs 的第一个目录。
    """
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == "allowed_dirs")
    )
    row = result.scalar_one_or_none()

    if row:
        try:
            dirs = json.loads(row)
            if isinstance(dirs, list) and dirs:
                return Path(dirs[0])
        except (json.JSONDecodeError, TypeError):
            pass

    return Path(DEFAULT_ALLOWED_DIRS[0])


def _extract_zip(archive_path: Path, target_dir: Path) -> None:
    """解压 zip 文件到目标目录。"""
    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(target_dir)


def _find_executables(directory: Path) -> list[Path]:
    """
    递归扫描目录下所有可执行文件。
    返回按优先级排序的列表。
    """
    executables: list[Path] = []

    for root, _dirs, files in os.walk(directory):
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() in ALLOWED_EXECUTABLE_SUFFIXES:
                executables.append(fpath)

    return executables


def _heuristic_pick(executables: list[Path], software_name: str) -> Path | None:
    """
    启发式算法选择核心可执行文件。

    优先级策略:
      1. 文件名包含软件名关键字（去空格、大小写不敏感）
      2. 文件名包含优先关键字（launcher, main, start, run, app）
      3. 位于根目录或第一层子目录（深度浅优先）
      4. 文件体积最大（通常是主程序）

    排除策略:
      - 排除 uninstall/uninst 相关文件
      - 排除 update/updater 相关文件
    """
    if not executables:
        return None

    # 排除明显的非主程序
    exclude_keywords = {"uninstall", "uninst", "update", "updater", "crash", "helper"}
    filtered = [
        e
        for e in executables
        if not any(kw in e.stem.lower() for kw in exclude_keywords)
    ]
    if not filtered:
        filtered = executables  # 如果全部被排除，回退到原始列表

    name_lower = (
        software_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    )

    def score(exe: Path) -> tuple[int, int, int]:
        """
        返回排序元组 (越大越优先):
          - 名称匹配分 (0-2)
          - 关键字匹配分 (0-1)
          - 文件大小 (越大越优先)
        """
        stem = exe.stem.lower().replace(" ", "").replace("-", "").replace("_", "")
        # 名称匹配
        name_score = 0
        if stem == name_lower:
            name_score = 2
        elif name_lower in stem or stem in name_lower:
            name_score = 1

        # 优先关键字匹配
        keyword_score = 1 if any(kw in stem for kw in EXE_PRIORITY_KEYWORDS) else 0

        # 文件大小
        try:
            size = exe.stat().st_size
        except OSError:
            size = 0

        return (name_score, keyword_score, size)

    filtered.sort(key=score, reverse=True)
    return filtered[0]


async def _generate_description_via_llm(
    software_name: str, exe_path: str, db: AsyncSession
) -> str:
    """
    尝试调用模块 C (LLM Gateway) 为软件生成描述。
    如果 LLM 未配置或调用失败，返回空字符串（不阻塞安装流程）。
    """
    try:
        # 加载 LLM 配置
        keys = ["llm_base_url", "llm_api_key", "model_chat"]
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key.in_(keys))
        )
        config = {row.key: row.value for row in result.scalars().all()}

        base_url = config.get("llm_base_url", "").strip()
        api_key = config.get("llm_api_key", "").strip()
        api_key = decrypt_value(api_key)  # 支持 DPAPI 加密值
        model = config.get("model_chat", "").strip()

        if not all([base_url, api_key, model]):
            logger.info("LLM 未配置，跳过描述生成")
            return ""

        from openai import OpenAI

        client = OpenAI(base_url=base_url, api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个软件知识助手。根据给出的软件名称和路径，"
                        "用简洁的中文（一两句话）描述这个软件的主要用途。"
                        "如果不认识这个软件，就根据名称合理推测。只返回描述文本。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"软件名称: {software_name}\n可执行文件路径: {exe_path}",
                },
            ],
            max_tokens=150,
            temperature=0.5,
        )

        if response.choices:
            desc = response.choices[0].message.content or ""
            logger.info("LLM 生成描述: %s -> %s", software_name, desc[:50])
            return desc.strip()

    except Exception as e:
        logger.warning("LLM 描述生成失败（非阻塞）: %s", e)

    return ""


def _index_to_chroma(software_id: str, name: str, description: str, path: str):
    """将软件信息写入 ChromaDB 向量索引。"""
    try:
        collection = get_software_collection()
        doc_text = f"{name}. {description}" if description else name
        collection.upsert(
            ids=[software_id],
            documents=[doc_text],
            metadatas=[
                {
                    "name": name,
                    "path": path,
                    "type": "software",
                }
            ],
        )
        logger.info("ChromaDB 索引更新: %s (%s)", name, software_id)
    except Exception as e:
        logger.warning("ChromaDB 索引失败（非阻塞）: %s", e)


# ── API 端点 ─────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=InstallerUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传压缩包并自动安装便携软件",
)
async def upload_and_install(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """
    完整 Pipeline:
      1. 接收上传的压缩包文件
      2. 在白名单目录下创建以软件名命名的文件夹
      3. 解压到该文件夹
      4. 启发式扫描寻找核心可执行文件
      5. 调用 LLM 生成描述（失败不阻塞）
      6. 写入 SQLite 数据库
      7. 写入 ChromaDB 向量索引
      8. 返回安装结果
    """
    # ── 1. 校验文件 ──────────────────────────────────────
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名为空",
        )

    filename = file.filename
    suffix = Path(filename).suffix.lower()

    if suffix != ".zip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前仅支持 .zip 格式，收到: {suffix}",
        )

    # 从文件名推断软件名（去除后缀）
    software_name = Path(filename).stem

    # ── 2. 确定安装目录并保存文件 ────────────────────────
    base_dir = await _get_install_base_dir(db)
    install_dir = base_dir / software_name

    # 如果目录已存在，添加数字后缀
    if install_dir.exists():
        counter = 1
        while (base_dir / f"{software_name}_{counter}").exists():
            counter += 1
        install_dir = base_dir / f"{software_name}_{counter}"
        software_name = f"{software_name}_{counter}"

    # 创建临时文件保存上传内容
    temp_archive = base_dir / f"_temp_{filename}"
    try:
        # 确保基础目录存在
        base_dir.mkdir(parents=True, exist_ok=True)

        # 保存上传文件
        with open(temp_archive, "wb") as f:
            content = await file.read()
            f.write(content)

        # ── 3. 解压 ─────────────────────────────────────
        install_dir.mkdir(parents=True, exist_ok=True)

        try:
            _extract_zip(temp_archive, install_dir)
        except zipfile.BadZipFile:
            # 清理
            shutil.rmtree(install_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的 ZIP 文件",
            )

        # 处理单层嵌套目录（zip 内只有一个顶层文件夹的情况）
        children = list(install_dir.iterdir())
        if len(children) == 1 and children[0].is_dir():
            nested = children[0]
            # 将嵌套目录的内容移动到 install_dir
            for item in nested.iterdir():
                target = install_dir / item.name
                shutil.move(str(item), str(target))
            nested.rmdir()

        # ── 4. 启发式寻址 ───────────────────────────────
        executables = _find_executables(install_dir)

        if not executables:
            # 没找到可执行文件，仍然创建记录但标注
            exe_path_str = ""
            exe_candidates = []
        else:
            best_exe = _heuristic_pick(executables, software_name)
            exe_path_str = str(best_exe) if best_exe else str(executables[0])
            exe_candidates = [str(e) for e in executables[:20]]

        # ── 5. LLM 描述生成（非阻塞） ──────────────────
        description = await _generate_description_via_llm(
            software_name, exe_path_str, db
        )

        # ── 6. 写入 SQLite ──────────────────────────────
        item = PortableSoftware(
            name=software_name,
            executable_path=exe_path_str,
            description=description or None,
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        await db.commit()

        logger.info(
            "安装完成: %s -> %s (exe: %s)",
            filename,
            install_dir,
            exe_path_str,
        )

        # ── 7. 写入 ChromaDB 向量索引 ───────────────────
        _index_to_chroma(item.id, software_name, description, exe_path_str)

        # ── 8. 返回结果 ─────────────────────────────────
        return InstallerUploadResponse(
            success=True,
            software_id=item.id,
            name=software_name,
            executable_path=exe_path_str,
            install_dir=str(install_dir),
            description=description,
            exe_candidates=exe_candidates,
            message="安装完成"
            if exe_path_str
            else "安装完成（未找到可执行文件，请手动指定）",
        )

    except HTTPException:
        raise
    except Exception as e:
        # 清理可能创建的目录
        if install_dir.exists():
            shutil.rmtree(install_dir, ignore_errors=True)
        logger.error("安装失败: %s -> %s", filename, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"安装失败: {e}",
        )
    finally:
        # 清理临时文件
        if temp_archive.exists():
            try:
                temp_archive.unlink()
            except OSError:
                pass


# ── 扫描导入端点 ─────────────────────────────────────────


@router.post(
    "/scan-dirs",
    response_model=ScanDirsResponse,
    summary="扫描白名单目录，导入已有便携软件",
)
async def scan_and_import(
    db: AsyncSession = Depends(get_db),
):
    """
    遍历 system_settings 中 allowed_dirs 配置的所有白名单目录。
    将每个一级子目录视为一个独立软件，使用启发式算法寻找主可执行文件并写入数据库。

    规则:
      - 仅处理直接子目录（不递归跨目录）
      - 若 executable_path 已存在于数据库，跳过（去重）
      - LLM 描述生成为非阻塞可选步骤
      - 同时更新 ChromaDB 向量索引
    """
    # 读取白名单目录列表
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    scan_dirs: list[Path] = []
    if setting and setting.value:
        try:
            raw = json.loads(setting.value)
            if isinstance(raw, list):
                scan_dirs = [Path(d) for d in raw if d]
        except (json.JSONDecodeError, TypeError):
            pass
    if not scan_dirs:
        scan_dirs = [Path(d) for d in DEFAULT_ALLOWED_DIRS]

    # 读取数据库中已有的所有 executable_path，用于去重
    existing_result = await db.execute(select(PortableSoftware.executable_path))
    existing_paths: set[str] = {row for row in existing_result.scalars().all() if row}

    imported = 0
    skipped = 0
    failed = 0
    details: list[dict] = []

    for base_dir in scan_dirs:
        if not base_dir.exists() or not base_dir.is_dir():
            logger.info("白名单目录不存在，跳过: %s", base_dir)
            continue

        # 遍历一级子目录，每个子目录视为一个软件
        for subdir in sorted(base_dir.iterdir()):
            if not subdir.is_dir():
                continue

            software_name = subdir.name

            try:
                # 启发式寻找可执行文件
                executables = _find_executables(subdir)
                if not executables:
                    # 子目录内没有可执行文件，尝试将子目录本身作为记录（路径为目录）
                    exe_path_str = ""
                else:
                    best = _heuristic_pick(executables, software_name)
                    exe_path_str = str(best) if best else str(executables[0])

                # 去重：若路径已在数据库，跳过
                if exe_path_str and exe_path_str in existing_paths:
                    skipped += 1
                    details.append(
                        {"name": software_name, "status": "skipped", "reason": "已存在"}
                    )
                    continue

                # 按名称去重：若同名软件已存在，也跳过
                name_check = await db.execute(
                    select(PortableSoftware).where(
                        PortableSoftware.name == software_name
                    )
                )
                if name_check.scalar_one_or_none() is not None:
                    skipped += 1
                    details.append(
                        {
                            "name": software_name,
                            "status": "skipped",
                            "reason": "同名已存在",
                        }
                    )
                    continue

                # LLM 描述（非阻塞）
                description = await _generate_description_via_llm(
                    software_name, exe_path_str or str(subdir), db
                )

                # 写入 SQLite
                item = PortableSoftware(
                    name=software_name,
                    executable_path=exe_path_str,
                    description=description or None,
                )
                db.add(item)
                await db.flush()
                await db.refresh(item)
                await db.commit()

                # 写入 ChromaDB
                _index_to_chroma(item.id, software_name, description, exe_path_str)

                existing_paths.add(exe_path_str)
                imported += 1
                details.append(
                    {
                        "name": software_name,
                        "status": "imported",
                        "executable_path": exe_path_str,
                        "description": description,
                    }
                )
                logger.info("扫描导入: %s -> %s", software_name, exe_path_str)

            except Exception as e:
                failed += 1
                details.append(
                    {"name": software_name, "status": "failed", "reason": str(e)}
                )
                logger.warning("扫描导入失败: %s -> %s", software_name, e)

    return ScanDirsResponse(
        success=True,
        imported=imported,
        skipped=skipped,
        failed=failed,
        details=details,
        message=f"扫描完成：新导入 {imported} 个，跳过 {skipped} 个，失败 {failed} 个",
    )
