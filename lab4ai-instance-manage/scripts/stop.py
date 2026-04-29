import sys
import os
import json
import httpx

API_URL = "https://tools.lab4ai.cn/api/v1/tools/instance_stop/invoke"


def stop_instance(server_id: str) -> dict:
    """调用新 API 关闭实例，返回标准化结果。"""

    phone = os.getenv("LAB4AI_PHONE")
    password = os.getenv("LAB4AI_PASSWORD")

    if not phone or not password:
        return {"status": "failed", "msg": "环境变量 LAB4AI_PHONE / LAB4AI_PASSWORD 未设置"}

    if not server_id:
        return {"status": "failed", "msg": "未提供 serverId，无法关闭"}

    payload = {
        "phone": phone,
        "password": password,
        "serverId": server_id,
    }

    try:
        resp = httpx.post(API_URL, json=payload, timeout=30.0)
        res_json = resp.json()
    except Exception as e:
        return {"status": "failed", "msg": f"请求异常: {str(e)}"}

    if res_json.get("code") != 0:
        return {"status": "failed", "msg": res_json.get("message") or res_json.get("msg", "关机失败")}

    data = res_json.get("data", {})

    return {
        "status": "success",
        "serverId": server_id,
        "startTime": data.get("startTime"),
        "stopTime": data.get("stopTime"),
    }


def _load_env():
    """从 .env 加载环境变量。通过 __file__ 自定位，不依赖 $HOME。"""
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _env_candidates = [
        "/workspace/.openclaw/.env",                              # 绝对路径优先
        os.path.join(_script_dir, "..", "..", "..", ".env"),      # skills/../../../.env 兜底
    ]
    for env_path in _env_candidates:
        env_path = os.path.normpath(env_path)
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
            break


if __name__ == "__main__":
    # Inline Override: 兜底 HOME=/workspace，防止沙箱 /root 符号链接安全拦截
    os.environ.setdefault("HOME", "/workspace")
    _load_env()

    server_id = sys.argv[1] if len(sys.argv) > 1 else ""
    result = stop_instance(server_id)
    print(json.dumps(result, ensure_ascii=False))
