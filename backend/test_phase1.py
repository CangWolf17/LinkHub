"""Phase 1 验证测试脚本"""

import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8147"


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


def test(name: str, expected_status: int, method: str, path: str, body=None):
    status, resp = api(method, path, body)
    ok = "PASS" if status == expected_status else "FAIL"
    print(f"[{ok}] {name}")
    print(f"  Expected: {expected_status}, Got: {status}")
    if "detail" in resp:
        detail = resp["detail"]
        if isinstance(detail, str):
            print(f"  Detail: {detail}")
        elif isinstance(detail, list) and detail:
            print(f"  Detail: {detail[0].get('msg', detail)}")
    elif "message" in resp:
        print(f"  Message: {resp['message']}")
    print()


print("=" * 60)
print("Phase 1 - OS Bridge 安全校验测试")
print("=" * 60)
print()

# 健康检查
test("Health Check", 200, "GET", "/api/health")

# Test 1: 路径遍历 (..)
test(
    "Path Traversal (..) -> 400",
    400,
    "POST",
    "/api/os/launch",
    {"target_path": "D:\\GreenSoftwares\\..\\Windows\\System32\\cmd.exe"},
)

# Test 2: 非白名单路径
test(
    "Non-whitelisted path -> 403",
    403,
    "POST",
    "/api/os/launch",
    {"target_path": "C:\\Windows\\System32\\cmd.exe"},
)

# Test 3: 非法后缀
test(
    "Invalid extension (.txt) -> 400",
    400,
    "POST",
    "/api/os/launch",
    {"target_path": "D:\\GreenSoftwares\\readme.txt"},
)

# Test 4: 相对路径
test(
    "Relative path -> 400",
    400,
    "POST",
    "/api/os/launch",
    {"target_path": "GreenSoftwares\\app.exe"},
)

# Test 5: 文件不存在 (路径合法但文件不在)
test(
    "File not found -> 404",
    404,
    "POST",
    "/api/os/launch",
    {"target_path": "D:\\GreenSoftwares\\nonexistent.exe"},
)

# Test 6: open-dir 非白名单
test(
    "open-dir non-whitelisted -> 403",
    403,
    "POST",
    "/api/os/open-dir",
    {"target_path": "C:\\Windows"},
)

# Test 7: open-dir 目录不存在
test(
    "open-dir not found -> 404",
    404,
    "POST",
    "/api/os/open-dir",
    {"target_path": "D:\\GreenSoftwares\\NoSuchDir"},
)

# Test 8: 查看 API 文档是否可访问
test("OpenAPI docs", 200, "GET", "/docs")

print("=" * 60)
print("所有安全校验测试完成")
print("=" * 60)
