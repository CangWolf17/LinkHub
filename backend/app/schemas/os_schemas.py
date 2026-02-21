"""
Pydantic Schema - OS Bridge 模块的请求/响应模型
"""

from pydantic import BaseModel, Field


class OSTargetRequest(BaseModel):
    """OS 操作请求体"""

    target_path: str = Field(
        ...,
        description="目标的绝对路径",
        examples=[r"D:\GreenSoftwares\VSCode\Code.exe"],
    )


class OSActionResponse(BaseModel):
    """OS 操作统一响应"""

    success: bool
    message: str
    target_path: str | None = None
