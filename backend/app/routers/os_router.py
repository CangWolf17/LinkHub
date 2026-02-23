"""
模块 A: 操作系统安全桥接 (OS Bridge Router) - 高危模块

安全措施:
  1. 白名单目录校验 — 目标路径必须位于允许的目录下
  2. 路径遍历防护 — resolve() 后重新校验，拒绝 ../ 等穿越攻击
  3. 可执行文件后缀白名单 — 仅允许 .exe/.bat/.cmd/.lnk
  4. 非阻塞执行 — subprocess.Popen + DETACHED_PROCESS，绝不阻塞主线程
"""

import base64
import ctypes
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    ALLOWED_EXECUTABLE_SUFFIXES,
    all_dir_paths,
    parse_allowed_dirs,
)
from app.core.database import get_db
from app.models.models import PortableSoftware, SystemSetting
from app.schemas.os_schemas import OSActionResponse, OSTargetRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/os", tags=["OS Bridge"])


# ── 内部工具函数 ─────────────────────────────────────────


async def _get_allowed_dirs(db: AsyncSession) -> list[Path]:
    """
    从 system_settings 表动态读取白名单目录。
    返回所有类型的目录（software + workspace），用于路径安全校验。
    """
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == "allowed_dirs")
    )
    row = result.scalar_one_or_none()

    if row:
        entries = parse_allowed_dirs(row)
        if entries:
            return [p.resolve() for p in all_dir_paths(entries)]

    return []


def _validate_path_within_whitelist(target: Path, allowed_dirs: list[Path]) -> bool:
    """
    校验 resolved 后的绝对路径是否位于白名单目录之下。
    使用 is_relative_to() 进行严格的父子关系判断。
    """
    for allowed in allowed_dirs:
        try:
            if target.is_relative_to(allowed):
                return True
        except (ValueError, TypeError):
            continue
    return False


def _sanitize_and_resolve(raw_path: str) -> Path:
    """
    路径净化:
      - 拒绝包含 .. 的原始输入（初筛）
      - 使用 resolve() 获取规范化绝对路径（最终防线）
    """
    # 初筛: 检查原始字符串中的遍历特征
    if ".." in raw_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径中不允许包含 '..'",
        )

    path = Path(raw_path)

    # 必须是绝对路径
    if not path.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供绝对路径",
        )

    # resolve() 会消除所有符号链接和 ./ ../ 得到真实路径
    return path.resolve()


# ── API 端点 ─────────────────────────────────────────────


