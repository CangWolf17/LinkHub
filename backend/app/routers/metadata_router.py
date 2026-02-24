"""
模块 B: 元数据与死链管理 (Metadata CRUD Router)

职责:
  - 便携软件 (PortableSoftware) 的增删改查
  - 工作区 (Workspace) 的增删改查
  - GET 列表时对路径执行 os.path.exists() 死链检测，标记 is_missing
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DIR_TYPE_WORKSPACE, filter_dirs_by_type, parse_allowed_dirs
from app.core.database import get_db
from app.core.llm_helpers import get_async_openai_client, load_llm_config
from app.models.models import PortableSoftware, SystemSetting, Workspace
from app.schemas.metadata_schemas import (
    AiFillFormRequest,
    AiFillFormResponse,
    GenerateDescriptionRequest,
    GenerateDescriptionResponse,
    SoftwareCreate,
    SoftwareListResponse,
    SoftwareResponse,
    SoftwareUpdate,
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceScanResponse,
    WorkspaceUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["Metadata CRUD"])


# ── 内部工具函数 ─────────────────────────────────────────


def _collect_dir_context(dir_path: Path, max_files: int = 30) -> str:
    """
    收集目录上下文信息供 LLM 推断软件/项目用途:
      - 顶层文件列表（最多 max_files 个）
      - README / LICENSE 等文件的前几行
    """
    if not dir_path.is_dir():
        return ""

    lines: list[str] = []

    # 收集一级文件/目录列表
    try:
        entries = sorted(
            dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())
        )
        file_list = []
        for entry in entries[:max_files]:
            prefix = "[DIR]" if entry.is_dir() else f"[{entry.suffix or 'file'}]"
            file_list.append(f"  {prefix} {entry.name}")
        if len(entries) > max_files:
            file_list.append(f"  ... 共 {len(entries)} 项")
        if file_list:
            lines.append("目录内容:")
            lines.extend(file_list)
    except OSError:
        pass

    # 尝试读取 README 等描述文件
    readme_names = [
        "README.md",
        "README.txt",
        "README",
        "readme.md",
        "readme.txt",
        "DESCRIPTION",
        "description.txt",
        "package.json",
        "setup.py",
        "pyproject.toml",
        "Cargo.toml",
        "pom.xml",
    ]
    for name in readme_names:
        readme_path = dir_path / name
        if readme_path.is_file():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="ignore")[:500]
                lines.append(f"\n{name} 内容 (前500字):")
                lines.append(content.strip())
                break  # 只取第一个找到的
            except OSError:
                pass

    return "\n".join(lines)


def _check_path_missing(path_str: str) -> bool:
    """轻量级死链检测: 检查本地路径是否已失效。"""
    try:
        return not Path(path_str).exists()
    except (OSError, ValueError):
        return True


def _to_software_response(item: PortableSoftware) -> SoftwareResponse:
    """将 ORM 对象转换为响应模型，附加 is_missing / exe_exists / dir_exists 标记。"""
    exe_path = item.executable_path
    install_dir = item.install_dir

    # 判断 exe 是否存在
    exe_exists = not _check_path_missing(exe_path) if exe_path else False

    # 判断安装目录是否存在
    if install_dir:
        dir_exists = not _check_path_missing(install_dir)
    elif exe_path:
        # 没有 install_dir 时，用 exe 路径的父目录
        try:
            dir_exists = Path(exe_path).parent.exists()
        except (OSError, ValueError):
            dir_exists = False
    else:
        dir_exists = False

    # is_missing 仅在 exe 不存在 且 目录也不存在时为 True（完全失效）
    is_missing = not exe_exists and not dir_exists

    return SoftwareResponse(
        id=item.id,
        name=item.name,
        executable_path=item.executable_path,
        install_dir=item.install_dir,
        description=item.description,
        tags=item.tags,
        icon_path=item.icon_path,
        is_missing=is_missing,
        exe_exists=exe_exists,
        dir_exists=dir_exists,
        last_used_at=item.last_used_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_workspace_response(item: Workspace) -> WorkspaceResponse:
    """将 ORM 对象转换为响应模型，附加 is_missing 标记。"""
    return WorkspaceResponse(
        id=item.id,
        name=item.name,
        directory_path=item.directory_path,
        description=item.description,
        deadline=item.deadline,
        status=item.status,
        is_missing=_check_path_missing(item.directory_path),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# ══════════════════════════════════════════════════════════
#  便携软件 CRUD
# ══════════════════════════════════════════════════════════


@router.post(
    "/software",
    response_model=SoftwareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建便携软件记录",
)
async def create_software(
    req: SoftwareCreate,
    db: AsyncSession = Depends(get_db),
):
    """新增一条便携软件记录到数据库。"""
    item = PortableSoftware(
        name=req.name,
        executable_path=req.executable_path,
        install_dir=req.install_dir,
        description=req.description,
        tags=req.tags,
        icon_path=req.icon_path,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("创建软件记录: %s (%s)", item.name, item.id)
    return _to_software_response(item)


@router.get(
    "/software",
    response_model=SoftwareListResponse,
    summary="获取便携软件列表",
)
async def list_software(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(50, ge=1, le=9999, description="每页数量"),
    search: str | None = Query(None, description="按名称模糊搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取便携软件列表，返回时自动检测死链。"""
    query = select(PortableSoftware)

    if search:
        query = query.where(PortableSoftware.name.ilike(f"%{search}%"))

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询
    query = query.order_by(PortableSoftware.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return SoftwareListResponse(
        items=[_to_software_response(item) for item in items],
        total=total,
    )


@router.post(
    "/software/batch-delete",
    summary="批量删除软件记录（仅数据库记录）",
)
async def batch_delete_software(
    req: dict,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 列表批量删除软件记录，不删除本地文件。"""
    ids: list[str] = req.get("ids", [])
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ids 不能为空"
        )

    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id.in_(ids))
    )
    items = result.scalars().all()

    deleted = []
    for item in items:
        deleted.append({"id": item.id, "name": item.name})
        await db.delete(item)

    await db.commit()
    logger.info("批量删除软件: %d 条", len(deleted))
    return {"deleted_count": len(deleted), "deleted": deleted}


@router.delete(
    "/software/cleanup/dead-links",
    summary="批量清理死链软件记录",
)
async def cleanup_dead_software(
    db: AsyncSession = Depends(get_db),
):
    """扫描所有软件记录，删除路径已失效的条目。"""
    result = await db.execute(select(PortableSoftware))
    items = result.scalars().all()

    removed = []
    for item in items:
        # 使用 executable_path 检测死链，若为空则用 install_dir
        check_path = item.executable_path or item.install_dir
        if check_path and _check_path_missing(check_path):
            removed.append({"id": item.id, "name": item.name, "path": check_path})
            await db.delete(item)

    await db.commit()
    logger.info("清理死链软件: 共 %d 条", len(removed))
    return {"removed_count": len(removed), "removed": removed}


@router.get(
    "/software/{software_id}",
    response_model=SoftwareResponse,
    summary="获取单个便携软件详情",
)
async def get_software(
    software_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取单个便携软件，附带死链检测。"""
    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    return _to_software_response(item)


@router.put(
    "/software/{software_id}",
    response_model=SoftwareResponse,
    summary="更新便携软件记录",
)
async def update_software(
    software_id: str,
    req: SoftwareUpdate,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 更新便携软件记录（仅更新非 None 字段）。"""
    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("更新软件记录: %s (%s)", item.name, item.id)
    return _to_software_response(item)


@router.delete(
    "/software/{software_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除便携软件记录",
)
async def delete_software(
    software_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 删除便携软件记录。"""
    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    await db.delete(item)
    await db.commit()
    logger.info("删除软件记录: %s (%s)", item.name, item.id)


# ── 软件 LLM 描述生成 ───────────────────────────────────


@router.post(
    "/software/{software_id}/generate-description",
    response_model=GenerateDescriptionResponse,
    summary="使用 LLM 为软件生成描述",
)
async def generate_software_description(
    software_id: str,
    req: GenerateDescriptionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    调用 LLM 根据软件名称和路径信息生成简短描述，并保存到数据库。
    支持自定义 prompt。
    """
    # 查找软件
    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    # 加载 LLM 配置
    config = await load_llm_config(db)
    client = get_async_openai_client(config)
    model = config.get("model_chat", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_chat 为空。",
        )

    # 构建 prompt — 收集目录上下文丰富 LLM 输入
    exe_path = Path(item.executable_path) if item.executable_path else None
    dir_context = ""
    if exe_path:
        dir_context = _collect_dir_context(exe_path.parent)
    elif item.install_dir:
        dir_context = _collect_dir_context(Path(item.install_dir))

    custom_prompt = req.custom_prompt if req and req.custom_prompt else None
    prompt_mode = req.mode if req else "append"
    context_block = f"\n\n目录文件信息:\n{dir_context}" if dir_context else ""

    if custom_prompt:
        user_content = (
            f"软件名称: {item.name}\n"
            f"可执行文件路径: {item.executable_path}"
            f"{context_block}\n\n"
            f"用户要求: {custom_prompt}"
        )
    else:
        user_content = (
            f"软件名称: {item.name}\n"
            f"可执行文件路径: {item.executable_path}"
            f"{context_block}"
        )

    system_prompt = config.get("llm_system_prompt_software", "").strip()
    if not system_prompt:
        system_prompt = (
            "你是一个软件描述助手。根据提供的软件名称、路径和目录文件列表信息，"
            "推断该软件的用途，生成一段简洁的中文描述（1-2句话），说明该软件的用途和特点。"
            "只返回描述文本，不要附加任何解释、标点符号列表或前缀。"
        )

    # 根据 mode 处理自定义 prompt: override=覆盖 system_prompt, append=追加
    if custom_prompt and prompt_mode == "override":
        system_prompt = custom_prompt

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    logger.info(
        "[LLM-REQ] 软件描述生成 | model=%s | name=%s | user_content 长度=%d",
        model,
        item.name,
        len(user_content),
    )
    logger.debug("[LLM-REQ] system_prompt: %s", system_prompt)
    logger.debug("[LLM-REQ] user_content: %s", user_content)

    try:
        max_tokens = int(config.get("llm_max_tokens", "1024"))
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens,
        )

        # 详细记录 LLM 响应便于排查
        raw = (
            response.model_dump() if hasattr(response, "model_dump") else str(response)
        )
        logger.info(
            "[LLM-RES] 软件描述 | model=%s | choices=%d | finish_reason=%s",
            getattr(response, "model", model),
            len(response.choices) if response.choices else 0,
            response.choices[0].finish_reason if response.choices else "N/A",
        )
        logger.debug("[LLM-RES] raw_response: %s", raw)

        description = ""
        if response.choices:
            msg = response.choices[0].message
            description = (msg.content or "").strip()
            # 推理模型 (如 GLM-4, DeepSeek-R1) 可能将内容放在 reasoning_content 中
            if not description:
                reasoning = getattr(msg, "reasoning_content", None) or ""
                if reasoning:
                    logger.info(
                        "[LLM-FALLBACK] 软件描述 | content 为空，尝试从 reasoning_content 提取 | reasoning 长度=%d",
                        len(reasoning),
                    )
                    # reasoning_content 是思维链，取最后一段作为结果的近似值
                    # 但更好的做法是提示用户模型输出异常
                    description = ""

        if not description:
            logger.warning(
                "[LLM-EMPTY] 软件描述 | name=%s | finish_reason=%s | choices=%s",
                item.name,
                response.choices[0].finish_reason if response.choices else "N/A",
                raw,
            )
            hint = ""
            if response.choices and response.choices[0].finish_reason == "length":
                hint = "（模型输出被截断，可能是推理模型消耗了所有 token，建议更换非推理模型或增大 token 限制）"
            reasoning_preview = ""
            if response.choices:
                rc = (
                    getattr(response.choices[0].message, "reasoning_content", None)
                    or ""
                )
                if rc:
                    reasoning_preview = f" | reasoning_content 前200字: {rc[:200]}"
            return GenerateDescriptionResponse(
                success=False,
                description="",
                model=model,
                message=f"LLM 返回了空内容{hint}{reasoning_preview}",
            )

        # 保存到数据库
        item.description = description
        item.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(item)
        await db.commit()

        logger.info("LLM 生成软件描述: %s -> %s", item.name, description[:50])
        return GenerateDescriptionResponse(
            success=True,
            description=description,
            model=response.model or model,
            message="描述生成成功",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM 生成软件描述失败: %s -> %s", item.name, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 调用失败: {e}",
        )


@router.post(
    "/software/{software_id}/generate-tags",
    summary="使用 LLM 为软件生成类型标签",
)
async def generate_software_tags(
    software_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    调用 LLM 根据软件名称、描述和路径信息推断软件类型标签。
    返回 JSON 数组字符串并保存到数据库。
    """
    import json as _json

    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    config = await load_llm_config(db)
    client = get_async_openai_client(config)
    model = config.get("model_chat", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_chat 为空。",
        )

    exe_path = Path(item.executable_path) if item.executable_path else None
    dir_context = ""
    if exe_path:
        dir_context = _collect_dir_context(exe_path.parent)
    elif item.install_dir:
        dir_context = _collect_dir_context(Path(item.install_dir))

    context_block = f"\n\n目录文件信息:\n{dir_context}" if dir_context else ""

    user_content = (
        f"软件名称: {item.name}\n"
        f"软件描述: {item.description or '无'}\n"
        f"可执行文件路径: {item.executable_path or '无'}"
        f"{context_block}"
    )

    system_prompt = (
        "你是一个软件分类助手。根据提供的软件信息，为它分配1-3个类型标签。"
        "标签应该简洁，如：开发工具、文本编辑器、图像处理、网络工具、系统工具、"
        "多媒体、浏览器、压缩工具、下载工具、数据库工具、IDE、终端工具、"
        "文件管理、安全工具、科学计算、游戏、办公软件等。"
        '只返回一个 JSON 数组，例如 ["开发工具", "文本编辑器"]，不要附加任何解释。'
    )

    try:
        max_tokens = int(config.get("llm_max_tokens", "256"))
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=min(max_tokens, 256),
        )

        tags_str = ""
        if response.choices:
            raw_content = (response.choices[0].message.content or "").strip()
            # 尝试提取 JSON 数组
            try:
                tags = _json.loads(raw_content)
                if isinstance(tags, list):
                    tags_str = _json.dumps(tags, ensure_ascii=False)
            except _json.JSONDecodeError:
                # 尝试从文本中提取 [...] 部分
                import re

                match = re.search(r"\[.*?\]", raw_content, re.DOTALL)
                if match:
                    try:
                        tags = _json.loads(match.group())
                        if isinstance(tags, list):
                            tags_str = _json.dumps(tags, ensure_ascii=False)
                    except _json.JSONDecodeError:
                        pass

        if not tags_str:
            return {"success": False, "tags": "", "message": "LLM 未返回有效标签"}

        item.tags = tags_str
        item.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(item)
        await db.commit()

        logger.info("LLM 生成软件标签: %s -> %s", item.name, tags_str)
        return {"success": True, "tags": tags_str, "message": "标签生成成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM 生成软件标签失败: %s -> %s", item.name, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 调用失败: {e}",
        )


# ══════════════════════════════════════════════════════════
#  工作区 CRUD
# ══════════════════════════════════════════════════════════


@router.post(
    "/workspaces",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建工作区记录",
)
async def create_workspace(
    req: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
):
    """新增一条工作区记录到数据库。"""
    item = Workspace(
        name=req.name,
        directory_path=req.directory_path,
        description=req.description,
        deadline=req.deadline,
        status=req.status,
    )
    if req.created_at is not None:
        item.created_at = req.created_at
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("创建工作区: %s (%s)", item.name, item.id)
    return _to_workspace_response(item)


@router.get(
    "/workspaces",
    response_model=WorkspaceListResponse,
    summary="获取工作区列表",
)
async def list_workspaces(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(50, ge=1, le=9999, description="每页数量"),
    search: str | None = Query(None, description="按名称模糊搜索"),
    status_filter: str | None = Query(None, alias="status", description="按状态过滤"),
    db: AsyncSession = Depends(get_db),
):
    """获取工作区列表，返回时自动检测死链。"""
    query = select(Workspace)

    if search:
        query = query.where(Workspace.name.ilike(f"%{search}%"))
    if status_filter:
        query = query.where(Workspace.status == status_filter)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询
    query = query.order_by(Workspace.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return WorkspaceListResponse(
        items=[_to_workspace_response(item) for item in items],
        total=total,
    )


# ── 工作区静态路由（必须在 {workspace_id} 之前注册） ──────


@router.post(
    "/workspaces/batch-delete",
    summary="批量删除工作区记录（仅数据库记录）",
)
async def batch_delete_workspaces(
    req: dict,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 列表批量删除工作区记录，不删除本地文件。"""
    ids: list[str] = req.get("ids", [])
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ids 不能为空"
        )

    result = await db.execute(select(Workspace).where(Workspace.id.in_(ids)))
    items = result.scalars().all()

    deleted = []
    for item in items:
        deleted.append({"id": item.id, "name": item.name})
        await db.delete(item)

    await db.commit()
    logger.info("批量删除工作区: %d 条", len(deleted))
    return {"deleted_count": len(deleted), "deleted": deleted}


@router.post(
    "/workspaces/batch-update-status",
    summary="批量更新工作区状态",
)
async def batch_update_workspace_status(
    req: dict,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 列表批量更新工作区状态。"""
    ids: list[str] = req.get("ids", [])
    new_status: str = req.get("status", "")
    valid_statuses = {"not_started", "active", "completed", "archived"}

    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ids 不能为空"
        )
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效状态: {new_status}，允许值: {valid_statuses}",
        )

    result = await db.execute(select(Workspace).where(Workspace.id.in_(ids)))
    items = result.scalars().all()

    updated = []
    now = datetime.now(timezone.utc)
    for item in items:
        item.status = new_status
        item.updated_at = now
        updated.append({"id": item.id, "name": item.name})

    await db.commit()
    logger.info("批量更新工作区状态 -> %s: %d 条", new_status, len(updated))
    return {"updated_count": len(updated), "status": new_status, "updated": updated}


@router.delete(
    "/workspaces/cleanup/dead-links",
    summary="批量清理死链工作区记录",
)
async def cleanup_dead_workspaces(
    db: AsyncSession = Depends(get_db),
):
    """扫描所有工作区记录，删除目录已失效的条目。"""
    result = await db.execute(select(Workspace))
    items = result.scalars().all()

    removed = []
    for item in items:
        if _check_path_missing(item.directory_path):
            removed.append(
                {"id": item.id, "name": item.name, "path": item.directory_path}
            )
            await db.delete(item)

    await db.commit()
    logger.info("清理死链工作区: 共 %d 条", len(removed))
    return {"removed_count": len(removed), "removed": removed}


@router.post(
    "/workspaces/scan",
    response_model=WorkspaceScanResponse,
    summary="扫描目录，批量导入已有工作区",
)
async def scan_workspaces(
    db: AsyncSession = Depends(get_db),
):
    """
    遍历 system_settings 中 allowed_dirs 配置的所有工作区目录（type=workspace）。
    将每个一级子目录视为一个独立工作区导入（状态默认 active）。

    规则:
      - 仅扫描 type=workspace 的目录
      - 仅扫描直接子目录
      - 若 directory_path 已存在于数据库，跳过
      - 若同名工作区已存在，跳过
    """
    # 读取白名单目录列表，仅取 type=workspace
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    entries = parse_allowed_dirs(setting.value if setting else "")
    scan_dirs = filter_dirs_by_type(entries, DIR_TYPE_WORKSPACE)

    if not scan_dirs:
        return WorkspaceScanResponse(
            success=True,
            imported=0,
            skipped=0,
            details=[],
            message="未配置工作区目录（type=workspace），请先在设置中配置",
        )

    # 读取数据库中已有的 directory_path
    existing_result = await db.execute(select(Workspace.directory_path))
    existing_paths: set[str] = {r for r in existing_result.scalars().all() if r}

    imported = 0
    skipped = 0
    details: list[dict] = []

    for base_dir in scan_dirs:
        if not base_dir.exists() or not base_dir.is_dir():
            continue

        for subdir in sorted(base_dir.iterdir()):
            if not subdir.is_dir():
                continue

            dir_path_str = str(subdir)
            ws_name = subdir.name

            # 路径去重
            if dir_path_str in existing_paths:
                skipped += 1
                details.append(
                    {"name": ws_name, "status": "skipped", "reason": "路径已存在"}
                )
                continue

            # 同名去重
            name_check = await db.execute(
                select(Workspace).where(Workspace.name == ws_name)
            )
            if name_check.scalar_one_or_none() is not None:
                skipped += 1
                details.append(
                    {"name": ws_name, "status": "skipped", "reason": "同名已存在"}
                )
                continue

            try:
                item = Workspace(
                    name=ws_name,
                    directory_path=dir_path_str,
                    status="active",
                )
                db.add(item)
                await db.flush()
                await db.commit()

                existing_paths.add(dir_path_str)
                imported += 1
                details.append(
                    {"name": ws_name, "status": "imported", "path": dir_path_str}
                )
                logger.info("工作区扫描导入: %s", dir_path_str)
            except Exception as e:
                await db.rollback()
                skipped += 1
                details.append({"name": ws_name, "status": "skipped", "reason": str(e)})
                logger.warning("工作区导入失败: %s -> %s", ws_name, e)

    return WorkspaceScanResponse(
        success=True,
        imported=imported,
        skipped=skipped,
        details=details,
        message=f"扫描完成：新导入 {imported} 个工作区，跳过 {skipped} 个",
    )


# ── 工作区动态路由（{workspace_id}） ─────────────────────


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="获取单个工作区详情",
)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取单个工作区，附带死链检测。"""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作区记录不存在: {workspace_id}",
        )

    return _to_workspace_response(item)


@router.put(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="更新工作区记录",
)
async def update_workspace(
    workspace_id: str,
    req: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 更新工作区记录（仅更新非 None 字段）。"""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作区记录不存在: {workspace_id}",
        )

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("更新工作区: %s (%s)", item.name, item.id)
    return _to_workspace_response(item)


@router.delete(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除工作区记录",
)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 删除工作区记录。"""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作区记录不存在: {workspace_id}",
        )

    await db.delete(item)
    await db.commit()
    logger.info("删除工作区: %s (%s)", item.name, item.id)


# ── 工作区 LLM 描述生成 ─────────────────────────────────


@router.post(
    "/workspaces/{workspace_id}/generate-description",
    response_model=GenerateDescriptionResponse,
    summary="使用 LLM 为工作区生成描述",
)
async def generate_workspace_description(
    workspace_id: str,
    req: GenerateDescriptionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    调用 LLM 根据工作区名称和路径信息生成简短描述，并保存到数据库。
    支持自定义 prompt。
    """
    # 查找工作区
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作区记录不存在: {workspace_id}",
        )

    # 加载 LLM 配置
    config = await load_llm_config(db)
    client = get_async_openai_client(config)
    model = config.get("model_chat", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_chat 为空。",
        )

    # 构建 prompt — 收集目录上下文丰富 LLM 输入
    ws_dir = Path(item.directory_path)
    dir_context = _collect_dir_context(ws_dir)

    custom_prompt = req.custom_prompt if req and req.custom_prompt else None
    prompt_mode = req.mode if req else "append"
    context_block = f"\n\n目录文件信息:\n{dir_context}" if dir_context else ""

    if custom_prompt:
        user_content = (
            f"工作区名称: {item.name}\n"
            f"目录路径: {item.directory_path}\n"
            f"当前状态: {item.status}"
            f"{context_block}\n\n"
            f"用户要求: {custom_prompt}"
        )
    else:
        user_content = (
            f"工作区名称: {item.name}\n"
            f"目录路径: {item.directory_path}\n"
            f"当前状态: {item.status}"
            f"{context_block}"
        )

    system_prompt = config.get("llm_system_prompt_workspace", "").strip()
    if not system_prompt:
        system_prompt = (
            "你是一个项目描述助手。根据提供的工作区名称、目录路径和目录文件列表信息，"
            "推断该项目的性质和技术栈，生成一段简洁的中文描述（1-2句话），说明该项目的用途和特点。"
            "只返回描述文本，不要附加任何解释、标点符号列表或前缀。"
        )

    # 根据 mode 处理自定义 prompt: override=覆盖 system_prompt, append=追加
    if custom_prompt and prompt_mode == "override":
        system_prompt = custom_prompt

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    logger.info(
        "[LLM-REQ] 工作区描述生成 | model=%s | name=%s | user_content 长度=%d",
        model,
        item.name,
        len(user_content),
    )
    logger.debug("[LLM-REQ] system_prompt: %s", system_prompt)
    logger.debug("[LLM-REQ] user_content: %s", user_content)

    try:
        max_tokens = int(config.get("llm_max_tokens", "1024"))
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=max_tokens,
        )

        # 详细记录 LLM 响应便于排查
        raw = (
            response.model_dump() if hasattr(response, "model_dump") else str(response)
        )
        logger.info(
            "[LLM-RES] 工作区描述 | model=%s | choices=%d | finish_reason=%s",
            getattr(response, "model", model),
            len(response.choices) if response.choices else 0,
            response.choices[0].finish_reason if response.choices else "N/A",
        )
        logger.debug("[LLM-RES] raw_response: %s", raw)

        description = ""
        if response.choices:
            msg = response.choices[0].message
            description = (msg.content or "").strip()
            # 推理模型 (如 GLM-4, DeepSeek-R1) 可能将内容放在 reasoning_content 中
            if not description:
                reasoning = getattr(msg, "reasoning_content", None) or ""
                if reasoning:
                    logger.info(
                        "[LLM-FALLBACK] 工作区描述 | content 为空，尝试从 reasoning_content 提取 | reasoning 长度=%d",
                        len(reasoning),
                    )
                    description = ""

        if not description:
            logger.warning(
                "[LLM-EMPTY] 工作区描述 | name=%s | finish_reason=%s | choices=%s",
                item.name,
                response.choices[0].finish_reason if response.choices else "N/A",
                raw,
            )
            hint = ""
            if response.choices and response.choices[0].finish_reason == "length":
                hint = "（模型输出被截断，可能是推理模型消耗了所有 token，建议更换非推理模型或增大 token 限制）"
            reasoning_preview = ""
            if response.choices:
                rc = (
                    getattr(response.choices[0].message, "reasoning_content", None)
                    or ""
                )
                if rc:
                    reasoning_preview = f" | reasoning_content 前200字: {rc[:200]}"
            return GenerateDescriptionResponse(
                success=False,
                description="",
                model=model,
                message=f"LLM 返回了空内容{hint}{reasoning_preview}",
            )

        # 保存到数据库
        item.description = description
        item.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(item)
        await db.commit()

        logger.info("LLM 生成工作区描述: %s -> %s", item.name, description[:50])
        return GenerateDescriptionResponse(
            success=True,
            description=description,
            model=response.model or model,
            message="描述生成成功",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM 生成工作区描述失败: %s -> %s", item.name, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 调用失败: {e}",
        )


