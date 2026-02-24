"""
系统管理路由 (System Router)

职责:
  - 提供初始化状态检测（前端向导弹窗触发依据）
  - 提供 allowed_dirs 的读写管理
  - 提供配置导入/导出
  - 提供端口配置
  - 提供服务关闭端点（优雅终止整个进程）
"""

import json
import logging
import os
from typing import Union

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    APP_PORT,
    DEFAULT_ALLOWED_DIRS,
    VALID_DIR_TYPES,
    DirEntry,
    _load_config_json,
    _save_config_json,
    parse_allowed_dirs,
    serialize_allowed_dirs,
)
from app.core.database import get_db
from app.models.models import PortableSoftware, SystemSetting, Workspace


class UpdateAllowedDirsRequest(BaseModel):
    """更新白名单目录请求体，兼容新旧格式。"""

    allowed_dirs: list[Union[dict, str]] = Field(
        default_factory=list,
        description='目录列表，支持 [{"path": "...", "type": "software"}] 或 ["path1", "path2"]',
    )


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get(
    "/init-status",
    summary="获取系统初始化状态",
)
async def get_init_status(db: AsyncSession = Depends(get_db)):
    """
    检测系统是否已完成首次初始化配置。

    未初始化的判定条件（满足任意一条）:
      - allowed_dirs 为空列表
      - llm_base_url 为空

    前端据此决定是否弹出设置向导。
    """
    keys = ["allowed_dirs", "llm_base_url"]
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(keys)))
    settings = {row.key: row.value for row in result.scalars().all()}

    # 解析 allowed_dirs（兼容新旧格式）
    entries = parse_allowed_dirs(settings.get("allowed_dirs", ""))

    llm_base_url = settings.get("llm_base_url", "").strip()
    dirs_empty = len(entries) == 0
    llm_not_configured = not llm_base_url

    needs_setup = dirs_empty or llm_not_configured

    return {
        "needs_setup": needs_setup,
        "allowed_dirs": entries,
        "llm_configured": not llm_not_configured,
    }


@router.get(
    "/allowed-dirs",
    summary="获取当前白名单目录列表",
)
async def get_allowed_dirs(db: AsyncSession = Depends(get_db)):
    """返回当前配置的 allowed_dirs 列表（含类型信息）。"""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    entries = parse_allowed_dirs(setting.value if setting else "")
    return {"allowed_dirs": entries}