@router.post(
    "/launch",
    response_model=OSActionResponse,
    summary="安全拉起可执行程序",
)
async def launch_executable(
    req: OSTargetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    以非阻塞方式启动目标可执行文件。
    执行前需通过: 白名单目录校验 + 可执行后缀校验 + 文件存在性校验。
    """
    resolved = _sanitize_and_resolve(req.target_path)
    allowed_dirs = await _get_allowed_dirs(db)

    # 白名单校验
    if not _validate_path_within_whitelist(resolved, allowed_dirs):
        logger.warning("拒绝越界访问: %s", resolved)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"路径不在允许的白名单目录内: {resolved}",
        )

    # 后缀校验
    if resolved.suffix.lower() not in ALLOWED_EXECUTABLE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不允许执行此类型文件: {resolved.suffix}",
        )

    # 存在性校验
    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标文件不存在: {resolved}",
        )

    # 非阻塞拉起 (Windows: DETACHED_PROCESS)
    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )

        subprocess.Popen(
            [str(resolved)],
            cwd=str(resolved.parent),
            creationflags=creation_flags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        logger.info("已拉起程序: %s", resolved)

        # 更新软件的最近使用时间
        try:
            result = await db.execute(
                select(PortableSoftware).where(
                    PortableSoftware.executable_path == str(resolved)
                )
            )
            sw = result.scalar_one_or_none()
            if sw:
                sw.last_used_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception as e:
            logger.debug("更新 last_used_at 失败（非阻塞）: %s", e)

        return OSActionResponse(
            success=True,
            message="程序已成功启动",
            target_path=str(resolved),
        )

    except OSError as e:
        # WinError 740: 需要提升权限 — 使用 ShellExecuteW runas 提权重试
        if sys.platform == "win32" and getattr(e, "winerror", None) == 740:
            logger.info("程序需要管理员权限，尝试提权启动: %s", resolved)
            try:
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", str(resolved), None, str(resolved.parent), 1
                )
                if ret > 32:
                    logger.info("已提权拉起程序: %s", resolved)

                    # 更新最近使用时间
                    try:
                        result = await db.execute(
                            select(PortableSoftware).where(
                                PortableSoftware.executable_path == str(resolved)
                            )
                        )
                        sw = result.scalar_one_or_none()
                        if sw:
                            sw.last_used_at = datetime.now(timezone.utc)
                            await db.commit()
                    except Exception as ex:
                        logger.debug("更新 last_used_at 失败（非阻塞）: %s", ex)

                    return OSActionResponse(
                        success=True,
                        message="程序已以管理员权限启动",
                        target_path=str(resolved),
                    )
                else:
                    logger.warning(
                        "提权启动失败 (ShellExecute 返回 %d): %s", ret, resolved
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"提权启动失败，用户可能取消了 UAC 提示 (code={ret})",
                    )
            except HTTPException:
                raise
            except Exception as ex:
                logger.error("提权启动异常: %s -> %s", resolved, ex)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"提权启动失败: {ex}",
                )

        logger.error("拉起程序失败: %s -> %s", resolved, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动程序失败: {e}",
        )


@router.post(
    "/open-dir",
    response_model=OSActionResponse,
    summary="用系统资源管理器打开目录",
)
async def open_directory(
    req: OSTargetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    调用系统资源管理器打开目标目录。
    同样需要通过白名单校验。
    """
    resolved = _sanitize_and_resolve(req.target_path)
    allowed_dirs = await _get_allowed_dirs(db)

    # 白名单校验
    if not _validate_path_within_whitelist(resolved, allowed_dirs):
        logger.warning("拒绝越界目录访问: %s", resolved)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"路径不在允许的白名单目录内: {resolved}",
        )

    # 存在性校验
    if not resolved.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标目录不存在: {resolved}",
        )

    # 使用 explorer 打开目录 (Windows)
    try:
        if sys.platform == "win32":
            # 使用 start explorer 避免窗口被后台进程遮挡
            subprocess.Popen(
                ["cmd", "/c", "start", "explorer", str(resolved)],
                creationflags=subprocess.CREATE_NO_WINDOW,
                close_fds=True,
            )
        else:
            # Linux / macOS 兼容 (虽然项目定位为 Windows)
            opener = "xdg-open" if sys.platform.startswith("linux") else "open"
            subprocess.Popen([opener, str(resolved)], close_fds=True)

        logger.info("已打开目录: %s", resolved)
        return OSActionResponse(
            success=True,
            message="已在资源管理器中打开目录",
            target_path=str(resolved),
        )

    except OSError as e:
        logger.error("打开目录失败: %s -> %s", resolved, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"打开目录失败: {e}",
        )


# ── 目录浏览端点（文件夹选择器） ─────────────────────────


class BrowseDirRequest(BaseModel):
    """目录浏览请求"""

    path: Optional[str] = Field(
        None,
        description="要浏览的目录绝对路径，为空时返回驱动器列表（Windows）",
    )


class DirItem(BaseModel):
    """单条目录项"""

    name: str
    path: str
    is_dir: bool = True


class BrowseDirResponse(BaseModel):
    """目录浏览响应"""

    current: str
    parent: Optional[str] = None
    items: list[DirItem]


