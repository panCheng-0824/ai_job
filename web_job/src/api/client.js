const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}${path}`, options);
  } catch (_) {
    throw new Error("无法连接后端，请确认 server_job 服务已启动");
  }
  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_) {
    data = { detail: text || "响应解析失败" };
  }
  if (!resp.ok) {
    throw new Error(data.detail || data.message || "请求失败");
  }
  return data;
}

export function apiGet(path) {
  return request(path);
}

export function apiPost(path, payload) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

/**
 * POST 请求 SSE（text/event-stream），按事件块解析并回调 onEvent(eventName, dataObject)。
 */
function _emitSseFrame(raw, onEvent) {
  const text = String(raw || "").replace(/\r\n/g, "\n");
  if (!text.trim()) return;
  let eventName = "message";
  const dataParts = [];
  for (const line of text.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataParts.push(line.slice(5).trimStart());
    } else if (line.startsWith(":")) {
      /* SSE 注释行，忽略 */
    }
  }
  if (!dataParts.length) return;
  const jsonText = dataParts.join("\n");
  try {
    const obj = JSON.parse(jsonText);
    onEvent?.(eventName, obj);
  } catch (err) {
    console.warn("SSE JSON 解析失败", err, jsonText);
  }
}

export async function apiPostSse(path, body, { onEvent, signal } = {}) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream"
      },
      body: JSON.stringify(body ?? {}),
      signal
    });
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    throw new Error("无法连接后端，请确认 server_job 服务已启动");
  }
  if (!resp.ok) {
    const text = await resp.text();
    let detail = text;
    try {
      const j = JSON.parse(text);
      detail = j.detail || text;
    } catch {
      /* ignore */
    }
    throw new Error(detail || "请求失败");
  }
  const reader = resp.body?.getReader();
  if (!reader) {
    throw new Error("响应不支持流式读取");
  }
  const decoder = new TextDecoder();
  let carry = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    carry += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let sep;
    while ((sep = carry.indexOf("\n\n")) >= 0) {
      const raw = carry.slice(0, sep);
      carry = carry.slice(sep + 2);
      _emitSseFrame(raw, onEvent);
    }
  }
  carry += decoder.decode();
  carry = carry.replace(/\r\n/g, "\n");
  if (carry.trim()) {
    _emitSseFrame(carry, onEvent);
  }
}

export function apiPut(path, payload) {
  return request(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export function apiDelete(path) {
  return request(path, { method: "DELETE" });
}

/** 与登录页一致：门户「我的」收藏/关注/评价依赖 localStorage.student_id */
export function getStudentId() {
  if (typeof window === "undefined") return "";
  return (localStorage.getItem("student_id") || "").trim();
}

/** 上传录音 → ASR，返回 { text } */
export async function apiPostVoiceTranscribe(fileBlob, filename = "recording.webm", modelLevel = "mid") {
  const fd = new FormData();
  fd.append("file", fileBlob, filename);
  fd.append("model_level", modelLevel);
  let resp;
  try {
    resp = await fetch(`${API_BASE}/api/voice/transcribe`, { method: "POST", body: fd });
  } catch (_) {
    throw new Error("无法连接后端，请确认 server_job 与 ai_job 已启动");
  }
  const text = await resp.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_) {
    data = { detail: text || "响应解析失败" };
  }
  if (!resp.ok) {
    throw new Error(data.detail || "语音识别失败");
  }
  return data;
}

/** TTS：返回音频 Blob */
export async function apiPostVoiceSpeech({ text, modelLevel = "mid", voice = "serena" }) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}/api/voice/speech`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, model_level: modelLevel, voice })
    });
  } catch (_) {
    throw new Error("无法连接后端，请确认服务已启动");
  }
  if (!resp.ok) {
    const t = await resp.text();
    let detail = t;
    try {
      const j = JSON.parse(t);
      detail = j.detail || t;
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail || "语音合成失败");
  }
  return resp.blob();
}

