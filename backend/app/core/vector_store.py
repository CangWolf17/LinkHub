"""
ChromaDB 向量数据库初始化模块
本地持久化模式，用于语义搜索（软件 + 工作区）。
"""

import logging

import chromadb

from app.core.config import CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)

# ── 全局 ChromaDB Client ─────────────────────────────────
_chroma_client: chromadb.ClientAPI | None = None

# Collection 名称常量
COLLECTION_SOFTWARE = "software"
COLLECTION_WORKSPACES = "workspaces"


def get_chroma_client() -> chromadb.ClientAPI:
    """获取 ChromaDB 客户端单例（懒加载）。"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        logger.info("ChromaDB 初始化完成: %s", CHROMA_PERSIST_DIR)
    return _chroma_client


def get_software_collection() -> chromadb.Collection:
    """获取软件向量集合（自动创建）。"""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_SOFTWARE,
        metadata={"description": "便携软件语义索引"},
    )


def get_workspace_collection() -> chromadb.Collection:
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