@router.post(
    "/browse-dir",
    response_model=BrowseDirResponse,
    summary="浏览本地目录（文件夹选择器）",
)
async def browse_directory(req: BrowseDirRequest):
    """
    列出指定目录下的子目录（不列出文件）。
    当 path 为空/null 时，Windows 下返回驱动器列表。
    此端点不受白名单限制（因为用户就是在选择要添加的白名单目录）。
    """
    # 如果没有指定路径，返回驱动器列表（Windows）
    if not req.path or not req.path.strip():
        if sys.platform == "win32":
            drives: list[DirItem] = []
            # 遍历 A-Z 盘符
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.isdir(drive):
                    drives.append(DirItem(name=f"{letter}:", path=drive))
            return BrowseDirResponse(current="", parent=None, items=drives)
        else:
            # Linux/macOS: 返回根目录
            return BrowseDirResponse(
                current="/",
                parent=None,
                items=[
                    DirItem(name=d, path=f"/{d}")
                    for d in sorted(os.listdir("/"))
                    if os.path.isdir(f"/{d}")
                ],
            )

    raw = req.path.strip()

    # 路径安全检查
    if ".." in raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径中不允许包含 '..'",
        )

    target = Path(raw)
    if not target.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供绝对路径",
        )

    resolved = target.resolve()
    if not resolved.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目录不存在: {resolved}",
        )

    # 获取父目录
    parent = str(resolved.parent) if resolved.parent != resolved else None

    # 列出子目录
    items: list[DirItem] = []
    try:
        for entry in sorted(resolved.iterdir(), key=lambda e: e.name.lower()):
            if entry.is_dir() and not entry.name.startswith("."):
                items.append(DirItem(name=entry.name, path=str(entry)))
    except PermissionError:
        logger.warning("无权限访问目录: %s", resolved)
        # 返回空列表但不报错，让用户知道这个目录不可访问

    return BrowseDirResponse(
        current=str(resolved),
        parent=parent,
        items=items,
    )


# ── 图标提取端点 ─────────────────────────────────────────


class IconRequest(BaseModel):
    """图标提取请求"""

    executable_path: str = Field(..., description="可执行文件绝对路径")
    size: int = Field(32, description="图标尺寸 (16/32/48)")


class IconResponse(BaseModel):
    """图标提取响应"""

    success: bool
    icon_base64: str = Field("", description="PNG 图标的 base64 编码")
    message: str = ""