/** chat 摘要 + TTS，返回播报用音频 Blob */
export async function apiPostSpokenSummary({
  answer_text,
  chat_model_level = "mid",
  tts_model_level = "mid",
  voice = "serena"
}) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}/api/voice/spoken-summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer_text, chat_model_level, tts_model_level, voice })
    });
  } catch (_) {
    throw new Error("无法连接后端，请确认服务已启动");
  }
  if (!resp.ok) {
    const t = await resp.text();
    let detail = t;
    try {
      const j = JSON.parse(t);
      detail = j.detail || t;
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail || "语音摘要播报失败");
  }
  return resp.blob();
}

/** POST JSON，返回已成功校验的 Response（body 未读，用于流式音频） */
export async function fetchTtsPostStream(path, payload, { signal } = {}) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal
    });
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    throw new Error("无法连接后端，请确认服务已启动");
  }
  if (!resp.ok) {
    const t = await resp.text();
    let detail = t;
    try {
      const j = JSON.parse(t);
      detail = j.detail || t;
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail || "请求失败");
  }
  return resp;
}

async function playBlobAudio(blob) {
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  const cleanup = () => URL.revokeObjectURL(url);
  audio.addEventListener("ended", cleanup, { once: true });
  audio.addEventListener("error", cleanup, { once: true });
  await audio.play();
  return audio;
}

function appendSourceBuffer(sb, u8) {
  const buf =
    u8.byteOffset === 0 && u8.byteLength === u8.buffer.byteLength
      ? u8.buffer
      : u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength);
  return new Promise((resolve, reject) => {
    const onEnd = () => {
      sb.removeEventListener("updateend", onEnd);
      sb.removeEventListener("error", onErr);
      resolve();
    };
    const onErr = () => {
      sb.removeEventListener("updateend", onEnd);
      sb.removeEventListener("error", onErr);
      reject(new Error("SourceBuffer 异常"));
    };
    sb.addEventListener("updateend", onEnd, { once: true });
    sb.addEventListener("error", onErr, { once: true });
    try {
      sb.appendBuffer(buf);
    } catch (e) {
      reject(e);
    }
  });
}

async function playWithMediaSource(bodyStream, mimeType) {
  const mediaSource = new MediaSource();
  const url = URL.createObjectURL(mediaSource);
  const audio = new Audio(url);
  const revoke = () => URL.revokeObjectURL(url);
  audio.addEventListener("ended", revoke, { once: true });
  audio.addEventListener("error", revoke, { once: true });

  await new Promise((resolve, reject) => {
    mediaSource.addEventListener("sourceopen", resolve, { once: true });
    mediaSource.addEventListener("error", reject, { once: true });
  });

  const sb = mediaSource.addSourceBuffer(mimeType);
  const reader = bodyStream.getReader();
  let started = false;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value && value.byteLength) {
        await appendSourceBuffer(sb, value);
        if (!started) {
          started = true;
          audio.play().catch(() => {});
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
  if (mediaSource.readyState === "open") {
    mediaSource.endOfStream();
  }
  return audio;
}

/**
 * 播放流式 TTS：支持则走 MSE 边下边播；否则整段缓冲后播放（不再 tee，避免双倍内存）。
 */
export async function playTtsStreamFromResponse(response) {
  const mime =
    response.headers.get("Content-Type")?.split(";")[0]?.trim() || "audio/mpeg";
  const stream = response.body;
  if (!stream) {
    const blob = await response.blob();
    return playBlobAudio(blob);
  }
  if (typeof MediaSource !== "undefined" && MediaSource.isTypeSupported(mime)) {
    try {
      return await playWithMediaSource(stream, mime);
    } catch (e) {
      console.warn("MediaSource 流式播放失败", e);
      throw new Error(
        "当前浏览器无法流式解码该音频格式，可换 Chrome 或稍后重试"
      );
    }
  }
  const blob = await new Response(stream).blob();
  return playBlobAudio(blob);
}
