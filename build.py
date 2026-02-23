"""
LinkHub 构建脚本
将后端 (FastAPI) + 前端 (Vue 3 dist) 打包。

用法:
    python build.py              # 打包 lite 版（不含 ChromaDB，单文件 exe）
    python build.py --full       # 打包 full 版（含 ChromaDB，onedir + zip）
    python build.py --all        # 同时打包两个版本

输出:
    lite → dist/LinkHub-lite.exe（单文件）
    full → dist/LinkHub/LinkHub.exe（文件夹），同时生成 dist/LinkHub-full.zip
"""

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
DIST_DIR = ROOT / "dist"

PYTHON = sys.executable  # 使用当前 Python 解释器


def _read_version() -> str:
    """从 backend/app/core/config.py 中读取 APP_VERSION。"""
    config_file = ROOT / "backend" / "app" / "core" / "config.py"
    import re

    match = re.search(
        r'APP_VERSION\s*=\s*"([^"]+)"', config_file.read_text(encoding="utf-8")
    )
    if match:
        return match.group(1)
    return "0.0.0"


# UPX 路径（项目内置）
UPX_DIR = ROOT / "tools" / "upx-5.0.1-win64"

# Conda 环境中 PyInstaller 找不到的 DLL
CONDA_LIB_BIN = Path(sys.prefix) / "Library" / "bin"
CONDA_DLLS = [
    "libexpat.dll",
    "libbz2.dll",
    "ffi.dll",
    "sqlite3.dll",
    "zstd.dll",
    "libcrypto-3-x64.dll",
    "libssl-3-x64.dll",
]

# 所有版本都需要排除的无用模块
COMMON_EXCLUDES = [
    "pygments",  # 仅用于 uvicorn 日志着色，非必需
    "setuptools",
    "pkg_resources",
    "_distutils_hack",
    "unittest",
    "test",
    "tkinter",
    "xmlrpc",
    "lib2to3",
    "ensurepip",
    "idlelib",
    "distutils",
]

# 所有版本都需要的 hidden imports
COMMON_HIDDEN_IMPORTS = [
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

# lite 版额外排除的模块（chromadb 全家桶）
LITE_EXCLUDES = [
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
    "numpy",
]

# full 版排除的 chromadb 非必要传递依赖
FULL_EXCLUDES = [
    "kubernetes",  # ~31 MB — chromadb 远程模式才需要
    "sympy",  # ~66 MB — onnxruntime 符号计算，推理不需要
    "mpmath",  # sympy 依赖
    "google.cloud",  # chromadb 云存储
    "azure",  # chromadb 云存储
    "boto3",  # chromadb 云存储
    "botocore",
    "IPython",
    "notebook",
    "sphinx",
    "docutils",
]


def build_frontend():
    """编译 Vue 3 前端为静态文件。"""
    print("=== 构建前端 ===")
    if FRONTEND_DIST.is_dir():
        shutil.rmtree(FRONTEND_DIST)
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True, shell=True)
    assert FRONTEND_DIST.is_dir(), "前端构建失败：dist 目录不存在"
    print(f"前端构建完成: {FRONTEND_DIST}")


def _base_cmd(name: str, variant: str, *, onedir: bool = False):
    """构建 PyInstaller 基础命令行参数列表。"""
    cmd = [
        PYTHON,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir" if onedir else "--onefile",
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
    ]

    # UPX 压缩
    if UPX_DIR.is_dir():
        cmd.extend(["--upx-dir", str(UPX_DIR)])
        print(f"  启用 UPX 压缩: {UPX_DIR}")
    else:
        print("  警告: UPX 未找到，跳过压缩")

    # 添加 Conda 环境中缺失的 DLL
    for dll_name in CONDA_DLLS:
        dll_path = CONDA_LIB_BIN / dll_name
        if dll_path.is_file():
            cmd.extend(["--add-binary", f"{dll_path};."])
        else:
            print(f"  警告: DLL 未找到，跳过: {dll_path}")

    return cmd