def _extract_icon_windows(exe_path: str, size: int = 32) -> str | None:
    """
    Windows 平台提取 exe 图标，返回 base64 编码的 PNG。
    使用 ctypes 调用 Win32 API: SHGetFileInfoW 或直接用 Pillow 读取 ico。
    """
    try:
        from PIL import Image

        # 方法1: 使用 icoextract 从 PE 资源读取（纯 Python）
        try:
            import struct

            with open(exe_path, "rb") as f:
                # 读取 PE 头查找 icon 资源
                data = f.read()

            # 尝试在 exe 中找到 ICO 数据（简化方案：使用 shell32 提取）
            raise ImportError("fallback to shell method")
        except (ImportError, Exception):
            pass

        # 方法2: 使用 Win32 API 提取图标
        try:
            # 使用 shell32.ExtractIconExW 提取图标句柄
            shell32 = ctypes.windll.shell32
            large_icons = (ctypes.c_void_p * 1)()
            small_icons = (ctypes.c_void_p * 1)()

            count = shell32.ExtractIconExW(exe_path, 0, large_icons, small_icons, 1)
            if count == 0:
                return None

            # 选择合适大小的图标
            hicon = large_icons[0] if size >= 32 else small_icons[0]
            if not hicon:
                hicon = large_icons[0] or small_icons[0]

            if not hicon:
                return None

            # 使用 GDI+ 将 HICON 转换为 bitmap
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            class ICONINFO(ctypes.Structure):
                _fields_ = [
                    ("fIcon", ctypes.c_bool),
                    ("xHotspot", ctypes.c_ulong),
                    ("yHotspot", ctypes.c_ulong),
                    ("hbmMask", ctypes.c_void_p),
                    ("hbmColor", ctypes.c_void_p),
                ]

            class BITMAP(ctypes.Structure):
                _fields_ = [
                    ("bmType", ctypes.c_long),
                    ("bmWidth", ctypes.c_long),
                    ("bmHeight", ctypes.c_long),
                    ("bmWidthBytes", ctypes.c_long),
                    ("bmPlanes", ctypes.c_ushort),
                    ("bmBitsPixel", ctypes.c_ushort),
                    ("bmBits", ctypes.c_void_p),
                ]

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.c_ulong),
                    ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long),
                    ("biPlanes", ctypes.c_ushort),
                    ("biBitCount", ctypes.c_ushort),
                    ("biCompression", ctypes.c_ulong),
                    ("biSizeImage", ctypes.c_ulong),
                    ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", ctypes.c_ulong),
                    ("biClrImportant", ctypes.c_ulong),
                ]

            # 获取图标信息
            icon_info = ICONINFO()
            if not user32.GetIconInfo(hicon, ctypes.byref(icon_info)):
                user32.DestroyIcon(large_icons[0])
                if small_icons[0]:
                    user32.DestroyIcon(small_icons[0])
                return None

            # 获取 bitmap 信息
            bmp = BITMAP()
            gdi32.GetObjectW(
                icon_info.hbmColor, ctypes.sizeof(BITMAP), ctypes.byref(bmp)
            )

            width = bmp.bmWidth
            height = bmp.bmHeight

            # 准备 BITMAPINFO
            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # top-down
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0  # BI_RGB

            # 获取位图数据
            hdc = user32.GetDC(0)
            buf_size = width * height * 4
            buf = ctypes.create_string_buffer(buf_size)

            gdi32.GetDIBits(
                hdc,
                icon_info.hbmColor,
                0,
                height,
                buf,
                ctypes.byref(bmi),
                0,  # DIB_RGB_COLORS
            )

            user32.ReleaseDC(0, hdc)

            # 转换 BGRA -> RGBA
            raw = bytearray(buf.raw)
            for i in range(0, len(raw), 4):
                raw[i], raw[i + 2] = raw[i + 2], raw[i]

            # 创建 PIL Image
            img = Image.frombuffer(
                "RGBA", (width, height), bytes(raw), "raw", "RGBA", 0, 1
            )

            # 调整大小
            if img.width != size or img.height != size:
                img = img.resize((size, size), Image.LANCZOS)

            # 转为 base64 PNG
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

            # 清理
            gdi32.DeleteObject(icon_info.hbmColor)
            gdi32.DeleteObject(icon_info.hbmMask)
            user32.DestroyIcon(large_icons[0])
            if small_icons[0]:
                user32.DestroyIcon(small_icons[0])

            return b64

        except Exception as e:
            logger.debug("Win32 API 图标提取失败: %s", e)
            return None

    except ImportError:
        logger.debug("Pillow 未安装，无法提取图标")
        return None


@router.post(
    "/extract-icon",
    response_model=IconResponse,
    summary="提取可执行文件的图标",
)
async def extract_icon(
    req: IconRequest,
    db: AsyncSession = Depends(get_db),
):
    """提取 exe 文件的图标并返回 base64 编码的 PNG。"""
    exe_path = req.executable_path.strip()

    if not exe_path:
        return IconResponse(success=False, message="路径为空")

    resolved = Path(exe_path)
    if not resolved.is_file():
        return IconResponse(success=False, message="文件不存在")

    if sys.platform != "win32":
        return IconResponse(success=False, message="仅支持 Windows 平台")

    size = max(16, min(req.size, 256))

    icon_b64 = _extract_icon_windows(str(resolved), size)
    if icon_b64:
        return IconResponse(success=True, icon_base64=icon_b64)
    else:
        return IconResponse(success=False, message="无法提取图标")
