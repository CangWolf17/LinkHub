"""
核心配置模块
从 system_settings 表动态加载的配置项在运行时通过数据库读取，
此处仅定义应用启动所需的静态配置。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


# ── 目录条目类型 ──────────────────────────────────────────
class _DirEntryRequired(TypedDict):
    """必填字段"""

    path: str
    type: str  # "software" | "workspace"


class DirEntry(_DirEntryRequired, total=False):
    """白名单目录条目：包含路径、类型和可选自定义标签"""

    label: str  # 可选，用户自定义显示名称


# ── 打包模式检测 ──────────────────────────────────────────
IS_FROZEN = getattr(sys, "frozen", False)
"""True when running inside a PyInstaller bundle."""

if IS_FROZEN:
    # PyInstaller 单文件模式: sys._MEIPASS 是临时解压目录
    # exe 所在目录用于持久化数据
    _BUNDLE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    _EXE_DIR = Path(sys.executable).resolve().parent
    # 后端代码在 _MEIPASS/backend/app/... 下
    BASE_DIR = _BUNDLE_DIR / "backend"
    # 持久化数据放在 exe 旁
    DATA_DIR = _EXE_DIR / "data"
    LOG_DIR = _EXE_DIR / "logs"
    # 前端静态文件
    FRONTEND_DIST_DIR = _BUNDLE_DIR / "frontend_dist"
else:
    # 开发模式
    BASE_DIR = Path(__file__).resolve().parent.parent  # backend/app/.. -> backend/
    DATA_DIR = BASE_DIR / "data"
    LOG_DIR = BASE_DIR / "logs"
    FRONTEND_DIST_DIR = BASE_DIR.parent / "frontend" / "dist"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'linkhub.db'}"

# ChromaDB 向量数据库持久化目录
CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")

# ── 服务配置 ──────────────────────────────────────────────
APP_HOST = "127.0.0.1"
_DEFAULT_PORT = 8147


def _load_config_json() -> dict:
    """
    从 config.json 读取用户自定义配置。
    打包模式：exe 同级目录；开发模式：项目根目录。
    """
    if IS_FROZEN:
        config_path = _EXE_DIR / "config.json"
    else:
        config_path = BASE_DIR.parent / "config.json"

    if not config_path.is_file():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("已加载 config.json: %s", config_path)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("config.json 解析失败: %s", e)
        return {}


def _save_config_json(data: dict) -> bool:
    """保存用户配置到 config.json。"""
    if IS_FROZEN:
        config_path = _EXE_DIR / "config.json"
    else:
        config_path = BASE_DIR.parent / "config.json"

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        logger.error("config.json 保存失败: %s", e)
        return False


def get_config_json_path() -> Path:
    """返回 config.json 的路径（供 API 使用）。"""
    if IS_FROZEN:
        return _EXE_DIR / "config.json"
    return BASE_DIR.parent / "config.json"


_user_config = _load_config_json()
APP_PORT = int(_user_config.get("port", _DEFAULT_PORT))

# ── OS Bridge 白名单默认值 ────────────────────────────────
# 这些默认值仅在 system_settings 表中尚未配置时使用。
# 运行时以数据库中 `allowed_dirs` 的值为准。
# 格式: [{"path": "C:\\...", "type": "software"|"workspace"}]
DEFAULT_ALLOWED_DIRS: list[DirEntry] = []


# ── 目录类型常量 ──────────────────────────────────────────
DIR_TYPE_SOFTWARE = "software"
DIR_TYPE_WORKSPACE = "workspace"
VALID_DIR_TYPES = {DIR_TYPE_SOFTWARE, DIR_TYPE_WORKSPACE}

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


# ── allowed_dirs 解析辅助函数 ─────────────────────────────


def parse_allowed_dirs(raw_json: str) -> list[DirEntry]:
    """
    解析 allowed_dirs 的 JSON 字符串，兼容新旧两种格式：
      - 新格式: [{"path": "C:\\...", "type": "software"}, ...]
      - 旧格式: ["C:\\...", "D:\\..."]（回退为 type=software）
    返回规范化的 DirEntry 列表。
    """
    if not raw_json:
        return []
    try:
        parsed = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        logger.warning("allowed_dirs JSON 解析失败: %s", raw_json[:100])
        return []

    if not isinstance(parsed, list):
        return []

    entries: list[DirEntry] = []
    for item in parsed:
        if isinstance(item, dict):
            p = str(item.get("path", "")).strip()
            t = str(item.get("type", DIR_TYPE_SOFTWARE)).strip()
            if p and t in VALID_DIR_TYPES:
                entry = DirEntry(path=p, type=t)
                # 保留可选的自定义标签
                lbl = str(item.get("label", "")).strip()
                if lbl:
                    entry["label"] = lbl
                entries.append(entry)
        elif isinstance(item, str):
            # 向后兼容：旧格式字符串数组，默认视为 software
            p = item.strip()
            if p:
                entries.append(DirEntry(path=p, type=DIR_TYPE_SOFTWARE))
    return entries


def filter_dirs_by_type(entries: list[DirEntry], dir_type: str) -> list[Path]:
    """按类型过滤目录条目，返回 Path 列表。"""
    return [Path(e["path"]) for e in entries if e["type"] == dir_type]


def all_dir_paths(entries: list[DirEntry]) -> list[Path]:
    """返回所有目录条目的 Path 列表（不过滤类型）。"""
    return [Path(e["path"]) for e in entries]


def serialize_allowed_dirs(entries: list[DirEntry]) -> str:
    """将 DirEntry 列表序列化为 JSON 字符串。"""
    return json.dumps(entries, ensure_ascii=False)