def run_pyinstaller(variant: str):
    """
    运行 PyInstaller 打包。
    variant: 'lite' 或 'full'
    """
    is_full = variant == "full"
    name = "LinkHub" if is_full else "LinkHub-lite"
    onedir = is_full  # full 版用 onedir，lite 版保持 onefile
    print(
        f"\n=== 打包 {variant} 版: {name} {'(onedir)' if onedir else '(onefile)'} ==="
    )

    cmd = _base_cmd(name, variant, onedir=onedir)

    # 排除模块
    excludes = list(COMMON_EXCLUDES)
    if is_full:
        excludes.extend(FULL_EXCLUDES)
    else:
        excludes.extend(LITE_EXCLUDES)

    for pkg in excludes:
        cmd.extend(["--exclude-module", pkg])

    # hidden imports
    hidden = list(COMMON_HIDDEN_IMPORTS)
    if is_full:
        hidden.extend(
            [
                # chromadb 默认嵌入函数 (all-MiniLM-L6-v2) 的依赖
                # 这些是延迟导入，PyInstaller 静态分析检测不到
                "onnxruntime",
                "tokenizers",
                "tqdm",
                # chromadb 的 posthog 遥测（通过字符串引用加载）
                "posthog",
                # chromadb 1.5+ 的 Rust 原生绑定（独立包, ~57 MB pyd）
                "chromadb_rust_bindings",
            ]
        )
        # chromadb 内部大量使用字符串引用动态加载子模块（DI 容器），
        # PyInstaller 静态分析无法检测，必须 collect 全部子模块
        cmd.extend(["--collect-submodules", "chromadb"])

    for h in hidden:
        cmd.extend(["--hidden-import", h])

    # 入口文件
    cmd.append(str(BACKEND_DIR / "main.py"))

    print(f"  排除 {len(excludes)} 个无用模块")
    print(f"  注册 {len(hidden)} 个 hidden imports")
    subprocess.run(cmd, check=True)

    if onedir:
        exe = DIST_DIR / name / f"{name}.exe"
    else:
        exe = DIST_DIR / f"{name}.exe"

    assert exe.is_file(), f"打包失败：{exe} 不存在"
    size_mb = exe.stat().st_size / (1024 * 1024)
    print(f"打包完成: {exe} ({size_mb:.1f} MB)")

    # onedir 模式：计算整个文件夹大小
    if onedir:
        folder = DIST_DIR / name
        total = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
        total_mb = total / (1024 * 1024)
        print(f"文件夹总大小: {folder} ({total_mb:.1f} MB)")

    return exe


def create_zip(variant: str, version: str):
    """将 onedir 输出打包为 zip 文件。"""
    name = "LinkHub"
    folder = DIST_DIR / name
    if not folder.is_dir():
        print(f"错误: 文件夹不存在 {folder}")
        return None

    zip_name = f"LinkHub-v{version}-full.zip"
    zip_path = DIST_DIR / zip_name
    print(f"\n=== 创建 ZIP: {zip_name} ===")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                arcname = file.relative_to(DIST_DIR)
                zf.write(file, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"ZIP 打包完成: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def main():
    parser = argparse.ArgumentParser(description="LinkHub 构建工具")
    parser.add_argument(
        "--lite", action="store_true", help="打包 lite 版（不含 ChromaDB，单文件）"
    )
    parser.add_argument(
        "--full", action="store_true", help="打包 full 版（含 ChromaDB）"
    )
    parser.add_argument(
        "--all", action="store_true", help="同时打包 lite + full 两个版本"
    )
    parser.add_argument(
        "--no-frontend", action="store_true", help="跳过前端构建（使用已有 dist）"
    )
    parser.add_argument(
        "--clean", action="store_true", help="清理整个 dist 目录后再构建"
    )
    parser.add_argument(
        "--version", type=str, default=None, help="指定版本号（默认从 config.py 读取）"
    )
    args = parser.parse_args()

    version = args.version or _read_version()
    print(f"构建版本: v{version}")

    # 默认行为：无参数等同于 --lite
    if not args.lite and not args.full and not args.all:
        args.lite = True

    # 构建前端
    if not args.no_frontend:
        build_frontend()
    else:
        assert FRONTEND_DIST.is_dir(), "前端 dist 目录不存在，请先构建前端"
        print("跳过前端构建，使用已有 dist")

    # 清理旧构建
    if args.clean:
        if DIST_DIR.is_dir():
            shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(exist_ok=True)

    if args.all:
        run_pyinstaller("lite")
        run_pyinstaller("full")
        create_zip("full", version)
    elif args.full:
        run_pyinstaller("full")
        create_zip("full", version)
    elif args.lite:
        run_pyinstaller("lite")

    print("\n=== 构建完成 ===")
    for f in sorted(DIST_DIR.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  {f.name} ({size_mb:.1f} MB)")
        elif f.is_dir():
            total = sum(x.stat().st_size for x in f.rglob("*") if x.is_file())
            total_mb = total / (1024 * 1024)
            print(f"  {f.name}/ ({total_mb:.1f} MB, 文件夹)")


if __name__ == "__main__":
    main()
