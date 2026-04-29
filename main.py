import os
import json
import hashlib
import hmac
import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# ── 环境变量 ──────────────────────────────────────────────
FEISHU_APP_ID       = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET   = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_ENCRYPT_KEY  = os.environ.get("FEISHU_ENCRYPT_KEY", "")
ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")

CLAUDE_MODEL        = "claude-sonnet-4-20250514"
FEISHU_API_BASE     = "https://open.feishu.cn/open-apis"

# 去重
processed_message_ids: set[str] = set()


async def get_tenant_access_token() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        )
        return resp.json().get("tenant_access_token", "")


async def send_feishu_message(receive_id: str, receive_id_type: str, text: str) -> None:
    token = await get_tenant_access_token()
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{FEISHU_API_BASE}/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            },
        )


async def call_claude(user_message: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        data = resp.json()
        if "content" in data and data["content"]:
            return data["content"][0].get("text", "（Claude 无响应）")
        return f"调用出错：{data.get('error', {}).get('message', '未知错误')}"


@app.get("/")
async def health_check():
    return {"status": "ok", "message": "飞书 Claude 机器人运行中 🚀"}


@app.post("/webhook/feishu")
async def feishu_webhook(request: Request):
    body_bytes = await request.body()
    payload = json.loads(body_bytes)

    # ── URL 验证（直接返回 challenge，不校验 token）──────────
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload.get("challenge", "")})

    # ── 处理消息事件 ─────────────────────────────────────
    header = payload.get("header", {})
    event  = payload.get("event", {})

    if header.get("event_type") != "im.message.receive_v1":
        return JSONResponse({"code": 0})

    message      = event.get("message", {})
    message_id   = message.get("message_id", "")
    message_type = message.get("message_type", "")
    chat_type    = message.get("chat_type", "")

    if message_id in processed_message_ids:
        return JSONResponse({"code": 0})
    processed_message_ids.add(message_id)

    if message_type != "text":
        return JSONResponse({"code": 0})

    try:
        content_obj = json.loads(message.get("content", "{}"))
        user_text   = content_obj.get("text", "").strip()
    except Exception:
        return JSONResponse({"code": 0})

    if chat_type == "group":
        import re
        user_text = re.sub(r"@\S+", "", user_text).strip()
        if not user_text:
            return JSONResponse({"code": 0})

    if chat_type == "p2p":
        receive_id      = event.get("sender", {}).get("sender_id", {}).get("open_id", "")
        receive_id_type = "open_id"
    else:
        receive_id      = message.get("chat_id", "")
        receive_id_type = "chat_id"

    async def reply():
        answer = await call_claude(user_text)
        await send_feishu_message(receive_id, receive_id_type, answer)

    asyncio.create_task(reply())

    return JSONResponse({"code": 0})
