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

from fastapi import APIRouter, Depends, HTTPException, status
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

        result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(SystemSetting(key=key, value=value))

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
        llm_system_prompt_software=config.get("llm_system_prompt_software", ""),
        llm_system_prompt_workspace=config.get("llm_system_prompt_workspace", ""),
    )


@router.post(
    "/test-connection",
    summary="测试 LLM 连接",
)
async def test_llm_connection(
    db: AsyncSession = Depends(get_db),
):
    """使用当前配置测试 LLM 连接是否可用。"""
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
