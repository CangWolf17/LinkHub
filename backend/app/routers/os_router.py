"""
模块 A: 操作系统安全桥接 (OS Bridge Router) - 高危模块

安全措施:
  1. 白名单目录校验 — 目标路径必须位于允许的目录下
  2. 路径遍历防护 — resolve() 后重新校验，拒绝 ../ 等穿越攻击
  3. 可执行文件后缀白名单 — 仅允许 .exe/.bat/.cmd/.lnk
  4. 非阻塞执行 — subprocess.Popen + DETACHED_PROCESS，绝不阻塞主线程
"""

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    ALLOWED_EXECUTABLE_SUFFIXES,
    all_dir_paths,
    parse_allowed_dirs,
)
from app.core.database import get_db
from app.models.models import PortableSoftware, SystemSetting
from app.schemas.os_schemas import OSActionResponse, OSTargetRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/os", tags=["OS Bridge"])


# ── 内部工具函数 ─────────────────────────────────────────


async def _get_allowed_dirs(db: AsyncSession) -> list[Path]:
    """
    从 system_settings 表动态读取白名单目录。
    返回所有类型的目录（software + workspace），用于路径安全校验。
    """
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == "allowed_dirs")
    )
    row = result.scalar_one_or_none()

    if row:
        entries = parse_allowed_dirs(row)
        if entries:
            return [p.resolve() for p in all_dir_paths(entries)]

    return []


def _validate_path_within_whitelist(target: Path, allowed_dirs: list[Path]) -> bool:
    """
    校验 resolved 后的绝对路径是否位于白名单目录之下。
    使用 is_relative_to() 进行严格的父子关系判断。
    """
    for allowed in allowed_dirs:
        try:
            if target.is_relative_to(allowed):
                return True
        except (ValueError, TypeError):
            continue
    return False


def _sanitize_and_resolve(raw_path: str) -> Path:
    """
    路径净化:
      - 拒绝包含 .. 的原始输入（初筛）
      - 使用 resolve() 获取规范化绝对路径（最终防线）
    """
    # 初筛: 检查原始字符串中的遍历特征
    if ".." in raw_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径中不允许包含 '..'",
        )

    path = Path(raw_path)

    # 必须是绝对路径
    if not path.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供绝对路径",
        )

    # resolve() 会消除所有符号链接和 ./ ../ 得到真实路径
    return path.resolve()


# ── API 端点 ─────────────────────────────────────────────


@router.post(
    "/launch",
    response_model=OSActionResponse,
    summary="安全拉起可执行程序",
)
async def launch_executable(
    req: OSTargetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    以非阻塞方式启动目标可执行文件。
    执行前需通过: 白名单目录校验 + 可执行后缀校验 + 文件存在性校验。
    """
    resolved = _sanitize_and_resolve(req.target_path)
    allowed_dirs = await _get_allowed_dirs(db)

    # 白名单校验
    if not _validate_path_within_whitelist(resolved, allowed_dirs):
        logger.warning("拒绝越界访问: %s", resolved)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"路径不在允许的白名单目录内: {resolved}",
        )

    # 后缀校验
    if resolved.suffix.lower() not in ALLOWED_EXECUTABLE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不允许执行此类型文件: {resolved.suffix}",
        )

    # 存在性校验
    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标文件不存在: {resolved}",
        )

    # 非阻塞拉起 (Windows: DETACHED_PROCESS)
    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )

        subprocess.Popen(
            [str(resolved)],
            cwd=str(resolved.parent),
            creationflags=creation_flags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        logger.info("已拉起程序: %s", resolved)

        # 更新软件的最近使用时间
        try:
            result = await db.execute(
                select(PortableSoftware).where(
                    PortableSoftware.executable_path == str(resolved)
                )
            )
            sw = result.scalar_one_or_none()
            if sw:
                sw.last_used_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception as e:
            logger.debug("更新 last_used_at 失败（非阻塞）: %s", e)

        return OSActionResponse(
            success=True,
            message="程序已成功启动",
            target_path=str(resolved),
        )

    except OSError as e:
        logger.error("拉起程序失败: %s -> %s", resolved, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动程序失败: {e}",
        )


@router.post(
    "/open-dir",
    response_model=OSActionResponse,
    summary="用系统资源管理器打开目录",
)
async def open_directory(
    req: OSTargetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    调用系统资源管理器打开目标目录。
    同样需要通过白名单校验。
    """
    resolved = _sanitize_and_resolve(req.target_path)
    allowed_dirs = await _get_allowed_dirs(db)

    # 白名单校验
    if not _validate_path_within_whitelist(resolved, allowed_dirs):
        logger.warning("拒绝越界目录访问: %s", resolved)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"路径不在允许的白名单目录内: {resolved}",
        )

    # 存在性校验
    if not resolved.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标目录不存在: {resolved}",
        )

    # 使用 explorer 打开目录 (Windows)
    try:
        if sys.platform == "win32":
            # 使用 start explorer 避免窗口被后台进程遮挡
            subprocess.Popen(
                ["cmd", "/c", "start", "explorer", str(resolved)],
                creationflags=subprocess.CREATE_NO_WINDOW,
                close_fds=True,
            )
        else:
            # Linux / macOS 兼容 (虽然项目定位为 Windows)
            opener = "xdg-open" if sys.platform.startswith("linux") else "open"
            subprocess.Popen([opener, str(resolved)], close_fds=True)

        logger.info("已打开目录: %s", resolved)
        return OSActionResponse(
            success=True,
            message="已在资源管理器中打开目录",
            target_path=str(resolved),
        )

    except OSError as e:
        logger.error("打开目录失败: %s -> %s", resolved, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"打开目录失败: {e}",
        )


