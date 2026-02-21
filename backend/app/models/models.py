"""
SQLAlchemy ORM 模型定义
三张核心表: portable_software, workspaces, system_settings
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """ORM 基类"""

    pass


class PortableSoftware(Base):
    """便携软件表"""

    __tablename__ = "portable_software"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    executable_path: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    tags: Mapped[str | None] = mapped_column(Text, default=None)  # JSON 字符串存储
    icon_path: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Workspace(Base):
    """工作区表"""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    directory_path: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active / archived / completed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SystemSetting(Base):
    """
    动态配置表 (Key-Value)
    预设 Keys:
      - llm_base_url, llm_api_key, model_chat, model_embedding
      - allowed_dirs (JSON 数组，OS Bridge 白名单目录)
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
