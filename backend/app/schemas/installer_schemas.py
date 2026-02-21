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


class ScanDirsResponse(BaseModel):
    """目录扫描导入响应"""

    success: bool
    imported: int = Field(0, description="本次新导入的软件数量")
    skipped: int = Field(0, description="已存在跳过的软件数量")
    failed: int = Field(0, description="处理失败的数量")
    details: list[dict] = Field(default_factory=list, description="每个导入项的详情")
    message: str = ""
