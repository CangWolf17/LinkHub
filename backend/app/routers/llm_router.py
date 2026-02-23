"""
模块 C: 通用大模型网关 (Universal LLM Gateway)

职责:
  - 动态从 system_settings 加载 LLM 配置（base_url, api_key, model 等）
  - 实例化 OpenAI 兼容 Client
  - 提供 Chat / Embed / Extract 三个任务级端点
  - 所有响应包含 raw_response 字段，供前端调试监控
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_value
from app.core.database import get_db
from app.core.llm_helpers import (
    get_async_openai_client,
    load_llm_config,
)
from app.models.models import SystemSetting
from app.schemas.llm_schemas import (
    ChatRequest,
    ChatResponse,
    EmbedRequest,
    EmbedResponse,
    ExtractRequest,
    ExtractResponse,
    LLMConfigResponse,
    LLMConfigUpdate,
    LLMErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM Gateway"])


# ── LLM 配置管理端点 ────────────────────────────────────


@router.get(
    "/config",
    response_model=LLMConfigResponse,
    summary="获取当前 LLM 配置（脱敏）",
)
async def get_llm_config(
    db: AsyncSession = Depends(get_db),
):
    """返回 LLM 配置状态，API Key 仅返回是否已设置。"""
    config = await load_llm_config(db)
    return LLMConfigResponse(
        llm_base_url=config.get("llm_base_url", ""),
        has_api_key=bool(config.get("llm_api_key", "").strip()),
        model_chat=config.get("model_chat", ""),
        model_embedding=config.get("model_embedding", ""),
        llm_max_tokens=int(config.get("llm_max_tokens", "1024")),
        llm_system_prompt_software=config.get("llm_system_prompt_software", ""),
        llm_system_prompt_workspace=config.get("llm_system_prompt_workspace", ""),
    )


@router.put(
    "/config",
    response_model=LLMConfigResponse,
    summary="更新 LLM 配置",
)
async def update_llm_config(
    req: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新 LLM 配置项（仅更新非 None 字段）。llm_api_key 自动加密存储。"""
    update_map = req.model_dump(exclude_unset=True)

    for key, value in update_map.items():
        # llm_api_key 写入前先加密
        if key == "llm_api_key" and value:
            value = encrypt_value(value)

        # DB system_settings 所有 value 都是 str，pydantic 可能传入 int
        db_value = str(value) if not isinstance(value, str) else value

        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = db_value
        else:
            db.add(SystemSetting(key=key, value=db_value))

    await db.flush()
    await db.commit()
    logger.info("LLM 配置已更新: %s", list(update_map.keys()))

    # 返回更新后的配置
    config = await load_llm_config(db)
    return LLMConfigResponse(
        llm_base_url=config.get("llm_base_url", ""),
        has_api_key=bool(config.get("llm_api_key", "").strip()),
        model_chat=config.get("model_chat", ""),
        model_embedding=config.get("model_embedding", ""),
        llm_max_tokens=int(config.get("llm_max_tokens", "1024")),
        llm_system_prompt_software=config.get("llm_system_prompt_software", ""),
        llm_system_prompt_workspace=config.get("llm_system_prompt_workspace", ""),
    )


@router.get(
    "/health",
    summary="LLM 健康检查（不消耗 token）",
)
async def llm_health_check(
    db: AsyncSession = Depends(get_db),
):
    """
    轻量级 LLM 连通性检查：调用 /models 端点列出可用模型。
    不发送任何 chat 请求，不消耗 token。
    """
    config = await load_llm_config(db)

    try:
        client = get_async_openai_client(config)
    except HTTPException:
        raise

    try:
        models_resp = await client.models.list()
        model_ids = [m.id for m in models_resp.data[:10]]  # 最多返回前 10 个模型名
        return {
            "success": True,
            "message": f"LLM 服务连接正常，可用模型 {len(models_resp.data)} 个",
            "models": model_ids,
        }
    except Exception as e:
        logger.error("LLM 健康检查失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 连接失败: {e}",
        )


@router.post(
    "/test-connection",
    summary="测试 LLM 连接",
)
async def test_llm_connection(
    db: AsyncSession = Depends(get_db),
):
    """使用当前配置测试 LLM 连接是否可用（发送一次短对话，消耗少量 token）。"""
    config = await load_llm_config(db)

    try:
        client = get_async_openai_client(config)
    except HTTPException:
        raise

    model = config.get("model_chat", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_chat 为空。",
        )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi, reply with 'OK' only."}],
            max_tokens=5,
            temperature=0,
        )
        content = response.choices[0].message.content if response.choices else ""
        return {
            "success": True,
            "message": f"连接成功，模型 {model} 响应正常",
            "model_reply": content,
        }

    except Exception as e:
        logger.error("LLM 连接测试失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM 连接失败: {e}",
        )


