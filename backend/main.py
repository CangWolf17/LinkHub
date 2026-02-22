"""
LinkHub - Local Smart Dashboard
主入口文件: 启动 FastAPI 应用，注册路由，初始化数据库。
服务强制绑定 127.0.0.1，仅供本机浏览器访问。
"""

import asyncio
import json
import logging
import logging.handlers
import os
import signal
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

# ── PyInstaller --noconsole 修复 ──────────────────────────
# PyInstaller --noconsole 模式下 sys.stdout / sys.stderr 为 None，
# 导致 uvicorn DefaultFormatter 调用 sys.stderr.isatty() 崩溃。
# 在所有 import 之前修复，确保日志系统正常初始化。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.config import (
    APP_HOST,
    APP_PORT,
    DEFAULT_ALLOWED_DIRS,
    FRONTEND_DIST_DIR,
    IS_FROZEN,
    LOG_DIR,
    serialize_allowed_dirs,
)
from app.core.crypto import encrypt_value, is_encrypted
from app.core.database import async_session_factory, engine
from app.core.log_buffer import BufferHandler, log_broadcaster, log_buffer
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

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_LOG_DATEFMT = "%H:%M:%S"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 防止 uvicorn reload 模式重复添加 handler
if not any(isinstance(h, BufferHandler) for h in root_logger.handlers):
    _formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT)

    # 控制台 handler
    _console = logging.StreamHandler()
    _console.setFormatter(_formatter)
    root_logger.addHandler(_console)

    # 内存缓冲 handler（供 WebSocket 推送）
    _buffer_handler = BufferHandler()
    _buffer_handler.setFormatter(_formatter)
    root_logger.addHandler(_buffer_handler)

    # 文件 handler: 按大小轮转，单文件最大 5MB，保留 3 个备份（共约 20MB）
    _file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_DIR / "linkhub.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    _file_handler.setFormatter(_file_formatter)
    root_logger.addHandler(_file_handler)

logger = logging.getLogger("linkhub")


# ── 数据库初始化 & 默认数据 ───────────────────────────────


async def _seed_default_settings():
    """向 system_settings 插入默认配置（仅当 key 不存在时）。"""
    defaults = {
        "allowed_dirs": serialize_allowed_dirs(DEFAULT_ALLOWED_DIRS),
        "llm_base_url": "",
        "llm_api_key": "",
        "model_chat": "",
        "model_embedding": "",
        "llm_max_tokens": "1024",
        "llm_system_prompt_software": (
            "你是一个软件描述助手。根据提供的软件名称、路径和目录文件列表信息，"
            "推断该软件的用途，生成一段简洁的中文描述（1-2句话），说明该软件的用途和特点。"
            "只返回描述文本，不要附加任何解释、标点符号列表或前缀。"
        ),
        "llm_system_prompt_workspace": (
            "你是一个项目描述助手。根据提供的工作区名称、目录路径和目录文件列表信息，"
            "推断该项目的性质和技术栈，生成一段简洁的中文描述（1-2句话），说明该项目的用途和特点。"
            "只返回描述文本，不要附加任何解释、标点符号列表或前缀。"
        ),
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

    # 初始化 ChromaDB 向量数据库（可选，lite 版不含此依赖）
    try:
        from app.core.vector_store import get_chroma_client

        get_chroma_client()
        logger.info("ChromaDB 向量数据库已就绪")
    except ImportError as exc:
        logger.info("ChromaDB 不可用（lite 版），语义搜索已禁用: %s", exc)
    except Exception as exc:
        logger.error("ChromaDB 初始化失败: %s", exc, exc_info=True)

    logger.info("LinkHub 启动完成 -> http://%s:%s", APP_HOST, APP_PORT)

    # 打包模式下自动打开浏览器
    if IS_FROZEN:
        webbrowser.open(f"http://{APP_HOST}:{APP_PORT}")

    yield

    # 关闭 ChromaDB
    try:
        from app.core.vector_store import shutdown_chroma

        shutdown_chroma()
    except ImportError:
        pass

    # 关闭引擎连接池
    await engine.dispose()
    logger.info("LinkHub 已关闭")


# ── FastAPI 实例 ──────────────────────────────────────────

app = FastAPI(
    title="LinkHub - Local Smart Dashboard",
    description="本地智能工作区与软件控制台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: 仅允许本机前端
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",  # Vite 默认端口
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        f"http://127.0.0.1:{APP_PORT}",  # 打包模式: 同源
        f"http://localhost:{APP_PORT}",
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


# ── 前端静态文件（打包模式）──────────────────────────────
# 必须在 API 路由之后挂载，否则会拦截 /api/* 请求
if FRONTEND_DIST_DIR.is_dir():
    from fastapi.responses import FileResponse

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    # SPA fallback: 非 /api 开头的路径返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 优先尝试静态文件
        file = FRONTEND_DIST_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    logger.info("前端静态文件已挂载: %s", FRONTEND_DIST_DIR)


# ── 健康检查 ──────────────────────────────────────────────


@app.get("/api/health", tags=["System"])
async def health_check():
    """服务健康检查端点"""
    return {"status": "ok", "service": "LinkHub"}


# ── 日志端点 ──────────────────────────────────────────────


@app.get("/api/logs", tags=["Logs"])
async def get_logs(limit: int = 200):
    """获取最近的日志记录（HTTP 轮询备用）"""
    return {"logs": log_buffer.get_recent(limit)}


@app.websocket("/api/ws/logs")
async def ws_logs(websocket: WebSocket):
    """WebSocket 实时日志推送"""
    await websocket.accept()
    queue = log_broadcaster.subscribe()
    try:
        while True:
            record = await queue.get()
            await websocket.send_text(json.dumps(record, ensure_ascii=False))
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        log_broadcaster.unsubscribe(queue)


# ── 启动入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    # 打包模式防僵尸进程：注册 atexit 确保进程树完整退出
    if IS_FROZEN:
        import atexit

        def _force_exit():
            """兜底退出：若正常 shutdown 流程卡住，强制终止进程。"""
            try:
                logger.info("atexit: 强制终止进程")
            except Exception:
                pass
            os._exit(0)

        atexit.register(_force_exit)

    uvicorn.run(
        "main:app" if not IS_FROZEN else app,
        host=APP_HOST,
        port=APP_PORT,
        reload=not IS_FROZEN,
        log_level="info",
    )
