from __future__ import annotations

import json
import logging
import time

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware

from app.portal import chat_stream_service
from app.portal import chat_turn_service
from app.portal import data_catalog
from app.portal import ocr_service
from app.portal import online_search_service
from app.portal import session_service
from app.portal import session_store
from app.portal import voice_service
from app.portal.errors import PortalError
from app.portal.schemas import (
    ChatMessageRequest,
    ChatStreamMessageRequest,
    InternalChatPayload,
    JobInfoQueryRequest,
    OCRRecognizeRequest,
    OCRRecognizeUrlRequest,
    SessionInitRequest,
    VoiceSpeechRequest,
    VoiceSpokenSummaryRequest,
    VoiceSpokenSummaryTextRequest,
)
from app.rag import greprag_router, lightrag_router
from app.session.role.role005.api.routes import router as interview_internal_router
from app.skills.job_info_query import run_job_info_query_async
from app.student_redis import format_student_profile_prompt_extra, get_student_profile
import copy

from app.portal import stream_registry

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

app = FastAPI(title="ai_job", description="AI 能力服务（LightRAG / GraphRAG / 对话 / 语音 / OCR 等）；业务数据与门户页面由 server_job + web_job 提供。")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


class ChineseAccessLogMiddleware(BaseHTTPMiddleware):
    """为每一次 HTTP 请求输出中文访问日志（含挂载入的子路由）。"""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        client_host = request.client.host if request.client else "-"
        path_with_qs = request.url.path
        if request.url.query:
            path_with_qs = f"{path_with_qs}?{request.url.query}"
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "接口访问异常 | 方法=%s | 路径=%s | 客户端=%s | 耗时=%.2fms",
                request.method,
                path_with_qs,
                client_host,
                elapsed_ms,
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "接口访问 | 方法=%s | 路径=%s | 客户端=%s | 状态码=%s | 耗时=%.2fms",
            request.method,
            path_with_qs,
            client_host,
            response.status_code,
            elapsed_ms,
        )
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ChineseAccessLogMiddleware)
app.include_router(lightrag_router)
app.include_router(greprag_router)
app.include_router(interview_internal_router)
logger = logging.getLogger(__name__)


def _pe(e: PortalError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.detail)


@app.get("/")
def root() -> dict[str, Any]:
    """本服务不再提供 HTML 门户；前端请使用 web_job，业务 API 请使用 server_job。"""
    return {
        "service": "ai_job",
        "docs": "/docs",
        "message": "AI 能力服务；门户与岗位/企业/收藏评价等数据请走 server_job",
    }


@app.get("/api/online-search")
def online_search(query: str, engine: str = "baidu", topk: int = 5, deep_search: bool = False):
    try:
        return online_search_service.run_online_search(query, engine, topk, deep_search)
    except PortalError as e:
        raise _pe(e) from e


@app.post("/api/ocr/recognize")
def ocr_recognize(payload: OCRRecognizeRequest):
    try:
        return ocr_service.recognize_by_path(
            payload.image_path, payload.lang, payload.use_angle_cls
        )
    except PortalError as e:
        raise _pe(e) from e


@app.post("/api/ocr/recognize-upload")
async def ocr_recognize_upload(
    file: UploadFile = File(...),
    lang: str = Form("ch"),
    use_angle_cls: bool = Form(True),
):
    filename = (file.filename or "").strip()
    try:
        content = await file.read()
        return ocr_service.recognize_upload_bytes(
            content,
            filename or "upload.png",
            lang,
            use_angle_cls,
        )
    except PortalError as e:
        raise _pe(e) from e
    finally:
        try:
            await file.close()
        except Exception:
            pass


@app.post("/api/ocr/recognize-url")
def ocr_recognize_url(payload: OCRRecognizeUrlRequest):
    try:
        return ocr_service.recognize_by_url(
            payload.image_url, payload.lang, payload.use_angle_cls
        )
    except PortalError as e:
        raise _pe(e) from e


@app.post("/api/voice/transcribe")
async def voice_transcribe(
    file: UploadFile = File(...),
    model_level: str = Form("mid"),
):
    raw_name = (file.filename or "").strip() or "recording.webm"
    ct = file.content_type or "application/octet-stream"
    try:
        content = await file.read()
        return voice_service.transcribe_upload(content, raw_name, ct, model_level)
    except PortalError as e:
        raise _pe(e) from e
    finally:
        try:
            await file.close()
        except Exception:
            pass


@app.post("/api/voice/speech")
def voice_speech(payload: VoiceSpeechRequest):
    try:
        audio, ctype = voice_service.speech_binary(
            payload.text, payload.model_level, payload.voice
        )
    except PortalError as e:
        raise _pe(e) from e
    return Response(content=audio, media_type=ctype)


