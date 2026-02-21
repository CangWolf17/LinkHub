"""
模块 B: 元数据与死链管理 (Metadata CRUD Router)

职责:
  - 便携软件 (PortableSoftware) 的增删改查
  - 工作区 (Workspace) 的增删改查
  - GET 列表时对路径执行 os.path.exists() 死链检测，标记 is_missing
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import PortableSoftware, SystemSetting, Workspace
from app.schemas.metadata_schemas import (
    SoftwareCreate,
    SoftwareListResponse,
    SoftwareResponse,
    SoftwareUpdate,
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceScanResponse,
    WorkspaceUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metadata", tags=["Metadata CRUD"])


# ── 内部工具函数 ─────────────────────────────────────────


def _check_path_missing(path_str: str) -> bool:
    """轻量级死链检测: 检查本地路径是否已失效。"""
    try:
        return not Path(path_str).exists()
    except (OSError, ValueError):
        return True


def _to_software_response(item: PortableSoftware) -> SoftwareResponse:
    """将 ORM 对象转换为响应模型，附加 is_missing 标记。"""
    return SoftwareResponse(
        id=item.id,
        name=item.name,
        executable_path=item.executable_path,
        description=item.description,
        tags=item.tags,
        icon_path=item.icon_path,
        is_missing=_check_path_missing(item.executable_path),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_workspace_response(item: Workspace) -> WorkspaceResponse:
    """将 ORM 对象转换为响应模型，附加 is_missing 标记。"""
    return WorkspaceResponse(
        id=item.id,
        name=item.name,
        directory_path=item.directory_path,
        description=item.description,
        deadline=item.deadline,
        status=item.status,
        is_missing=_check_path_missing(item.directory_path),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# ══════════════════════════════════════════════════════════
#  便携软件 CRUD
# ══════════════════════════════════════════════════════════


@router.post(
    "/software",
    response_model=SoftwareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建便携软件记录",
)
async def create_software(
    req: SoftwareCreate,
    db: AsyncSession = Depends(get_db),
):
    """新增一条便携软件记录到数据库。"""
    item = PortableSoftware(
        name=req.name,
        executable_path=req.executable_path,
        description=req.description,
        tags=req.tags,
        icon_path=req.icon_path,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("创建软件记录: %s (%s)", item.name, item.id)
    return _to_software_response(item)


@router.get(
    "/software",
    response_model=SoftwareListResponse,
    summary="获取便携软件列表",
)
async def list_software(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    search: str | None = Query(None, description="按名称模糊搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取便携软件列表，返回时自动检测死链。"""
    query = select(PortableSoftware)

    if search:
        query = query.where(PortableSoftware.name.ilike(f"%{search}%"))

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询
    query = query.order_by(PortableSoftware.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return SoftwareListResponse(
        items=[_to_software_response(item) for item in items],
        total=total,
    )


@router.delete(
    "/software/cleanup/dead-links",
    summary="批量清理死链软件记录",
)
async def cleanup_dead_software(
    db: AsyncSession = Depends(get_db),
):
    """扫描所有软件记录，删除路径已失效的条目。"""
    result = await db.execute(select(PortableSoftware))
    items = result.scalars().all()

    removed = []
    for item in items:
        if _check_path_missing(item.executable_path):
            removed.append(
                {"id": item.id, "name": item.name, "path": item.executable_path}
            )
            await db.delete(item)

    await db.commit()
    logger.info("清理死链软件: 共 %d 条", len(removed))
    return {"removed_count": len(removed), "removed": removed}


@router.get(
    "/software/{software_id}",
    response_model=SoftwareResponse,
    summary="获取单个便携软件详情",
)
async def get_software(
    software_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取单个便携软件，附带死链检测。"""
    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    return _to_software_response(item)


@router.put(
    "/software/{software_id}",
    response_model=SoftwareResponse,
    summary="更新便携软件记录",
)
async def update_software(
    software_id: str,
    req: SoftwareUpdate,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 更新便携软件记录（仅更新非 None 字段）。"""
    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("更新软件记录: %s (%s)", item.name, item.id)
    return _to_software_response(item)


@router.delete(
    "/software/{software_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除便携软件记录",
)
async def delete_software(
    software_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 删除便携软件记录。"""
    result = await db.execute(
        select(PortableSoftware).where(PortableSoftware.id == software_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"软件记录不存在: {software_id}",
        )

    await db.delete(item)
    await db.commit()
    logger.info("删除软件记录: %s (%s)", item.name, item.id)


# ══════════════════════════════════════════════════════════
#  工作区 CRUD
# ══════════════════════════════════════════════════════════


@router.post(
    "/workspaces",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建工作区记录",
)
async def create_workspace(
    req: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
):
    """新增一条工作区记录到数据库。"""
    item = Workspace(
        name=req.name,
        directory_path=req.directory_path,
        description=req.description,
        deadline=req.deadline,
        status=req.status,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("创建工作区: %s (%s)", item.name, item.id)
    return _to_workspace_response(item)


@router.get(
    "/workspaces",
    response_model=WorkspaceListResponse,
    summary="获取工作区列表",
)
async def list_workspaces(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    search: str | None = Query(None, description="按名称模糊搜索"),
    status_filter: str | None = Query(None, alias="status", description="按状态过滤"),
    db: AsyncSession = Depends(get_db),
):
    """获取工作区列表，返回时自动检测死链。"""
    query = select(Workspace)

    if search:
        query = query.where(Workspace.name.ilike(f"%{search}%"))
    if status_filter:
        query = query.where(Workspace.status == status_filter)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页查询
    query = query.order_by(Workspace.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return WorkspaceListResponse(
        items=[_to_workspace_response(item) for item in items],
        total=total,
    )


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="获取单个工作区详情",
)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取单个工作区，附带死链检测。"""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作区记录不存在: {workspace_id}",
        )

    return _to_workspace_response(item)


@router.put(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="更新工作区记录",
)
async def update_workspace(
    workspace_id: str,
    req: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 更新工作区记录（仅更新非 None 字段）。"""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作区记录不存在: {workspace_id}",
        )

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(item)
    await db.commit()

    logger.info("更新工作区: %s (%s)", item.name, item.id)
    return _to_workspace_response(item)


@router.delete(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除工作区记录",
)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 删除工作区记录。"""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作区记录不存在: {workspace_id}",
        )

    await db.delete(item)
    await db.commit()
    logger.info("删除工作区: %s (%s)", item.name, item.id)


@router.delete(
    "/workspaces/cleanup/dead-links",
    summary="批量清理死链工作区记录",
)
async def cleanup_dead_workspaces(
    db: AsyncSession = Depends(get_db),
):
    """扫描所有工作区记录，删除目录已失效的条目。"""
    result = await db.execute(select(Workspace))
    items = result.scalars().all()

    removed = []
    for item in items:
        if _check_path_missing(item.directory_path):
            removed.append(
                {"id": item.id, "name": item.name, "path": item.directory_path}
            )
            await db.delete(item)

    await db.commit()
    logger.info("清理死链工作区: 共 %d 条", len(removed))
    return {"removed_count": len(removed), "removed": removed}


@router.post(
    "/workspaces/scan",
    response_model=WorkspaceScanResponse,
    summary="扫描目录，批量导入已有工作区",
)
async def scan_workspaces(
    db: AsyncSession = Depends(get_db),
):
    """
    遍历 system_settings 中 allowed_dirs 配置的所有路径。
    将每个一级子目录视为一个独立工作区导入（状态默认 active）。

    规则:
      - 仅扫描直接子目录（非软件目录的其他路径）
      - 若 directory_path 已存在于数据库，跳过
      - 若同名工作区已存在，跳过
    """
    # 读取白名单目录列表
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "allowed_dirs")
    )
    setting = result.scalar_one_or_none()
    scan_dirs: list[Path] = []
    if setting and setting.value:
        try:
            raw = json.loads(setting.value)
            if isinstance(raw, list):
                scan_dirs = [Path(d) for d in raw if d]
        except (json.JSONDecodeError, TypeError):
            pass

    if not scan_dirs:
        return WorkspaceScanResponse(
            success=True,
            imported=0,
            skipped=0,
            details=[],
            message="未配置 allowed_dirs，请先在设置中配置白名单目录",
        )

    # 读取数据库中已有的 directory_path
    existing_result = await db.execute(select(Workspace.directory_path))
    existing_paths: set[str] = {r for r in existing_result.scalars().all() if r}

    imported = 0
    skipped = 0
    details: list[dict] = []

    for base_dir in scan_dirs:
        if not base_dir.exists() or not base_dir.is_dir():
            continue

        for subdir in sorted(base_dir.iterdir()):
            if not subdir.is_dir():
                continue

            dir_path_str = str(subdir)
            ws_name = subdir.name

            # 路径去重
            if dir_path_str in existing_paths:
                skipped += 1
                details.append(
                    {"name": ws_name, "status": "skipped", "reason": "路径已存在"}
                )
                continue

            # 同名去重
            name_check = await db.execute(
                select(Workspace).where(Workspace.name == ws_name)
            )
            if name_check.scalar_one_or_none() is not None:
                skipped += 1
                details.append(
                    {"name": ws_name, "status": "skipped", "reason": "同名已存在"}
                )
                continue

            try:
                item = Workspace(
                    name=ws_name,
                    directory_path=dir_path_str,
                    status="active",
                )
                db.add(item)
                await db.flush()
                await db.commit()

                existing_paths.add(dir_path_str)
                imported += 1
                details.append(
                    {"name": ws_name, "status": "imported", "path": dir_path_str}
                )
                logger.info("工作区扫描导入: %s", dir_path_str)
            except Exception as e:
                await db.rollback()
                skipped += 1
                details.append({"name": ws_name, "status": "skipped", "reason": str(e)})
                logger.warning("工作区导入失败: %s -> %s", ws_name, e)

    return WorkspaceScanResponse(
        success=True,
        imported=imported,
        skipped=skipped,
        details=details,
        message=f"扫描完成：新导入 {imported} 个工作区，跳过 {skipped} 个",
    )
