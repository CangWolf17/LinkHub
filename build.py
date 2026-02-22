"""
LinkHub 构建脚本
将后端 (FastAPI) + 前端 (Vue 3 dist) 打包为单个 exe。

用法:
    python build.py              # 打包 lite 版（不含 ChromaDB）
    python build.py --full       # 打包 full 版（含 ChromaDB 语义搜索）
    python build.py --all        # 同时打包两个版本

输出: dist/LinkHub-lite.exe 和/或 dist/LinkHub.exe
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
DIST_DIR = ROOT / "dist"

PYTHON = sys.executable  # 使用当前 Python 解释器


def build_frontend():
    """编译 Vue 3 前端为静态文件。"""
    print("=== 构建前端 ===")
    if FRONTEND_DIST.is_dir():
        shutil.rmtree(FRONTEND_DIST)
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True, shell=True)
    assert FRONTEND_DIST.is_dir(), "前端构建失败：dist 目录不存在"
    print(f"前端构建完成: {FRONTEND_DIST}")


def run_pyinstaller(variant: str):
    """
    运行 PyInstaller 打包。
    variant: 'lite' 或 'full'
    """
    name = "LinkHub" if variant == "full" else "LinkHub-lite"
    print(f"\n=== 打包 {variant} 版: {name}.exe ===")

    # Conda 环境中 PyInstaller 找不到的 DLL（Windows 特有问题）
    conda_lib_bin = Path(sys.prefix) / "Library" / "bin"
    conda_dlls = [
        "libexpat.dll",  # pyexpat 依赖
        "libbz2.dll",  # _bz2 依赖
        "ffi.dll",  # _ctypes 依赖
        "sqlite3.dll",  # _sqlite3 依赖
        "zstd.dll",  # zstandard 依赖
        "libcrypto-3-x64.dll",  # ssl 依赖
        "libssl-3-x64.dll",  # ssl 依赖
    ]

    # 基础参数
    cmd = [
        PYTHON,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name",
        name,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(ROOT / "build" / variant),
        "--specpath",
        str(ROOT / "build"),
        # 添加后端源码
        "--add-data",
        f"{BACKEND_DIR / 'app'};backend/app",
        # 添加前端 dist
        "--add-data",
        f"{FRONTEND_DIST};frontend_dist",
        # 隐藏控制台窗口
        "--noconsole",
        # 图标（如果有的话）
    ]

    # 添加 Conda 环境中缺失的 DLL
    for dll_name in conda_dlls:
        dll_path = conda_lib_bin / dll_name
        if dll_path.is_file():
            cmd.extend(["--add-binary", f"{dll_path};."])
        else:
            print(f"  警告: DLL 未找到，跳过: {dll_path}")

    # hidden imports - 所有版本都需要的
    hidden = [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "aiosqlite",
        "sqlalchemy.dialects.sqlite",
        "multipart",
    ]

    if variant == "lite":
        # 排除 chromadb 及其重量级依赖
        for pkg in [
            "chromadb",
            "onnxruntime",
            "tokenizers",
            "tqdm",
            "posthog",
            "opentelemetry",
            "sentence_transformers",
            "torch",
            "torchvision",
            "torchaudio",
            "transformers",
            "huggingface_hub",
        ]:
            cmd.extend(["--exclude-module", pkg])
    else:
        hidden.extend(
            [
                "chromadb",
                "chromadb.config",
            ]
        )

    for h in hidden:
        cmd.extend(["--hidden-import", h])

    # 入口文件
    cmd.append(str(BACKEND_DIR / "main.py"))

    subprocess.run(cmd, check=True)

    exe = DIST_DIR / f"{name}.exe"
    assert exe.is_file(), f"打包失败：{exe} 不存在"
    size_mb = exe.stat().st_size / (1024 * 1024)
    print(f"打包完成: {exe} ({size_mb:.1f} MB)")
    return exe


def main():
    parser = argparse.ArgumentParser(description="LinkHub 构建工具")
    parser.add_argument(
        "--full", action="store_true", help="打包 full 版（含 ChromaDB）"
    )
    parser.add_argument(
        "--all", action="store_true", help="同时打包 lite + full 两个版本"
    )
    args = parser.parse_args()

    # 构建前端
    build_frontend()

    # 清理旧构建
    if DIST_DIR.is_dir():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(exist_ok=True)

    if args.all:
        run_pyinstaller("lite")
        run_pyinstaller("full")
    elif args.full:
        run_pyinstaller("full")
    else:
        run_pyinstaller("lite")

    print("\n=== 构建完成 ===")
    for f in DIST_DIR.iterdir():
        if f.suffix == ".exe":
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  {f.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
