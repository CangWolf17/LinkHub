"""
ChromaDB 向量数据库初始化模块
本地持久化模式，用于语义搜索（软件 + 工作区）。
lite 版本不含 chromadb 依赖，此时所有函数返回 None。
"""

import logging

from app.core.config import CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)

try:
    import chromadb

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    chromadb = None  # type: ignore[assignment]

# ── 全局 ChromaDB Client ─────────────────────────────────
_chroma_client = None

# Collection 名称常量
COLLECTION_SOFTWARE = "software"
COLLECTION_WORKSPACES = "workspaces"


def get_chroma_client():
    """获取 ChromaDB 客户端单例（懒加载）。若 chromadb 不可用则抛出 ImportError。"""
    global _chroma_client
    if not HAS_CHROMADB:
        raise ImportError("chromadb 未安装，语义搜索不可用")
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        logger.info("ChromaDB 初始化完成: %s", CHROMA_PERSIST_DIR)
    return _chroma_client


def get_software_collection():
    """获取软件向量集合（自动创建）。"""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_SOFTWARE,
        metadata={"description": "便携软件语义索引"},
    )


def get_workspace_collection():
    """获取工作区向量集合（自动创建）。"""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_WORKSPACES,
        metadata={"description": "工作区语义索引"},
    )


def shutdown_chroma():
    """关闭 ChromaDB 客户端（应用关闭时调用）。"""
    global _chroma_client
    if _chroma_client is not None:
        logger.info("ChromaDB 已关闭")
        _chroma_client = None