@app.post("/api/voice/spoken-summary")
def voice_spoken_summary(payload: VoiceSpokenSummaryRequest):
    try:
        audio, ctype = voice_service.spoken_summary_audio(
            payload.answer_text,
            payload.chat_model_level,
            payload.tts_model_level,
            payload.voice,
        )
    except PortalError as e:
        raise _pe(e) from e
    return Response(content=audio, media_type=ctype)


@app.post("/api/voice/speech/stream")
def voice_speech_stream(payload: VoiceSpeechRequest):
    try:
        stream = voice_service.open_tts_stream_for_text(
            payload.text, payload.model_level, payload.voice
        )
    except PortalError as e:
        raise _pe(e) from e
    return StreamingResponse(stream.chunks, media_type=stream.content_type)


@app.post("/api/voice/spoken-summary/stream")
def voice_spoken_summary_stream(payload: VoiceSpokenSummaryRequest):
    try:
        stream = voice_service.spoken_summary_stream(
            payload.answer_text,
            payload.chat_model_level,
            payload.tts_model_level,
            payload.voice,
        )
    except PortalError as e:
        raise _pe(e) from e
    return StreamingResponse(stream.chunks, media_type=stream.content_type)


@app.post("/api/voice/spoken-summary/text")
def voice_spoken_summary_text(payload: VoiceSpokenSummaryTextRequest):
    try:
        spoken = voice_service.resolve_spoken_summary_text(
            payload.answer_text, payload.chat_model_level
        )
    except PortalError as e:
        raise _pe(e) from e
    return {"text": spoken}


@app.post("/api/skills/job-info-query")
async def job_info_query(payload: JobInfoQueryRequest):
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")
    return await run_job_info_query_async(payload)


@app.get("/api/user-models")
def list_user_models():
    return data_catalog.list_user_models_for_api()


@app.get("/api/search")
def search_data(keyword: str, scope: str = "all", limit: int = 20):
    try:
        return data_catalog.search_data(keyword, scope, limit)
    except PortalError as e:
        raise _pe(e) from e


@app.get("/api/chat-sessions/{session_id}")
def get_chat_session(session_id: str):
    try:
        return session_service.get_session_or_raise(session_id)
    except PortalError as e:
        raise _pe(e) from e


@app.get("/api/chat-sessions")
def list_chat_sessions(student_id: str):
    try:
        return session_service.list_sessions_for_student(student_id)
    except PortalError as e:
        raise _pe(e) from e


@app.delete("/api/chat-sessions/{session_id}")
def delete_chat_session(session_id: str):
    try:
        return session_service.delete_session(session_id)
    except PortalError as e:
        raise _pe(e) from e


@app.post("/api/chat-sessions/init")
def init_chat_session(payload: SessionInitRequest):
    try:
        return session_service.init_session(
            payload.session_id, payload.student_id, payload.usercode
        )
    except PortalError as e:
        raise _pe(e) from e


@app.get("/api/session-id")
def generate_session_id(student_id: str):
    try:
        return data_catalog.random_session_id_for_student(student_id)
    except PortalError as e:
        raise _pe(e) from e


@app.get("/api/chat-sessions/{session_id}/history")
def get_chat_history(session_id: str):
    try:
        return session_service.get_history_bundle(session_id)
    except PortalError as e:
        raise _pe(e) from e


@app.post("/api/chat-sessions/{session_id}/messages")
def chat_in_session(session_id: str, payload: ChatMessageRequest):
    try:
        return chat_turn_service.chat_turn_in_persisted_session(session_id, payload)
    except PortalError as e:
        raise _pe(e) from e


def _chat_stream_event_gen(
    session_id: str,
    student_id: str,
    *,
    display: str,
    hidden: str,
    cards: list,
    use_role_pipeline: bool,
    use_adversarial_harness: bool,
    adversarial_desc: str,
):
    from app.session.user_turn_context import build_llm_user_text

    text = build_llm_user_text(display=display, hidden=hidden)
    if not text and not cards:
        raise HTTPException(status_code=400, detail="message 不能为空")

    try:
        sessions, idx, session = session_service.load_session_pair_or_raise(session_id)
    except PortalError as e:
        raise _pe(e) from e

    usercode = str(session.get("usercode", "")).strip()
    user_model = data_catalog.user_models_index.get(usercode)
    if not user_model:
        raise HTTPException(status_code=404, detail="会话对应的 user_model 不存在")

    history_turns = session.get("history", [])
    profile_extra = format_student_profile_prompt_extra(str(session.get("student_id", "")))

    def persist_file_session() -> None:
        session["history"] = history_turns
        sessions[idx] = session
        session_store.save_sessions(sessions)

    yield from chat_stream_service.iter_chat_sse_events(
        session_id,
        usercode,
        student_id,
        user_model,
        text,
        history_turns,
        use_role_pipeline=use_role_pipeline,
        use_adversarial_harness=use_adversarial_harness,
        adversarial_desc=adversarial_desc,
        model_level_fallback=str(session.get("model_level", "")),
        after_history_mutated=persist_file_session,
        system_prompt_extra=profile_extra,
        user_display_content=display,
        user_message_context=hidden,
        user_context_cards=cards,
    )


