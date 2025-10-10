import hmac
import time
import json
import hashlib
import datetime
import asyncio
from typing import Dict, Any, Optional
from utilities.my_logging import logger
import httpx
from config.setting import access_key,secret_key

METHOD = "POST"
HOST = "visual.volcengineapi.com"
ENDPOINT = f"https://{HOST}"
REGION = "cn-north-1"
SERVICE = "cv"
VERSION = "2022-08-31"


ACCESS_KEY = access_key
SECRET_KEY = secret_key

# 即梦视频模型的 req_key
REQ_KEY = "jimeng_ti2v_v30_pro"

# ====== V4 签名工具 ======
def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def _get_signing_key(secret_key: str, datestamp: str, region: str, service: str) -> bytes:
    k_date = _sign(secret_key.encode("utf-8"), datestamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "request")
    return k_signing

def _sorted_query(params: Dict[str, str]) -> str:
    # 规范化 Query（值里若含特殊字符，建议先 urlencode 再组装）
    return "&".join(f"{k}={params[k]}" for k in sorted(params))

def _signed_headers_and_auth(query_str: str, body: str, now_utc: datetime.datetime) -> Dict[str, str]:
    x_date = now_utc.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now_utc.strftime("%Y%m%d")
    content_type = "application/json"

    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    signed_headers = "content-type;host;x-content-sha256;x-date"
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{HOST}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    canonical_request = (
        f"{METHOD}\n/\n{query_str}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    algorithm = "HMAC-SHA256"
    credential_scope = f"{datestamp}/{REGION}/{SERVICE}/request"
    string_to_sign = (
        f"{algorithm}\n{x_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = _get_signing_key(SECRET_KEY, datestamp, REGION, SERVICE)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"{algorithm} Credential={ACCESS_KEY}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return {
        "X-Date": x_date,
        "Authorization": authorization,
        "X-Content-Sha256": payload_hash,
        "Content-Type": content_type,
    }

async def _submit_text2video_task(
    client: httpx.AsyncClient,
    prompt: str,
    *,
    frames: int = 121,                # 5s（24*n+1），10s=241
    aspect_ratio: str = "16:9",
    seed: int = -1,
    extra_body: Optional[Dict[str, Any]] = None,
) -> str:
    """
    提交即梦文生视频任务，返回 task_id（使用外部传入的 AsyncClient）
    """
    query = {"Action": "CVSync2AsyncSubmitTask", "Version": VERSION}
    query_str = _sorted_query(query)

    body_dict: Dict[str, Any] = {
        "req_key": REQ_KEY,
        "prompt": prompt,
        "seed": seed,
        "frames": frames,
        "aspect_ratio": aspect_ratio,
    }
    if extra_body:
        body_dict.update(extra_body)

    body = json.dumps(body_dict, separators=(",", ":"))
    headers = _signed_headers_and_auth(query_str, body, datetime.datetime.utcnow())

    resp = await client.post(f"{ENDPOINT}?{query_str}", headers=headers, content=body)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != 10000:
        raise RuntimeError(f"Submit failed: {data}")
    return data["data"]["task_id"]

async def _query_text2video_result(
    client: httpx.AsyncClient,
    task_id: str,
) -> Dict[str, Any]:
    """
    查询任务结果（使用外部传入的 AsyncClient），返回响应 JSON
    """
    query = {"Action": "CVSync2AsyncGetResult", "Version": VERSION}
    query_str = _sorted_query(query)

    body_dict = {"req_key": REQ_KEY, "task_id": task_id}
    body = json.dumps(body_dict, separators=(",", ":"))
    headers = _signed_headers_and_auth(query_str, body, datetime.datetime.utcnow())

    resp = await client.post(f"{ENDPOINT}?{query_str}", headers=headers, content=body)
    resp.raise_for_status()
    return resp.json()

async def get_videos(
    client: httpx.AsyncClient,
    prompt: str,
    *,
    poll_interval_sec: float = 5.0,
    max_wait_sec: float = 600.0,
    # 透传给 _submit_text2video_task 的可选参数：
    frames: int = 121,
    aspect_ratio: str = "16:9",
    seed: int = -1,
    extra_body: Optional[Dict[str, Any]] = None,
) -> str:
    """
    端到端：提交任务 + 轮询查询，最终返回 video_url。
    - client: 复用你的 httpx.AsyncClient 实例（外部创建，便于连接池/代理/重试等统一管理）
    - prompt: 文生视频提示词
    - poll_interval_sec: 轮询间隔
    - max_wait_sec: 最大等待时间
    - frames/aspect_ratio/seed/extra_body: 透传给提交任务接口
    """
    task_id = await _submit_text2video_task(
        client,
        prompt,
        frames=frames,
        aspect_ratio=aspect_ratio,
        seed=seed,
        extra_body=extra_body,
    )

    deadline = time.monotonic() + max_wait_sec
    last_status = None

    while time.monotonic() < deadline:
        res = await _query_text2video_result(client, task_id)
        code = res.get("status")
        msg = res.get("message")
        data = res.get("data") or {}

        status = data.get("status")
        if status != last_status:
            logger.info(f"[poll] status={status}, code={code}, message={msg}")
            last_status = status

        if status == "done":
            video_url = data.get("video_url")
            if not video_url:
                raise RuntimeError(f"Done but no video_url: {res}")
            return video_url
        if status in {"not_found", "expired"}:
            raise RuntimeError(f"Task {status}: {res}")

        await asyncio.sleep(poll_interval_sec)

    raise asyncio.TimeoutError(f"Polling timeout after {max_wait_sec}s (task_id={task_id})")
