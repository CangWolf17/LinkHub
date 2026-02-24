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
    install_dir: str | None = Field(None, description="安装目录路径")
    description: str | None = Field(None, description="软件描述（可由 LLM 生成）")
    tags: str | None = Field(None, description="标签，JSON 数组字符串")
    icon_path: str | None = Field(None, description="图标路径")


class SoftwareUpdate(BaseModel):
    """更新便携软件请求体（所有字段可选）"""

    name: str | None = Field(None, min_length=1, max_length=255)
    executable_path: str | None = None
    install_dir: str | None = None
    description: str | None = None
    tags: str | None = None
    icon_path: str | None = None


class SoftwareResponse(BaseModel):
    """便携软件响应体"""

    id: str
    name: str
    executable_path: str
    install_dir: str | None = None
    description: str | None = None
    tags: str | None = None
    icon_path: str | None = None
    is_missing: bool = Field(False, description="完全失效（exe和目录都不存在）")
    exe_exists: bool = Field(True, description="可执行文件是否存在")
    dir_exists: bool = Field(True, description="安装目录是否存在")
    last_used_at: datetime | None = None
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
    created_at: datetime | None = Field(
        None, description="创建日期（可选，不填则由服务端自动生成）"
    )
    status: str = Field(
        "active", description="状态: not_started / active / completed / archived"
    )


class WorkspaceUpdate(BaseModel):
    """更新工作区请求体（所有字段可选）"""

    name: str | None = Field(None, min_length=1, max_length=255)
    directory_path: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    created_at: datetime | None = None
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


class WorkspaceScanResponse(BaseModel):
    """工作区扫描导入响应"""

    success: bool
    imported: int = Field(0, description="本次新导入的工作区数量")
    skipped: int = Field(0, description="已存在跳过的数量")
    details: list[dict] = Field(default_factory=list)
    message: str = ""


# ── LLM 描述生成 Schemas ─────────────────────────────────


class GenerateDescriptionRequest(BaseModel):
    """LLM 描述生成请求（可选自定义提示词）"""

    custom_prompt: str | None = Field(
        None, description="用户自定义提示词，为空则使用默认 prompt"
    )
    mode: str = Field(
        "append",
        description="prompt 模式: append=追加到系统提示词后, override=覆盖系统提示词",
    )


class GenerateDescriptionResponse(BaseModel):
    """LLM 描述生成响应"""

    success: bool
    description: str = Field("", description="生成的描述文本")
    model: str = Field("", description="使用的模型")
    message: str = ""


# ── 工作区 AI 表单填充 Schemas ────────────────────────────


class AiFillFormRequest(BaseModel):
    """AI 自动填充工作区表单请求"""

    directory_path: str = Field(..., description="工作区目录路径")


class AiFillFormResponse(BaseModel):
    """AI 自动填充工作区表单响应"""

    success: bool
    name: str = Field("", description="清洗后的项目名称")
    description: str = Field("", description="生成的项目描述")
    created_at: str | None = Field(
        None, description="从目录名中提取的创建日期 (YYYY-MM-DD) 或 None"
    )
    deadline: str | None = Field(None, description="保留字段，暂未使用")
    model: str = Field("", description="使用的模型")
    message: str = ""
