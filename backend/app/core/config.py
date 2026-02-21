"""
核心配置模块
从 system_settings 表动态加载的配置项在运行时通过数据库读取，
此处仅定义应用启动所需的静态配置。
"""

from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'linkhub.db'}"

# ChromaDB 向量数据库持久化目录
CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")

# ── 服务配置 ──────────────────────────────────────────────
APP_HOST = "127.0.0.1"
APP_PORT = 8147

# ── OS Bridge 白名单默认值 ────────────────────────────────
# 这些默认值仅在 system_settings 表中尚未配置时使用。
# 运行时以数据库中 `allowed_dirs` 的值为准。
DEFAULT_ALLOWED_DIRS: list[str] = [
    r"D:\GreenSoftwares",
    r"F:\WorkSpace",
]

# ── 可执行文件白名单后缀 ──────────────────────────────────
ALLOWED_EXECUTABLE_SUFFIXES: set[str] = {".exe", ".bat", ".cmd", ".lnk"}

# ── 压缩包支持的后缀 ──────────────────────────────────────
ALLOWED_ARCHIVE_SUFFIXES: set[str] = {".zip", ".7z", ".rar"}

# ── 启发式寻址：可执行文件优先关键字 ─────────────────────
EXE_PRIORITY_KEYWORDS: list[str] = [
    "launcher",
    "main",
    "start",
    "run",
    "app",
    "setup",
]
