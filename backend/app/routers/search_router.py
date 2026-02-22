"""
语义搜索路由 (Semantic Search Router)

职责:
  - 基于 ChromaDB 向量数据库实现自然语言搜索
  - 支持软件和工作区的全局/分类搜索
  - 提供索引管理（重建索引、统计信息）
  - 入库时自动转向量（通过 upsert）

ChromaDB 使用内置的 default embedding function (all-MiniLM-L6-v2)，
无需调用外部 LLM API 即可实现语义搜索。
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.vector_store import (
    HAS_CHROMADB,
    get_software_collection,
    get_workspace_collection,
)
from app.models.models import PortableSoftware, Workspace
from app.schemas.search_schemas import (
    IndexStatsResponse,
    ReindexResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["Semantic Search"])


# ── 内部工具函数 ─────────────────────────────────────────


def _check_path_missing(path_str: str) -> bool:
    """轻量级死链检测。"""
    try:
        return not Path(path_str).exists()
    except (OSError, ValueError):
        return True


def _search_collection(
    collection, query: str, top_k: int, result_type: str
) -> list[SearchResultItem]:
    """在指定 collection 中执行向量搜索。"""
    try:
        count = collection.count()
        if count == 0:
            return []

        # 实际返回数不超过 collection 中的文档数
        n = min(top_k, count)

        results = collection.query(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        items: list[SearchResultItem] = []
        if results and results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            distances = (
                results["distances"][0] if results["distances"] else [0.0] * len(ids)
            )
            metadatas = (
                results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
            )

            for i, doc_id in enumerate(ids):
                meta = metadatas[i] or {}
                path = meta.get("path", "")
                items.append(
                    SearchResultItem(
                        id=doc_id,
                        name=meta.get("name", ""),
                        type=result_type,
                        description=meta.get("description"),
                        path=path,
                        score=distances[i],
                        is_missing=_check_path_missing(path) if path else False,
                    )
                )

        return items

    except Exception as e:
        logger.error("向量搜索失败 (%s): %s", result_type, e)
        return []


# ── API 端点 ─────────────────────────────────────────────


@router.post(
    "",
    response_model=SearchResponse,
    summary="语义搜索（自然语言查向量）",
)
async def semantic_search(req: SearchRequest):
    """
    基于 ChromaDB 的语义搜索。
    使用内置 embedding 模型将查询文本转为向量，在索引中查找最相似的结果。

    scope 参数控制搜索范围:
      - all: 同时搜索软件和工作区
      - software: 仅搜索软件
      - workspaces: 仅搜索工作区
    """
    if not HAS_CHROMADB:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="语义搜索不可用（lite 版不含 ChromaDB）",
        )
    all_results: list[SearchResultItem] = []

    if req.scope in ("all", "software"):
        sw_collection = get_software_collection()
        sw_results = _search_collection(sw_collection, req.query, req.top_k, "software")
        all_results.extend(sw_results)

    if req.scope in ("all", "workspaces"):
        ws_collection = get_workspace_collection()
        ws_results = _search_collection(
            ws_collection, req.query, req.top_k, "workspace"
        )
        all_results.extend(ws_results)

    # 按 score (距离) 排序，距离越小越相似
    all_results.sort(key=lambda x: x.score)

    # 截取 top_k
    all_results = all_results[: req.top_k]

    return SearchResponse(
        success=True,
        results=all_results,
        total=len(all_results),
        query=req.query,
    )


@router.get(
    "/stats",
    response_model=IndexStatsResponse,
    summary="查看向量索引统计信息",
)
async def get_index_stats():
    """返回 ChromaDB 中各 collection 的文档数量。"""
    if not HAS_CHROMADB:
        return IndexStatsResponse(software_count=0, workspace_count=0)
    sw_collection = get_software_collection()
    ws_collection = get_workspace_collection()

    return IndexStatsResponse(
        software_count=sw_collection.count(),
        workspace_count=ws_collection.count(),
    )


@router.post(
    "/reindex",
    response_model=ReindexResponse,
    summary="从数据库重建全部向量索引",
)
async def reindex_all(
    db: AsyncSession = Depends(get_db),
):
    """
    从 SQLite 数据库重新读取所有软件和工作区记录，
    全量重建 ChromaDB 向量索引。
    用于索引损坏或数据不一致时的修复操作。
    """
    if not HAS_CHROMADB:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="语义搜索不可用（lite 版不含 ChromaDB）",
        )
    sw_count = 0
    ws_count = 0

    # ── 重建软件索引 ────────────────────────────────────
    try:
        sw_collection = get_software_collection()
        result = await db.execute(select(PortableSoftware))
        software_items = result.scalars().all()

        if software_items:
            ids = []
            documents = []
            metadatas = []

            for item in software_items:
                doc = (
                    f"{item.name}. {item.description}"
                    if item.description
                    else item.name
                )
                ids.append(item.id)
                documents.append(doc)
                metadatas.append(
                    {
                        "name": item.name,
                        "path": item.executable_path,
                        "type": "software",
                        "description": item.description or "",
                    }
                )

            sw_collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            sw_count = len(ids)

        logger.info("软件索引重建完成: %d 条", sw_count)

    except Exception as e:
        logger.error("软件索引重建失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"软件索引重建失败: {e}",
        )

    # ── 重建工作区索引 ──────────────────────────────────
    try:
        ws_collection = get_workspace_collection()
        result = await db.execute(select(Workspace))
        workspace_items = result.scalars().all()

        if workspace_items:
            ids = []
            documents = []
            metadatas = []

            for item in workspace_items:
                doc = (
                    f"{item.name}. {item.description}"
                    if item.description
                    else item.name
                )
                ids.append(item.id)
                documents.append(doc)
                metadatas.append(
                    {
                        "name": item.name,
                        "path": item.directory_path,
                        "type": "workspace",
                        "description": item.description or "",
                        "status": item.status or "",
                    }
                )

            ws_collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            ws_count = len(ids)

        logger.info("工作区索引重建完成: %d 条", ws_count)

    except Exception as e:
        logger.error("工作区索引重建失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"工作区索引重建失败: {e}",
        )

    return ReindexResponse(
        success=True,
        software_indexed=sw_count,
        workspace_indexed=ws_count,
        message=f"索引重建完成: 软件 {sw_count} 条, 工作区 {ws_count} 条",
    )
