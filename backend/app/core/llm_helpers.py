"""
共享 LLM 工具函数

将 LLM 配置加载和 Client 实例化从 llm_router 中提取出来，
供 metadata_router 等模块复用。
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_value
from app.models.models import SystemSetting

logger = logging.getLogger(__name__)


async def load_llm_config(db: AsyncSession) -> dict[str, str]:
    """从 system_settings 表动态加载 LLM 相关配置，自动解密 llm_api_key。"""
    keys = ["llm_base_url", "llm_api_key", "model_chat", "model_embedding"]
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys)))
    settings = {row.key: row.value for row in result.scalars().all()}

    # 解密 API key（支持明文向后兼容）
    if "llm_api_key" in settings and settings["llm_api_key"]:
        settings["llm_api_key"] = decrypt_value(settings["llm_api_key"])

    return settings


def get_openai_client(config: dict[str, str]):
    """
    根据配置动态创建 OpenAI 兼容 Client。
    使用延迟导入以避免未安装 openai 时的启动错误。
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="openai 库未安装，请执行: pip install openai",
        )

    base_url = config.get("llm_base_url", "").strip()
    api_key = config.get("llm_api_key", "").strip()

    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: llm_base_url 为空。请先在设置中配置 LLM 连接信息。",
        )
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: llm_api_key 为空。请先在设置中配置 API 密钥。",
        )

    return OpenAI(base_url=base_url, api_key=api_key)
