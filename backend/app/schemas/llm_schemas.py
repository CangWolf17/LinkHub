"""
Pydantic Schema - 模块 C: Universal LLM Gateway 的请求/响应模型
支持 Chat / Embed / Extract 三种任务类型。
所有响应必须包含 raw_response 字段，保留 LLM 返回的原始数据。
"""

from pydantic import BaseModel, Field


# ── Chat Schemas ─────────────────────────────────────────


class ChatMessage(BaseModel):
    """单条对话消息"""

    role: str = Field(..., description="角色: system / user / assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """Chat 对话请求体"""

    messages: list[ChatMessage] = Field(..., min_length=1, description="对话消息列表")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int | None = Field(None, ge=1, description="最大生成 token 数")


class ChatResponse(BaseModel):
    """Chat 对话响应体"""

    success: bool
    content: str = Field("", description="助手回复的文本内容")
    model: str = Field("", description="实际使用的模型名称")
    usage: dict | None = Field(None, description="Token 使用量统计")
    raw_response: dict | str | None = Field(
        None, description="LLM 返回的原始响应（供前端调试监控）"
    )


# ── Embed Schemas ────────────────────────────────────────


class EmbedRequest(BaseModel):
    """文本嵌入请求体"""

    texts: list[str] = Field(..., min_length=1, description="需要转向量的文本列表")


class EmbedResponse(BaseModel):
    """文本嵌入响应体"""

    success: bool
    embeddings: list[list[float]] = Field(
        default_factory=list, description="向量结果列表"
    )
    model: str = Field("", description="实际使用的 Embedding 模型")
    raw_response: dict | str | None = None


# ── Extract Schemas ──────────────────────────────────────


class ExtractRequest(BaseModel):
    """结构化信息提取请求体"""

    text: str = Field(..., min_length=1, description="待提取的源文本")
    instruction: str = Field(
        "请从以下文本中提取结构化信息，以 JSON 格式返回。",
        description="提取指令",
    )
    temperature: float = Field(
        0.3, ge=0.0, le=2.0, description="生成温度（提取任务建议低温）"
    )


class ExtractResponse(BaseModel):
    """结构化信息提取响应体"""

    success: bool
    extracted: dict | list | str | None = Field(None, description="提取到的结构化数据")
    model: str = Field("", description="实际使用的模型名称")
    raw_response: dict | str | None = None


# ── 通用错误响应 ─────────────────────────────────────────


class LLMErrorResponse(BaseModel):
    """LLM 网关错误响应"""

    success: bool = False
    error: str = Field(..., description="错误信息")
    raw_response: dict | str | None = None


# ── LLM 配置相关 ─────────────────────────────────────────


class LLMConfigResponse(BaseModel):
    """当前 LLM 配置状态（脱敏）"""

    llm_base_url: str = ""
    has_api_key: bool = False
    model_chat: str = ""
    model_embedding: str = ""
    llm_max_tokens: int = 1024
    llm_system_prompt_software: str = ""
    llm_system_prompt_workspace: str = ""
    ai_blacklist_software: list[str] = Field(
        default_factory=list, description="AI 批量操作排除的软件名列表"
    )
    ai_blacklist_workspace: list[str] = Field(
        default_factory=list, description="AI 批量操作排除的工作区名列表"
    )


class LLMConfigUpdate(BaseModel):
    """更新 LLM 配置"""

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    model_chat: str | None = None
    model_embedding: str | None = None
    llm_max_tokens: int | None = None
    llm_system_prompt_software: str | None = None
    llm_system_prompt_workspace: str | None = None
    ai_blacklist_software: list[str] | None = None
    ai_blacklist_workspace: list[str] | None = None