# ── AI 自动填充工作区表单 ────────────────────────────────────


@router.post(
    "/workspaces/ai-fill-form",
    response_model=AiFillFormResponse,
    summary="AI 自动填充工作区表单",
)
async def ai_fill_workspace_form(
    req: AiFillFormRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    根据目录路径，使用 LLM 推断并返回:
      - name: 清洗后的可读项目名称（去掉日期前缀、下划线等）
      - description: 1-2 句项目描述
      - deadline: 从目录名中提取的日期 (YYYY-MM-DD)，如果没有则为 null
    不会写入数据库，仅返回建议值供前端填充。
    """
    import json
    import re

    config = await load_llm_config(db)
    client = get_async_openai_client(config)
    model = config.get("model_chat", "gpt-3.5-turbo")

    dir_path = Path(req.directory_path)
    dir_name = dir_path.name
    dir_context = _collect_dir_context(dir_path) if dir_path.is_dir() else ""
    context_block = f"\n\n目录文件信息:\n{dir_context}" if dir_context else ""

    system_prompt = (
        "你是一个项目表单填充助手。根据用户提供的工作区目录名和目录内容，返回以下 JSON 格式的填充建议:\n"
        "{\n"
        '  "name": "清洗后的可读项目名称（去掉日期前缀如 2024-01-01_、编号前缀、下划线/连字符等，保留有意义的项目名）",\n'
        '  "description": "1-2句简洁中文描述，说明项目用途和特点",\n'
        '  "created_at": "从目录名中提取的项目创建日期 YYYY-MM-DD 格式，如果目录名中没有日期则为 null"\n'
        "}\n\n"
        "规则:\n"
        "1. name 应简洁易读，如 '2024-03-15_MyProject_v2' → 'MyProject v2'\n"
        "2. 如果目录名含日期（如 20240315、2024-03-15、2024_0315），提取到 created_at 字段（这是项目的创建日期，不是截止日期）\n"
        "3. description 应基于目录内容推断项目性质，如果目录不存在或为空则根据名称推断\n"
        "4. 只返回 JSON，不要附加任何解释"
    )

    user_content = (
        f"目录名: {dir_name}\n目录完整路径: {req.directory_path}{context_block}"
    )

    logger.info("[LLM-REQ] AI 填充工作区表单 | dir=%s", dir_name)

    try:
        max_tokens = int(config.get("llm_max_tokens", "1024"))
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )

        content = ""
        if response.choices:
            content = (response.choices[0].message.content or "").strip()

        if not content:
            return AiFillFormResponse(
                success=False,
                message="LLM 返回了空内容",
                model=model,
            )

        # 提取 JSON（兼容 markdown ```json ... ``` 包裹）
        json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        if not json_match:
            logger.warning("[LLM-PARSE] 无法从响应中提取 JSON: %s", content[:200])
            return AiFillFormResponse(
                success=False,
                message=f"无法解析 LLM 响应为 JSON: {content[:100]}",
                model=getattr(response, "model", model) or model,
            )

        parsed = json.loads(json_match.group())
        name = str(parsed.get("name", dir_name)).strip()
        description = str(parsed.get("description", "")).strip()
        # 优先从 created_at 字段提取，兼容旧模型输出 deadline
        created_at = parsed.get("created_at") or parsed.get("deadline")
        deadline = None  # 不再从目录名提取 deadline

        # 校验 created_at 格式
        if created_at:
            created_at = str(created_at).strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", created_at):
                created_at = None
            elif created_at.lower() == "null":
                created_at = None

        logger.info(
            "[LLM-RES] AI 填充表单 | name=%s | created_at=%s | desc=%s",
            name,
            created_at,
            description[:50],
        )

        return AiFillFormResponse(
            success=True,
            name=name,
            description=description,
            created_at=created_at,
            deadline=deadline,
            model=getattr(response, "model", model) or model,
            message="表单填充成功",
        )

    except json.JSONDecodeError as e:
        logger.error("AI 填充表单 JSON 解析失败: %s", e)
        return AiFillFormResponse(
            success=False,
            message=f"LLM 响应 JSON 解析失败: {e}",
            model=model,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI 填充工作区表单失败: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 调用失败: {e}",
        )
