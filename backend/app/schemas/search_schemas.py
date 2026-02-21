"""
Pydantic Schema - 语义搜索的请求/响应模型
基于 ChromaDB 向量搜索实现自然语言查询。
"""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """语义搜索请求体"""

    query: str = Field(..., min_length=1, description="自然语言搜索查询")
    top_k: int = Field(10, ge=1, le=100, description="返回结果数量上限")
    scope: str = Field(
        "all",
        description="搜索范围: all / software / workspaces",
    )


class SearchResultItem(BaseModel):
    """单条搜索结果"""

    id: str = Field(..., description="记录 ID")
    name: str = Field("", description="名称")
    type: str = Field("", description="类型: software / workspace")
    description: str | None = Field(None, description="描述")
    path: str = Field("", description="路径")
    score: float = Field(0.0, description="相似度得分 (距离越小越相似)")
    is_missing: bool = Field(False, description="路径是否已失效")


class SearchResponse(BaseModel):
    """语义搜索响应体"""

    success: bool
    results: list[SearchResultItem] = Field(default_factory=list)
    total: int = Field(0, description="返回的结果数量")
    query: str = Field("", description="原始查询")


class IndexStatsResponse(BaseModel):
    """向量索引统计信息"""

    software_count: int = Field(0, description="软件索引中的文档数")
    workspace_count: int = Field(0, description="工作区索引中的文档数")


class ReindexResponse(BaseModel):
    """重建索引响应"""

    success: bool
    software_indexed: int = Field(0, description="软件索引更新数量")
    workspace_indexed: int = Field(0, description="工作区索引更新数量")
    message: str = ""
