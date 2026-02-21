"""
Phase 2 验证测试脚本
模块 B: Metadata CRUD (软件 + 工作区) + 死链检测
模块 C: LLM Gateway 配置管理 (不测试实际 LLM 调用，仅测试配置和未配置时的错误处理)
"""

import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8147"

passed = 0
failed = 0


def api(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
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


def test(
    name: str, expected_status: int, method: str, path: str, body=None, check=None
):
    global passed, failed
    status_code, resp = api(method, path, body)
    ok = status_code == expected_status
    if check and ok:
        ok = check(resp)
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
        print(f"  Response: {json.dumps(resp, ensure_ascii=False, default=str)[:300]}")
    print()
    return resp


print("=" * 60)
print("Phase 2 - Metadata CRUD & LLM Gateway 测试")
print("=" * 60)
print()

# ══════════════════════════════════════════════════════════
#  软件 CRUD 测试
# ══════════════════════════════════════════════════════════

print("─── 便携软件 CRUD ───")
print()

# 创建软件 (路径不存在，但 CRUD 不校验路径存在性)
resp = test(
    "创建软件记录",
    201,
    "POST",
    "/api/metadata/software",
    {
        "name": "TestApp",
        "executable_path": r"D:\GreenSoftwares\TestApp\test.exe",
        "description": "测试应用",
        "tags": '["test", "demo"]',
    },
)
software_id = resp.get("id", "")

# 获取列表
test(
    "获取软件列表",
    200,
    "GET",
    "/api/metadata/software",
    check=lambda r: r.get("total", 0) >= 1,
)

# 获取单个
if software_id:
    test(
        "获取单个软件 (含 is_missing 标记)",
        200,
        "GET",
        f"/api/metadata/software/{software_id}",
        check=lambda r: r.get("is_missing") is True,  # 路径不存在，应为 True
    )

# 更新
if software_id:
    test(
        "更新软件名称",
        200,
        "PUT",
        f"/api/metadata/software/{software_id}",
        {"name": "TestApp-Updated"},
        check=lambda r: r.get("name") == "TestApp-Updated",
    )

# 搜索
test(
    "按名称搜索软件",
    200,
    "GET",
    "/api/metadata/software?search=Updated",
    check=lambda r: r.get("total", 0) >= 1,
)

# 获取不存在的 ID
test(
    "获取不存在的软件 -> 404",
    404,
    "GET",
    "/api/metadata/software/nonexistent-id",
)

# 删除
if software_id:
    test(
        "删除软件记录",
        204,
        "DELETE",
        f"/api/metadata/software/{software_id}",
    )

# 验证删除后获取 -> 404
if software_id:
    test(
        "删除后获取 -> 404",
        404,
        "GET",
        f"/api/metadata/software/{software_id}",
    )

# ══════════════════════════════════════════════════════════
#  工作区 CRUD 测试
# ══════════════════════════════════════════════════════════

print("─── 工作区 CRUD ───")
print()

# 创建工作区
resp = test(
    "创建工作区记录",
    201,
    "POST",
    "/api/metadata/workspaces",
    {
        "name": "TestProject",
        "directory_path": r"F:\WorkSpace\TestProject",
        "description": "测试工作区",
        "status": "active",
    },
)
workspace_id = resp.get("id", "")

# 获取列表
test(
    "获取工作区列表",
    200,
    "GET",
    "/api/metadata/workspaces",
    check=lambda r: r.get("total", 0) >= 1,
)

# 获取单个 (含死链)
if workspace_id:
    test(
        "获取单个工作区 (含 is_missing 标记)",
        200,
        "GET",
        f"/api/metadata/workspaces/{workspace_id}",
        check=lambda r: r.get("is_missing") is True,
    )

# 更新
if workspace_id:
    test(
        "更新工作区状态",
        200,
        "PUT",
        f"/api/metadata/workspaces/{workspace_id}",
        {"status": "archived"},
        check=lambda r: r.get("status") == "archived",
    )

# 按状态过滤
test(
    "按状态过滤工作区",
    200,
    "GET",
    "/api/metadata/workspaces?status=archived",
    check=lambda r: r.get("total", 0) >= 1,
)

# 删除
if workspace_id:
    test(
        "删除工作区记录",
        204,
        "DELETE",
        f"/api/metadata/workspaces/{workspace_id}",
    )

# ══════════════════════════════════════════════════════════
#  死链批量清理测试
# ══════════════════════════════════════════════════════════

print("─── 死链批量清理 ───")
print()

# 先创建几条带无效路径的数据
api(
    "POST",
    "/api/metadata/software",
    {
        "name": "GhostApp1",
        "executable_path": r"D:\GreenSoftwares\Ghost1\phantom.exe",
    },
)
api(
    "POST",
    "/api/metadata/software",
    {
        "name": "GhostApp2",
        "executable_path": r"D:\GreenSoftwares\Ghost2\phantom.exe",
    },
)

test(
    "批量清理死链软件",
    200,
    "DELETE",
    "/api/metadata/software/cleanup/dead-links",
    check=lambda r: r.get("removed_count", 0) >= 2,
)

# 工作区也测一下
api(
    "POST",
    "/api/metadata/workspaces",
    {
        "name": "GhostWorkspace",
        "directory_path": r"F:\WorkSpace\NonExistent",
    },
)

test(
    "批量清理死链工作区",
    200,
    "DELETE",
    "/api/metadata/workspaces/cleanup/dead-links",
    check=lambda r: r.get("removed_count", 0) >= 1,
)

# ══════════════════════════════════════════════════════════
#  LLM Gateway 测试 (配置管理 + 未配置时的保护)
# ══════════════════════════════════════════════════════════

print("─── LLM Gateway ───")
print()

# 获取当前 LLM 配置
test(
    "获取 LLM 配置 (脱敏)",
    200,
    "GET",
    "/api/llm/config",
    check=lambda r: "has_api_key" in r,
)

# 更新 LLM 配置 (仅更新 base_url，不设 key)
test(
    "更新 LLM 配置 (部分更新)",
    200,
    "PUT",
    "/api/llm/config",
    {"llm_base_url": "http://localhost:11434/v1", "model_chat": "test-model"},
    check=lambda r: r.get("llm_base_url") == "http://localhost:11434/v1",
)

# Chat 未配置 API Key -> 503
test(
    "Chat 未配 API Key -> 503",
    503,
    "POST",
    "/api/llm/chat",
    {"messages": [{"role": "user", "content": "hello"}]},
)

# 测试连接 (未配 key -> 503)
test(
    "测试连接 (未配 key) -> 503",
    503,
    "POST",
    "/api/llm/test-connection",
)

# ══════════════════════════════════════════════════════════
#  验证 Pydantic 校验
# ══════════════════════════════════════════════════════════

print("─── 请求体校验 ───")
print()

# 空 name
test(
    "创建软件 name 为空 -> 422",
    422,
    "POST",
    "/api/metadata/software",
    {"name": "", "executable_path": "C:\\test.exe"},
)

# 缺少必填字段
test(
    "创建工作区缺少必填字段 -> 422",
    422,
    "POST",
    "/api/metadata/workspaces",
    {"name": "test"},
)

# Chat messages 为空列表
test(
    "Chat messages 为空 -> 422",
    422,
    "POST",
    "/api/llm/chat",
    {"messages": []},
)

# ══════════════════════════════════════════════════════════
#  结果汇总
# ══════════════════════════════════════════════════════════

print("=" * 60)
print(f"Phase 2 测试完成: {passed} 通过, {failed} 失败, 共 {passed + failed} 个")
print("=" * 60)

if failed > 0:
    exit(1)