@router.put(
    "/allowed-dirs",
    summary="更新白名单目录列表",
)
async def update_allowed_dirs(
    payload: UpdateAllowedDirsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    更新 allowed_dirs 配置。
    请求体: { "allowed_dirs": [{"path": "C:/path1", "type": "software"}, ...] }
    也兼容旧格式: { "allowed_dirs": ["C:/path1", "D:/path2"] }
    """
    raw_dirs = payload.allowed_dirs

    # 规范化为 DirEntry 列表
    entries: list[DirEntry] = []
    for item in raw_dirs:
        if isinstance(item, dict):
            p = str(item.get("path", "")).strip()
            t = str(item.get("type", "software")).strip()
            if p and t in VALID_DIR_TYPES:
                entry = DirEntry(path=p, type=t)
                lbl = str(item.get("label", "")).strip() if item.get("label") else ""
                if lbl:
                    entry["label"] = lbl
                entries.append(entry)
        elif isinstance(item, str):
            p = item.strip()
            if p:
                entries.append(DirEntry(path=p, type="software"))

    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    new_value = serialize_allowed_dirs(entries)

    if setting:
        setting.value = new_value
    else:
        db.add(SystemSetting(key="allowed_dirs", value=new_value))

    await db.flush()
    await db.commit()
    logger.info("allowed_dirs 已更新: %s", entries)
    return {"allowed_dirs": entries}


# ── 端口配置 ──────────────────────────────────────────────


@router.get(
    "/port-config",
    summary="获取当前端口配置",
)
async def get_port_config():
    """返回当前运行端口和 config.json 中的配置。"""
    user_config = _load_config_json()
    return {
        "current_port": APP_PORT,
        "configured_port": user_config.get("port", 8147),
    }


class UpdatePortRequest(BaseModel):
    port: int = Field(ge=1024, le=65535, description="端口号 (1024-65535)")


@router.put(
    "/port-config",
    summary="更新端口配置（需重启生效）",
)
async def update_port_config(payload: UpdatePortRequest):
    """更新 config.json 中的端口配置。修改后需重启 LinkHub 才能生效。"""
    user_config = _load_config_json()
    user_config["port"] = payload.port
    if _save_config_json(user_config):
        logger.info("端口配置已更新为 %d (需重启生效)", payload.port)
        return {
            "message": f"端口已设置为 {payload.port}，重启 LinkHub 后生效",
            "configured_port": payload.port,
            "current_port": APP_PORT,
        }
    return {
        "message": "保存失败",
        "configured_port": APP_PORT,
        "current_port": APP_PORT,
    }


# ── 配置导入/导出 ────────────────────────────────────────

# 导出时排除的敏感 key
_SENSITIVE_KEYS = {"llm_api_key"}


@router.get(
    "/export-config",
    summary="导出所有配置",
)
async def export_config(db: AsyncSession = Depends(get_db)):
    """
    导出 system_settings 表中的所有配置为 JSON。
    同时导出软件和工作区的元数据（描述、标签等），便于迁移。
    API Key 等敏感字段会被排除。
    """
    result = await db.execute(select(SystemSetting))
    settings = {}
    for row in result.scalars().all():
        if row.key in _SENSITIVE_KEYS:
            continue
        # allowed_dirs 特殊处理：解析为结构化数据
        if row.key == "allowed_dirs":
            settings[row.key] = parse_allowed_dirs(row.value)
        else:
            settings[row.key] = row.value

    # 导出软件元数据
    sw_result = await db.execute(select(PortableSoftware))
    software_meta = []
    for sw in sw_result.scalars().all():
        entry: dict = {
            "name": sw.name,
            "executable_path": sw.executable_path,
        }
        if sw.install_dir:
            entry["install_dir"] = sw.install_dir
        if sw.description:
            entry["description"] = sw.description
        if sw.tags:
            entry["tags"] = sw.tags
        software_meta.append(entry)

    # 导出工作区元数据
    ws_result = await db.execute(select(Workspace))
    workspace_meta = []
    for ws in ws_result.scalars().all():
        entry = {
            "name": ws.name,
            "directory_path": ws.directory_path,
        }
        if ws.description:
            entry["description"] = ws.description
        if ws.status and ws.status != "active":
            entry["status"] = ws.status
        if ws.deadline:
            entry["deadline"] = ws.deadline.isoformat()
        workspace_meta.append(entry)

    if software_meta:
        settings["_software_metadata"] = software_meta
    if workspace_meta:
        settings["_workspace_metadata"] = workspace_meta

    settings["_export_version"] = "3"
    settings["_export_source"] = "LinkHub"
    return settings


@router.post(
    "/import-config",
    summary="导入配置",
)
async def import_config(
    config: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    导入配置 JSON，批量覆盖 system_settings 表。
    忽略敏感字段和元数据字段。

    兼容处理:
      - v1 格式: allowed_dirs 为字符串数组 ["C:/path1"] -> 自动转为 [{"path": "...", "type": "software"}]
      - 缺失字段: 不覆盖已有值（仅导入文件中存在的 key）
      - 未知字段: 静默跳过（不报错）
    """
    # 过滤掉元数据字段和敏感字段
    skip_keys = _SENSITIVE_KEYS | {
        "_export_version",
        "_export_source",
        "_software_metadata",
        "_workspace_metadata",
    }
    imported_keys = []
    skipped_keys = []

    # ── 处理软件元数据 ──
    sw_meta = config.get("_software_metadata")
    sw_updated = 0
    if isinstance(sw_meta, list):
        for item in sw_meta:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            exe_path = str(item.get("executable_path", "")).strip()
            if not name or not exe_path:
                continue
            # 按 name + executable_path 精确匹配
            sw_result = await db.execute(
                select(PortableSoftware).where(
                    PortableSoftware.name == name,
                    PortableSoftware.executable_path == exe_path,
                )
            )
            sw = sw_result.scalar_one_or_none()
            if sw is None:
                continue
            changed = False
            if item.get("description") and not sw.description:
                sw.description = item["description"]
                changed = True
            if item.get("tags") and not sw.tags:
                sw.tags = item["tags"]
                changed = True
            if item.get("install_dir") and not sw.install_dir:
                sw.install_dir = item["install_dir"]
                changed = True
            if changed:
                sw_updated += 1
        if sw_updated:
            imported_keys.append(f"_software_metadata({sw_updated})")

    # ── 处理工作区元数据 ──
    ws_meta = config.get("_workspace_metadata")
    ws_updated = 0
    if isinstance(ws_meta, list):
        for item in ws_meta:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            dir_path = str(item.get("directory_path", "")).strip()
            if not name or not dir_path:
                continue
            ws_result = await db.execute(
                select(Workspace).where(
                    Workspace.name == name,
                    Workspace.directory_path == dir_path,
                )
            )
            ws = ws_result.scalar_one_or_none()
            if ws is None:
                continue
            changed = False
            if item.get("description") and not ws.description:
                ws.description = item["description"]
                changed = True
            if item.get("status") and ws.status == "active":
                ws.status = item["status"]
                changed = True
            if item.get("deadline") and not ws.deadline:
                from datetime import datetime as _dt

                try:
                    ws.deadline = _dt.fromisoformat(item["deadline"])
                    changed = True
                except (ValueError, TypeError):
                    pass
            if changed:
                ws_updated += 1
        if ws_updated:
            imported_keys.append(f"_workspace_metadata({ws_updated})")

    for key, value in config.items():
        if key in skip_keys:
            continue
        if key.startswith("_"):
            skipped_keys.append(key)
            continue

        # allowed_dirs 特殊处理：兼容新旧格式
        if key == "allowed_dirs" and isinstance(value, list):
            # 规范化: 可能是 ["path1", "path2"] 或 [{"path": "...", "type": "..."}]
            normalized = []
            for item in value:
                if isinstance(item, dict):
                    p = str(item.get("path", "")).strip()
                    t = str(item.get("type", "software")).strip()
                    if p and t in VALID_DIR_TYPES:
                        normalized.append({"path": p, "type": t})
                elif isinstance(item, str):
                    p = item.strip()
                    if p:
                        normalized.append({"path": p, "type": "software"})
            str_value = serialize_allowed_dirs(normalized)
        elif isinstance(value, (dict, list)):
            str_value = json.dumps(value, ensure_ascii=False)
        elif value is None:
            # 跳过 null 值，不覆盖已有配置
            skipped_keys.append(key)
            continue
        else:
            str_value = str(value)

        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str_value
        else:
            db.add(SystemSetting(key=key, value=str_value))
        imported_keys.append(key)

    await db.flush()
    await db.commit()
    logger.info(
        "配置已导入，共 %d 项: %s (跳过: %s)",
        len(imported_keys),
        imported_keys,
        skipped_keys,
    )
    return {
        "message": f"已导入 {len(imported_keys)} 项配置",
        "imported_keys": imported_keys,
    }


@router.post(
    "/shutdown",
    summary="关闭 LinkHub 服务",
)
async def shutdown_server():
    """
    优雅关闭整个 LinkHub 进程。

    先返回 HTTP 200，然后向自身进程发送终止信号。
    打包模式使用 os._exit 确保无僵尸进程残留；
    开发模式发送 SIGINT 让 uvicorn 正常走 shutdown 流程。
    """
    import asyncio

    logger.info("收到关闭请求，服务将在 1 秒后终止...")

    async def _delayed_shutdown():
        await asyncio.sleep(1)
        logger.info("LinkHub 正在终止进程...")
        # 统一使用 os._exit 确保 Windows 上可靠退出
        os._exit(0)

    asyncio.get_event_loop().create_task(_delayed_shutdown())
    return {"message": "服务正在关闭..."}
