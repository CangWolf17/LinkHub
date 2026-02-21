"""
Phase 3 验证测试脚本
模块 D: Auto-Installer (上传→解压→启发式寻址→入库→ChromaDB 索引)
语义搜索: ChromaDB 向量搜索、重建索引、索引统计
"""

import io
import json
import os
import shutil
import time
import urllib.error
import urllib.request
import uuid
import zipfile

BASE = "http://127.0.0.1:8147"

passed = 0
failed = 0


# ── HTTP 工具 ─────────────────────────────────────────────


def api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    """JSON API 调用。"""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return resp.status, {"_raw": raw.decode(errors="replace")[:200]}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return e.code, {"_raw": raw.decode(errors="replace")[:200]}


def upload_file(
    path: str, filename: str, file_bytes: bytes, content_type: str = "application/zip"
) -> tuple[int, dict]:
    """Multipart form-data 文件上传（无第三方依赖）。"""
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
    body = io.BytesIO()

    # file part
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    )
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(file_bytes)
    body.write(b"\r\n")

    # closing boundary
    body.write(f"--{boundary}--\r\n".encode())

    data = body.getvalue()

    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(data)),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return resp.status, {"_raw": raw.decode(errors="replace")[:500]}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return e.code, {"_raw": raw.decode(errors="replace")[:500]}


def test(
    name: str,
    expected_status: int,
    method: str,
    path: str,
    body=None,
    check=None,
    *,
    upload=None,
):
    """
    运行单个测试用例。

    upload: (filename, file_bytes) — 如果提供则使用 multipart 上传。
    """
    global passed, failed

    if upload:
        filename, file_bytes = upload
        status_code, resp = upload_file(path, filename, file_bytes)
    else:
        status_code, resp = api(method, path, body)

    ok = status_code == expected_status
    if check and ok:
        try:
            ok = check(resp)
        except Exception as exc:
            ok = False
            print(f"  Check error: {exc}")
    tag = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"[{tag}] {name}")
    print(f"  Expected: {expected_status}, Got: {status_code}")
    if "detail" in resp:
        print(f"  Detail: {resp['detail']}")
    if not ok:
        print(f"  Response: {json.dumps(resp, ensure_ascii=False, default=str)[:400]}")
    print()
    return resp


# ── 辅助：构建测试用 ZIP ──────────────────────────────────


