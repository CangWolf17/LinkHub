"""
Pydantic Schema - 模块 D: Auto-Installer 的请求/响应模型
处理压缩包上传、解压、启发式寻址的全流程。
"""

from pydantic import BaseModel, Field


class InstallerUploadResponse(BaseModel):
    """安装器上传处理完成响应"""

    success: bool
    software_id: str = Field("", description="新创建的软件记录 ID")
    name: str = Field("", description="检测到的软件名称")
    executable_path: str = Field("", description="启发式寻址找到的核心可执行文件路径")
    install_dir: str = Field("", description="解压后的安装目录")
    description: str = Field("", description="LLM 生成的软件描述（可能为空）")
    exe_candidates: list[str] = Field(
        default_factory=list, description="扫描到的所有可执行文件候选列表"
    )
    message: str = Field("", description="处理状态消息")


class InstallerStatusResponse(BaseModel):
    """安装进度查询响应（预留，当前为同步处理）"""

    stage: str = Field("", description="当前阶段: uploading/extracting/analyzing/done")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="进度 0~1")
    message: str = ""