# ── Chat 端点 ────────────────────────────────────────────


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={503: {"model": LLMErrorResponse}},
    summary="标准多轮对话",
)
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    调用 Chat 模型进行多轮对话。
    使用 system_settings 中的 model_chat 配置。
    """
    config = await load_llm_config(db)
    client = get_async_openai_client(config)

    model = config.get("model_chat", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_chat 为空。",
        )

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": req.temperature,
        }
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens

        response = await client.chat.completions.create(**kwargs)

        # 构建 raw_response
        raw = (
            response.model_dump() if hasattr(response, "model_dump") else str(response)
        )

        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        logger.info("Chat 完成: model=%s, tokens=%s", model, usage)
        return ChatResponse(
            success=True,
            content=content,
            model=response.model or model,
            usage=usage,
            raw_response=raw,
        )

    except Exception as e:
        logger.error("Chat 调用失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM Chat 调用失败，请检查配置和网络连接。",
        )


# ── Chat Streaming 端点 (SSE) ────────────────────────────


@router.post(
    "/chat/stream",
    summary="流式多轮对话 (SSE)",
)
async def chat_stream(
    req: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    调用 Chat 模型进行流式对话，通过 Server-Sent Events 逐 token 返回。
    事件类型:
      - data: {"delta": "..."} — 增量文本片段
      - data: {"done": true, "content": "...", "usage": {...}} — 完成信号
      - data: {"error": "..."} — 错误信号
    """
    config = await load_llm_config(db)
    client = get_async_openai_client(config)

    model = config.get("model_chat", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_chat 为空。",
        )

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async def event_generator():
        full_content = ""
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": req.temperature,
                "stream": True,
            }
            if req.max_tokens is not None:
                kwargs["max_tokens"] = req.max_tokens

            stream = await client.chat.completions.create(**kwargs)

            async for chunk in stream:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    full_content += delta
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"

            # 完成信号
            yield f"data: {json.dumps({'done': True, 'content': full_content, 'model': model}, ensure_ascii=False)}\n\n"
            logger.info(
                "Chat Stream 完成: model=%s, length=%d", model, len(full_content)
            )

        except Exception as e:
            logger.error("Chat Stream 失败: %s", e)
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Embed 端点 ───────────────────────────────────────────


@router.post(
    "/embed",
    response_model=EmbedResponse,
    responses={503: {"model": LLMErrorResponse}},
    summary="文本转向量",
)
async def embed(
    req: EmbedRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    调用 Embedding 模型将文本转为向量。
    使用 system_settings 中的 model_embedding 配置。
    """
    config = await load_llm_config(db)
    client = get_async_openai_client(config)

    model = config.get("model_embedding", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_embedding 为空。",
        )

    try:
        response = await client.embeddings.create(
            model=model,
            input=req.texts,
        )

        raw = (
            response.model_dump() if hasattr(response, "model_dump") else str(response)
        )

        embeddings = [item.embedding for item in response.data]

        logger.info("Embed 完成: model=%s, count=%d", model, len(embeddings))
        return EmbedResponse(
            success=True,
            embeddings=embeddings,
            model=response.model or model,
            raw_response=raw,
        )

    except Exception as e:
        logger.error("Embed 调用失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM Embed 调用失败，请检查配置和网络连接。",
        )


# ── Extract 端点 ─────────────────────────────────────────


@router.post(
    "/extract",
    response_model=ExtractResponse,
    responses={503: {"model": LLMErrorResponse}},
    summary="结构化信息提取",
)
async def extract(
    req: ExtractRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    使用 Chat 模型从文本中提取结构化信息。
    通过 system prompt 引导模型返回 JSON 格式输出。
    """
    config = await load_llm_config(db)
    client = get_async_openai_client(config)

    model = config.get("model_chat", "").strip()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM 未配置: model_chat 为空。",
        )

    system_prompt = (
        "你是一个精确的信息提取助手。用户会给你一段文本和一个提取指令，"
        "你必须严格按照指令从文本中提取信息，并以 JSON 格式返回。"
        "只返回 JSON，不要附加任何解释文字。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"提取指令: {req.instruction}\n\n源文本:\n{req.text}",
        },
    ]

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=req.temperature,
        )

        raw = (
            response.model_dump() if hasattr(response, "model_dump") else str(response)
        )

        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""

        # 尝试解析为 JSON
        extracted = content
        try:
            # 处理可能被 markdown 代码块包裹的 JSON
            clean = content.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                # 移除首尾的 ``` 行
                lines = [l for l in lines if not l.strip().startswith("```")]
                clean = "\n".join(lines)
            extracted = json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            # 保持原始文本
            extracted = content

        logger.info("Extract 完成: model=%s", model)
        return ExtractResponse(
            success=True,
            extracted=extracted,
            model=response.model or model,
            raw_response=raw,
        )

    except Exception as e:
        logger.error("Extract 调用失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM Extract 调用失败，请检查配置和网络连接。",
        )