@app.get("/api/chat-sessions/{session_id}/messages/stream")
def chat_in_session_stream(
    session_id: str,
    message: str,
    use_role_pipeline: bool = True,
    use_adversarial_harness: bool = False,
    adversarial_desc: str = "",
    message_context: str = "",
    context_cards: str = "",
):
    display = (message or "").strip()
    hidden = (message_context or "").strip()
    cards: list = []
    if (context_cards or "").strip():
        try:
            parsed = json.loads(context_cards)
            if isinstance(parsed, list):
                cards = parsed
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="context_cards 不是合法 JSON 数组")

    def event_gen():
        yield from _chat_stream_event_gen(
            session_id,
            display=display,
            hidden=hidden,
            cards=cards,
            use_role_pipeline=use_role_pipeline,
            use_adversarial_harness=use_adversarial_harness,
            adversarial_desc=adversarial_desc,
        )

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/api/chat-sessions/{session_id}/messages/stream")
def chat_in_session_stream_post(session_id: str, payload: ChatStreamMessageRequest):
    """携带卡片/长上下文时用 POST，避免 GET 查询串过长导致 context_cards 丢失。"""
    display = (payload.message or "").strip()
    hidden = (payload.message_context or "").strip()
    cards = list(payload.context_cards or [])

    def event_gen():
        yield from _chat_stream_event_gen(
            session_id,
            display=display,
            hidden=hidden,
            cards=cards,
            use_role_pipeline=payload.use_role_pipeline,
            use_adversarial_harness=payload.use_adversarial_harness,
            adversarial_desc=payload.adversarial_desc or "",
        )

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/api/chat-sessions/{session_id}/messages/stop")
def stop_stream_message(session_id: str):
    cancel_fn = stream_registry.pop_stream_canceller(session_id)
    if not cancel_fn:
        return {"success": False, "message": "当前会话没有进行中的流式生成"}
    stream_registry.safe_cancel(cancel_fn)
    return {"success": True, "message": "已请求停止后台生成"}


@app.post("/api/internal/chat/stream")
def internal_chat_stream(payload: InternalChatPayload):
    try:
        user_model = data_catalog.get_user_model_or_raise(payload.usercode)
    except PortalError as e:
        raise _pe(e) from e
    logger.info("进行会话聊天")
    sid = payload.session_id.strip()
    stuid = payload.student_id.strip()
    if not sid:
        raise HTTPException(status_code=400, detail="session_id 不能为空")
    from app.session.user_turn_context import build_llm_user_text

    display = payload.message.strip()
    hidden = (payload.message_context or "").strip()
    cards = list(payload.context_cards or [])
    text = build_llm_user_text(display=display, hidden=hidden)
    if not text and not cards:
        raise HTTPException(status_code=400, detail="message 不能为空")

    usercode = str(user_model.get("usercode", "")).strip()
    history_turns = copy.deepcopy(payload.history)
    profile_extra = format_student_profile_prompt_extra(payload.student_id)

    def event_gen():
        yield from chat_stream_service.iter_chat_sse_events(
            sid,
            usercode,
            stuid,
            user_model,
            text,
            history_turns,
            use_role_pipeline=payload.use_role_pipeline,
            use_adversarial_harness=payload.use_adversarial_harness,
            adversarial_desc=payload.adversarial_desc,
            model_level_fallback=str(user_model.get("model_level", "")),
            after_history_mutated=None,
            system_prompt_extra=profile_extra,
            user_display_content=display,
            user_message_context=hidden,
            user_context_cards=cards,
        )

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/api/internal/chat/complete")
def internal_chat_complete(payload: InternalChatPayload):
    try:
        return chat_turn_service.internal_chat_complete_result(payload)
    except PortalError as e:
        raise _pe(e) from e


@app.get("/api/internal/student-profile/{student_id}")
def internal_get_student_profile(student_id: str):
    sid = (student_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="student_id 不能为空")
    data = get_student_profile(sid)
    if data is None:
        raise HTTPException(status_code=404, detail="学生画像不存在或未登录缓存")
    return data


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    uvicorn.run("web_app:app", host="127.0.0.1", port=8001, reload=False)


if __name__ == "__main__":
    main()
