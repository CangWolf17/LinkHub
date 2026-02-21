"""
LinkHub - Local Smart Dashboard
主入口文件: 启动 FastAPI 应用，注册路由，初始化数据库。
服务强制绑定 127.0.0.1，仅供本机浏览器访问。
"""

import json
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import APP_HOST, APP_PORT, DEFAULT_ALLOWED_DIRS
from app.core.crypto import encrypt_value, is_encrypted
from app.core.database import async_session_factory, engine
from app.core.vector_store import get_chroma_client, shutdown_chroma
from app.models.models import Base, SystemSetting
from app.routers import (
    installer_router,
    llm_router,
    metadata_router,
    os_router,
    search_router,
    system_router,
)

# ── 日志配置 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("linkhub")


# ── 数据库初始化 & 默认数据 ───────────────────────────────


async def _seed_default_settings():
    """向 system_settings 插入默认配置（仅当 key 不存在时）。"""
    defaults = {
        "allowed_dirs": json.dumps(DEFAULT_ALLOWED_DIRS, ensure_ascii=False),
        "llm_base_url": "",
        "llm_api_key": "",
        "model_chat": "",
        "model_embedding": "",
    }

    async with async_session_factory() as session:
        for key, value in defaults.items():
            existing = await session.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            if existing.scalar_one_or_none() is None:
                session.add(SystemSetting(key=key, value=value))
                logger.info("初始化配置项: %s", key)
        await session.commit()


async def _migrate_plaintext_api_key():
    """
    启动时迁移：检测 llm_api_key 是否为明文，若是则用 DPAPI 重新加密。
    保证旧版本数据库升级后 key 自动加密，无需用户手动操作。
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == "llm_api_key")
        )
        setting = result.scalar_one_or_none()
        if setting and setting.value and not is_encrypted(setting.value):
            try:
                setting.value = encrypt_value(setting.value)
                await session.commit()
                logger.info("llm_api_key 已从明文迁移为 DPAPI 加密存储")
            except Exception as e:
                logger.error("llm_api_key 迁移加密失败: %s", e)


# ── 应用生命周期 ──────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭的生命周期管理。"""
    logger.info("LinkHub 正在启动...")

    # 创建所有数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表已就绪")

    # 插入默认配置
    await _seed_default_settings()
    logger.info("默认配置已就绪")

    # 迁移明文 API key → DPAPI 加密
    await _migrate_plaintext_api_key()

    # 初始化 ChromaDB 向量数据库
    get_chroma_client()
    logger.info("ChromaDB 向量数据库已就绪")

    logger.info("LinkHub 启动完成 -> http://%s:%s", APP_HOST, APP_PORT)
    yield

    # 关闭 ChromaDB
    shutdown_chroma()

    # 关闭引擎连接池
    await engine.dispose()
    logger.info("LinkHub 已关闭")


# ── FastAPI 实例 ──────────────────────────────────────────

app = FastAPI(
    title="LinkHub - Local Smart Dashboard",
    description="本地智能工作区与软件控制台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: 仅允许本机前端开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",  # Vite 默认端口
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──────────────────────────────────────────────
app.include_router(system_router.router)
app.include_router(os_router.router)
app.include_router(metadata_router.router)
app.include_router(llm_router.router)
app.include_router(installer_router.router)
app.include_router(search_router.router)


# ── 健康检查 ──────────────────────────────────────────────


@app.get("/api/health", tags=["System"])
async def health_check():
    """服务健康检查端点"""
    return {"status": "ok", "service": "LinkHub"}


# ── 启动入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=True,
        log_level="info",
    )
