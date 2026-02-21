"""
系统管理路由 (System Router)

职责:
  - 提供初始化状态检测（前端向导弹窗触发依据）
  - 提供 allowed_dirs 的读写管理
"""

import json
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEFAULT_ALLOWED_DIRS
from app.core.database import get_db
from app.models.models import SystemSetting

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["System"])

# 判断"未初始化"时的哨兵：allowed_dirs 仍是默认占位值且 llm_base_url 为空
_DEFAULT_DIRS_SET = set(DEFAULT_ALLOWED_DIRS)


@router.get(
    "/init-status",
    summary="获取系统初始化状态",
)
async def get_init_status(db: AsyncSession = Depends(get_db)):
    """
    检测系统是否已完成首次初始化配置。

    未初始化的判定条件（满足任意一条）:
      - allowed_dirs 为空列表
      - allowed_dirs 仍等于启动时写入的默认占位目录（未被用户修改过）
      - llm_base_url 为空

    前端据此决定是否弹出设置向导。
    """
    keys = ["allowed_dirs", "llm_base_url"]
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys)))
    settings = {row.key: row.value for row in result.scalars().all()}

    # 解析 allowed_dirs
    dirs: list[str] = []
    raw_dirs = settings.get("allowed_dirs", "")
    if raw_dirs:
        try:
            parsed = json.loads(raw_dirs)
            if isinstance(parsed, list):
                dirs = [d for d in parsed if d]
        except (json.JSONDecodeError, TypeError):
            pass

    llm_base_url = settings.get("llm_base_url", "").strip()

    dirs_are_default = set(dirs) == _DEFAULT_DIRS_SET
    dirs_empty = len(dirs) == 0
    llm_not_configured = not llm_base_url

    needs_setup = dirs_empty or dirs_are_default or llm_not_configured

    return {
        "needs_setup": needs_setup,
        "allowed_dirs": dirs,
        "llm_configured": not llm_not_configured,
        "dirs_are_default": dirs_are_default,
    }


@router.get(
    "/allowed-dirs",
    summary="获取当前白名单目录列表",
)
async def get_allowed_dirs(db: AsyncSession = Depends(get_db)):
    """返回当前配置的 allowed_dirs 列表。"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    dirs: list[str] = []
    if setting and setting.value:
        try:
            parsed = json.loads(setting.value)
            if isinstance(parsed, list):
                dirs = [d for d in parsed if d]
        except (json.JSONDecodeError, TypeError):
            pass
    return {"allowed_dirs": dirs}


@router.put(
    "/allowed-dirs",
    summary="更新白名单目录列表",
)
async def update_allowed_dirs(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    更新 allowed_dirs 配置。
    请求体: { "allowed_dirs": ["C:/path1", "D:/path2"] }
    """
    dirs = payload.get("allowed_dirs", [])
    if not isinstance(dirs, list):
        dirs = []
    # 过滤空字符串
    dirs = [str(d).strip() for d in dirs if str(d).strip()]

    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    new_value = json.dumps(dirs, ensure_ascii=False)

    if setting:
        setting.value = new_value
    else:
        db.add(SystemSetting(key="allowed_dirs", value=new_value))

    await db.flush()
    await db.commit()
    logger.info("allowed_dirs 已更新: %s", dirs)
    return {"allowed_dirs": dirs}