# ── 目录浏览端点（文件夹选择器） ─────────────────────────


class BrowseDirRequest(BaseModel):
    """目录浏览请求"""

    path: Optional[str] = Field(
        None,
        description="要浏览的目录绝对路径，为空时返回驱动器列表（Windows）",
    )


class DirItem(BaseModel):
    """单条目录项"""

    name: str
    path: str
    is_dir: bool = True


class BrowseDirResponse(BaseModel):
    """目录浏览响应"""

    current: str
    parent: Optional[str] = None
    items: list[DirItem]


@router.post(
    "/browse-dir",
    response_model=BrowseDirResponse,
    summary="浏览本地目录（文件夹选择器）",
)
async def browse_directory(req: BrowseDirRequest):
    """
    列出指定目录下的子目录（不列出文件）。
    当 path 为空/null 时，Windows 下返回驱动器列表。
    此端点不受白名单限制（因为用户就是在选择要添加的白名单目录）。
    """
    # 如果没有指定路径，返回驱动器列表（Windows）
    if not req.path or not req.path.strip():
        if sys.platform == "win32":
            drives: list[DirItem] = []
            # 遍历 A-Z 盘符
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.isdir(drive):
                    drives.append(DirItem(name=f"{letter}:", path=drive))
            return BrowseDirResponse(current="", parent=None, items=drives)
        else:
            # Linux/macOS: 返回根目录
            return BrowseDirResponse(
                current="/",
                parent=None,
                items=[
                    DirItem(name=d, path=f"/{d}")
                    for d in sorted(os.listdir("/"))
                    if os.path.isdir(f"/{d}")
                ],
            )

    raw = req.path.strip()

    # 路径安全检查
    if ".." in raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径中不允许包含 '..'",
        )

    target = Path(raw)
    if not target.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供绝对路径",
        )

    resolved = target.resolve()
    if not resolved.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目录不存在: {resolved}",
        )

    # 获取父目录
    parent = str(resolved.parent) if resolved.parent != resolved else None

    # 列出子目录
    items: list[DirItem] = []
    try:
        for entry in sorted(resolved.iterdir(), key=lambda e: e.name.lower()):
            if entry.is_dir() and not entry.name.startswith("."):
                items.append(DirItem(name=entry.name, path=str(entry)))
    except PermissionError:
        logger.warning("无权限访问目录: %s", resolved)
        # 返回空列表但不报错，让用户知道这个目录不可访问

    return BrowseDirResponse(
        current=str(resolved),
        parent=parent,
        items=items,
    )
