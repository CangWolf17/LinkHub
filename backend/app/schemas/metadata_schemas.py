"""
Pydantic Schema - 模块 B: Metadata CRUD 的请求/响应模型
包含便携软件 (PortableSoftware) 和工作区 (Workspace) 的 CRUD Schema。
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── 便携软件 Schemas ─────────────────────────────────────


class SoftwareCreate(BaseModel):
    """创建便携软件请求体"""

    name: str = Field(..., min_length=1, max_length=255, description="软件名称")
    executable_path: str = Field(..., description="可执行文件绝对路径")
    description: str | None = Field(None, description="软件描述（可由 LLM 生成）")
    tags: str | None = Field(None, description="标签，JSON 数组字符串")
    icon_path: str | None = Field(None, description="图标路径")


class SoftwareUpdate(BaseModel):
    """更新便携软件请求体（所有字段可选）"""

    name: str | None = Field(None, min_length=1, max_length=255)
    executable_path: str | None = None
    description: str | None = None
    tags: str | None = None
    icon_path: str | None = None


class SoftwareResponse(BaseModel):
    """便携软件响应体"""

    id: str
    name: str
    executable_path: str
    description: str | None = None
    tags: str | None = None
    icon_path: str | None = None
    is_missing: bool = Field(False, description="可执行文件路径是否已失效（死链）")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SoftwareListResponse(BaseModel):
    """便携软件列表响应体"""

    items: list[SoftwareResponse]
    total: int


# ── 工作区 Schemas ───────────────────────────────────────


class WorkspaceCreate(BaseModel):
    """创建工作区请求体"""

    name: str = Field(..., min_length=1, max_length=255, description="工作区名称")
    directory_path: str = Field(..., description="工作区目录绝对路径")
    description: str | None = Field(None, description="项目备注")
    deadline: datetime | None = Field(None, description="截止日期")
    status: str = Field("active", description="状态: active / archived / completed")


class WorkspaceUpdate(BaseModel):
    """更新工作区请求体（所有字段可选）"""

    name: str | None = Field(None, min_length=1, max_length=255)
    directory_path: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    status: str | None = None


class WorkspaceResponse(BaseModel):
    """工作区响应体"""

    id: str
    name: str
    directory_path: str
    description: str | None = None
    deadline: datetime | None = None
    status: str
    is_missing: bool = Field(False, description="目录路径是否已失效（死链）")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceListResponse(BaseModel):
    """工作区列表响应体"""

    items: list[WorkspaceResponse]
    total: int
