"""
系统管理路由 (System Router)

职责:
  - 提供初始化状态检测（前端向导弹窗触发依据）
  - 提供 allowed_dirs 的读写管理
  - 提供服务关闭端点（优雅终止整个进程）
"""

import logging
import os
import signal
import sys
from typing import Union

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    DEFAULT_ALLOWED_DIRS,
    VALID_DIR_TYPES,
    DirEntry,
    parse_allowed_dirs,
    serialize_allowed_dirs,
)
from app.core.database import get_db
from app.models.models import SystemSetting


class UpdateAllowedDirsRequest(BaseModel):
    """更新白名单目录请求体，兼容新旧格式。"""

    allowed_dirs: list[Union[dict, str]] = Field(
        default_factory=list,
        description='目录列表，支持 [{"path": "...", "type": "software"}] 或 ["path1", "path2"]',
    )


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get(
    "/init-status",
    summary="获取系统初始化状态",
)
async def get_init_status(db: AsyncSession = Depends(get_db)):
    """
    检测系统是否已完成首次初始化配置。

    未初始化的判定条件（满足任意一条）:
      - allowed_dirs 为空列表
      - llm_base_url 为空

    前端据此决定是否弹出设置向导。
    """
    keys = ["allowed_dirs", "llm_base_url"]
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys)))
    settings = {row.key: row.value for row in result.scalars().all()}

    # 解析 allowed_dirs（兼容新旧格式）
    entries = parse_allowed_dirs(settings.get("allowed_dirs", ""))

    llm_base_url = settings.get("llm_base_url", "").strip()
    dirs_empty = len(entries) == 0
    llm_not_configured = not llm_base_url

    needs_setup = dirs_empty or llm_not_configured

    return {
        "needs_setup": needs_setup,
        "allowed_dirs": entries,
        "llm_configured": not llm_not_configured,
    }


@router.get(
    "/allowed-dirs",
    summary="获取当前白名单目录列表",
)
async def get_allowed_dirs(db: AsyncSession = Depends(get_db)):
    """返回当前配置的 allowed_dirs 列表（含类型信息）。"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    entries = parse_allowed_dirs(setting.value if setting else "")
    return {"allowed_dirs": entries}


@router.put(
    "/allowed-dirs",
    summary="更新白名单目录列表",
)
async def update_allowed_dirs(
    payload: UpdateAllowedDirsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    更新 allowed_dirs 配置。
    请求体: { "allowed_dirs": [{"path": "C:/path1", "type": "software"}, ...] }
    也兼容旧格式: { "allowed_dirs": ["C:/path1", "D:/path2"] }
    """
    raw_dirs = payload.allowed_dirs

    # 规范化为 DirEntry 列表
    entries: list[DirEntry] = []
    for item in raw_dirs:
        if isinstance(item, dict):
            p = str(item.get("path", "")).strip()
            t = str(item.get("type", "software")).strip()
            if p and t in VALID_DIR_TYPES:
                entries.append(DirEntry(path=p, type=t))
        elif isinstance(item, str):
            p = item.strip()
            if p:
                entries.append(DirEntry(path=p, type="software"))

    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    new_value = serialize_allowed_dirs(entries)

    if setting:
        setting.value = new_value
    else:
        db.add(SystemSetting(key="allowed_dirs", value=new_value))

    await db.flush()
    await db.commit()
    logger.info("allowed_dirs 已更新: %s", entries)
    return {"allowed_dirs": entries}


@router.post(
    "/shutdown",
    summary="关闭 LinkHub 服务",
)
async def shutdown_server():
    """
    优雅关闭整个 LinkHub 进程。

    先返回 HTTP 200，然后向自身进程发送终止信号。
    打包模式使用 os._exit 确保无僵尸进程残留；
    开发模式发送 SIGINT 让 uvicorn 正常走 shutdown 流程。
    """
    import asyncio

    logger.info("收到关闭请求，服务将在 1 秒后终止...")

    async def _delayed_shutdown():
        await asyncio.sleep(1)
        logger.info("LinkHub 正在终止进程...")
        from app.core.config import IS_FROZEN

        if IS_FROZEN:
            # 打包模式：直接退出，避免僵尸进程
            os._exit(0)
        else:
            # 开发模式：发送 SIGINT 让 uvicorn 优雅停止
            os.kill(os.getpid(), signal.SIGINT)

    asyncio.get_event_loop().create_task(_delayed_shutdown())
    return {"message": "服务正在关闭..."}