def make_test_zip(name: str, files: dict[str, bytes]) -> bytes:
    """
    在内存中创建 ZIP，files 是 {相对路径: 内容} 字典。
    返回 zip 的 bytes。
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath, content in files.items():
            zf.writestr(fpath, content)
    return buf.getvalue()


def make_invalid_zip() -> bytes:
    """返回不合法的 ZIP 字节。"""
    return b"PK\x03\x04this-is-not-a-valid-zip-file-at-all-garbage-data-1234567890"


# ══════════════════════════════════════════════════════════
#  START
# ══════════════════════════════════════════════════════════

print("=" * 60)
print("Phase 3 - Auto-Installer & Semantic Search 测试")
print("=" * 60)
print()

# ── 0. 健康检查 ──────────────────────────────────────────
test("健康检查", 200, "GET", "/api/health")

# ══════════════════════════════════════════════════════════
#  模块 D: Auto-Installer 测试
# ══════════════════════════════════════════════════════════

print("─── 模块 D: Auto-Installer ───")
print()

# ── D1. 上传有效 ZIP（含 .exe）──────────────────────────
# 构建一个模拟便携软件的 ZIP:
#   TestSoft/
#     TestSoft.exe          (大文件 → 主程序)
#     uninstall.exe         (应被排除)
#     readme.txt
#     data/helper.exe       (深层小文件)

test_zip_bytes = make_test_zip(
    "TestSoft",
    {
        "TestSoft/TestSoft.exe": b"\x00" * 2048,  # 2KB "主程序"
        "TestSoft/uninstall.exe": b"\x00" * 512,
        "TestSoft/readme.txt": b"This is a test portable software.",
        "TestSoft/data/helper.exe": b"\x00" * 256,
    },
)

resp_install = test(
    "上传有效 ZIP (含 exe)",
    201,
    "POST",
    "/api/installer/upload",
    check=lambda r: (
        r.get("success") is True
        and r.get("software_id")
        and r.get("name")
        and r.get("executable_path", "").endswith(".exe")
        and len(r.get("exe_candidates", []))
        >= 2  # 至少 TestSoft.exe + helper.exe (uninstall 可能被排除)
    ),
    upload=("TestSoft.zip", test_zip_bytes),
)

installed_sw_id = resp_install.get("software_id", "")
installed_dir = resp_install.get("install_dir", "")
installed_exe = resp_install.get("executable_path", "")

# 验证启发式寻址选择了正确的 exe（TestSoft.exe 应被选中，而非 uninstall.exe）
if installed_exe:
    exe_basename = os.path.basename(installed_exe).lower()
    is_correct = "uninstall" not in exe_basename
    tag = "PASS" if is_correct else "FAIL"
    if is_correct:
        passed += 1
    else:
        failed += 1
    print(f"[{tag}] 启发式寻址排除了 uninstall.exe")
    print(f"  选中: {installed_exe}")
    print()

# ── D2. 上传非 ZIP 文件 → 400 ───────────────────────────
test(
    "上传非 ZIP 文件 -> 400",
    400,
    "POST",
    "/api/installer/upload",
    upload=("test.rar", b"not-a-zip-just-raw-bytes"),
)

# ── D3. 上传损坏的 ZIP → 400 ────────────────────────────
test(
    "上传损坏 ZIP -> 400",
    400,
    "POST",
    "/api/installer/upload",
    upload=("BadArchive.zip", make_invalid_zip()),
)

# ── D4. 上传不含 exe 的 ZIP ─────────────────────────────
no_exe_zip = make_test_zip(
    "DocPack",
    {
        "DocPack/readme.txt": b"just docs",
        "DocPack/notes.md": b"# Notes",
        "DocPack/data.json": b'{"key": "value"}',
    },
)

resp_no_exe = test(
    "上传 ZIP 不含 exe (仍应入库但提示手动指定)",
    201,
    "POST",
    "/api/installer/upload",
    check=lambda r: (
        r.get("success") is True
        and r.get("executable_path") == ""
        and "手动指定" in r.get("message", "")
    ),
    upload=("DocPack.zip", no_exe_zip),
)

no_exe_sw_id = resp_no_exe.get("software_id", "")
no_exe_install_dir = resp_no_exe.get("install_dir", "")

# ── D5. 重复上传同名 ZIP → 应自动重命名目录 ─────────────
resp_dup = test(
    "重复上传同名 ZIP -> 自动重命名",
    201,
    "POST",
    "/api/installer/upload",
    check=lambda r: (
        r.get("success") is True and r.get("name") != "TestSoft"  # 应该带数字后缀
    ),
    upload=("TestSoft.zip", test_zip_bytes),
)

dup_sw_id = resp_dup.get("software_id", "")
dup_install_dir = resp_dup.get("install_dir", "")

# ── D6. 验证 SQLite 中有记录 ────────────────────────────
if installed_sw_id:
    test(
        "验证安装记录已存入 SQLite",
        200,
        "GET",
        f"/api/metadata/software/{installed_sw_id}",
        check=lambda r: r.get("name") is not None and r.get("id") == installed_sw_id,
    )

# 小暂停，让 ChromaDB 完成索引
time.sleep(1)

# ══════════════════════════════════════════════════════════
#  语义搜索测试
# ══════════════════════════════════════════════════════════

print("─── 语义搜索 (ChromaDB) ───")
print()

# ── S1. 索引统计 ─────────────────────────────────────────
test(
    "获取索引统计 (应有 software 文档)",
    200,
    "GET",
    "/api/search/stats",
    check=lambda r: r.get("software_count", 0) >= 1,
)

# ── S2. 语义搜索 - 搜全部 ────────────────────────────────
test(
    "语义搜索 (scope=all)",
    200,
    "POST",
    "/api/search",
    body={"query": "test software", "top_k": 10, "scope": "all"},
    check=lambda r: (
        r.get("success") is True
        and r.get("total", 0) >= 1
        and len(r.get("results", [])) >= 1
    ),
)

# ── S3. 语义搜索 - 仅搜软件 ──────────────────────────────
test(
    "语义搜索 (scope=software)",
    200,
    "POST",
    "/api/search",
    body={"query": "TestSoft", "top_k": 5, "scope": "software"},
    check=lambda r: (
        r.get("success") is True
        and all(item.get("type") == "software" for item in r.get("results", []))
    ),
)

# ── S4. 语义搜索 - 仅搜工作区 (当前应为空) ───────────────
test(
    "语义搜索 (scope=workspaces, 当前无数据)",
    200,
    "POST",
    "/api/search",
    body={"query": "project", "top_k": 5, "scope": "workspaces"},
    check=lambda r: r.get("success") is True and r.get("total", 0) == 0,
)

# ── S5. 重建索引 ─────────────────────────────────────────
# 先创建一个工作区记录用于验证 reindex
ws_resp = api(
    "POST",
    "/api/metadata/workspaces",
    {
        "name": "SearchTestWorkspace",
        "directory_path": r"F:\WorkSpace\SearchTest",
        "description": "用于测试语义搜索的工作区",
        "status": "active",
    },
)
ws_id = ws_resp[1].get("id", "")

test(
    "从数据库重建全部向量索引",
    200,
    "POST",
    "/api/search/reindex",
    check=lambda r: (
        r.get("success") is True
        and r.get("software_indexed", 0) >= 1
        and r.get("workspace_indexed", 0) >= 1
    ),
)

time.sleep(1)

# ── S6. reindex 后可搜索到工作区 ──────────────────────────
test(
    "reindex 后搜索工作区",
    200,
    "POST",
    "/api/search",
    body={"query": "语义搜索测试", "top_k": 5, "scope": "workspaces"},
    check=lambda r: r.get("success") is True and r.get("total", 0) >= 1,
)

# ── S7. 搜索结果包含 is_missing 字段 ─────────────────────
test(
    "搜索结果含 is_missing 字段",
    200,
    "POST",
    "/api/search",
    body={"query": "TestSoft", "top_k": 5, "scope": "software"},
    check=lambda r: all("is_missing" in item for item in r.get("results", [{}])),
)

# ── S8. 空查询 -> 422 ────────────────────────────────────
test(
    "空查询 -> 422",
    422,
    "POST",
    "/api/search",
    body={"query": "", "top_k": 5},
)


# ══════════════════════════════════════════════════════════
#  清理测试数据
# ══════════════════════════════════════════════════════════

print("─── 清理测试数据 ───")
print()

# 清理 SQLite 记录
cleanup_ids = [installed_sw_id, no_exe_sw_id, dup_sw_id]
for sid in cleanup_ids:
    if sid:
        api("DELETE", f"/api/metadata/software/{sid}")
if ws_id:
    api("DELETE", f"/api/metadata/workspaces/{ws_id}")

# 清理解压的目录
cleanup_dirs = [installed_dir, no_exe_install_dir, dup_install_dir]
for d in cleanup_dirs:
    if d and os.path.isdir(d):
        try:
            shutil.rmtree(d)
            print(f"  已清理: {d}")
        except OSError as e:
            print(f"  清理失败: {d} -> {e}")

print(f"  清理了 {sum(1 for s in cleanup_ids if s)} 条软件记录")
print(f"  清理了 {1 if ws_id else 0} 条工作区记录")
print()

# ══════════════════════════════════════════════════════════
#  结果汇总
# ══════════════════════════════════════════════════════════

print("=" * 60)
print(f"Phase 3 测试完成: {passed} 通过, {failed} 失败, 共 {passed + failed} 个")
print("=" * 60)

if failed > 0:
    exit(1)
