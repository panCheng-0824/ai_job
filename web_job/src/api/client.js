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

const pendingRequests = new Map();
const cache = new Map();
const DEFAULT_TTL = 30_000;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function invalidateCache(pathPrefix) {
  if (!pathPrefix) {
    cache.clear();
    return;
  }
  for (const key of cache.keys()) {
    if (key.startsWith(pathPrefix)) {
      cache.delete(key);
    }
  }
}

export async function apiGetWithCache(path, { ttl = DEFAULT_TTL, retries = 2 } = {}) {
  const key = path;

  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < ttl) {
    return cached.data;
  }

  if (pendingRequests.has(key)) {
    return pendingRequests.get(key);
  }

  const doRequest = async () => {
    let lastError;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        return await request(path);
      } catch (e) {
        lastError = e;
        if (attempt < retries) {
          await sleep(1000 * (1 << attempt));
        }
      }
    }
    throw lastError;
  };

  const promise = doRequest();
  pendingRequests.set(key, promise);

  try {
    const data = await promise;
    cache.set(key, { data, timestamp: Date.now() });
    return data;
  } finally {
    pendingRequests.delete(key);
  }
}

export function apiGet(path, options) {
  return apiGetWithCache(path, options);
}

/** 绕过读缓存（ttl=0），用于需实时数据的列表/详情 */
export function apiGetFresh(path, options = {}) {
  return apiGetWithCache(path, { ...options, ttl: 0 });
}

export function apiPost(path, payload) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

/**
 * POST NDJSON 流（application/x-ndjson）：按行解析 JSON，非 SSE。
 */
export async function apiPostNdjsonStream(path, body, { onEvent, signal } = {}) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/x-ndjson, application/json"
      },
      body: JSON.stringify(body ?? {}),
      signal
    });
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    throw new Error("无法连接后端，请确认 server_job 与 ai_job 已启动");
  }
  if (!resp.ok) {
    const text = await resp.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail || text;
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
    carry += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = carry.indexOf("\n")) >= 0) {
      const line = carry.slice(0, idx).trim();
      carry = carry.slice(idx + 1);
      if (!line) continue;
      try {
        onEvent?.(JSON.parse(line));
      } catch (err) {
        console.warn("NDJSON 解析失败", err, line);
      }
    }
  }
  carry += decoder.decode();
  const tail = carry.trim();
  if (tail) {
    try {
      onEvent?.(JSON.parse(tail));
    } catch (err) {
      console.warn("NDJSON 尾行解析失败", err, tail);
    }
  }
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

/** multipart/form-data 上传（不设 Content-Type，由浏览器带 boundary） */
export async function apiPostForm(path, formData) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: formData
    });
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
    throw new Error(data.detail || data.message || "上传失败");
  }
  return data;
}

export function apiDelete(path) {
  return request(path, { method: "DELETE" });
}

/** 与登录页一致：门户「我的」收藏/关注/评价依赖 localStorage.student_id */
export function getStudentId() {
  if (typeof window === "undefined") return "";
  return (localStorage.getItem("student_id") || "").trim();
}

export function isLoggedIn() {
  return Boolean(getStudentId());
}

/** 退出登录：清除本地会话标识，可选跳转登录页 */
export function logout({ redirect = true, router } = {}) {
  if (typeof window === "undefined") return;
  if (!window.confirm("确定退出登录？将清除本地会话数据")) return;
  localStorage.removeItem("student_id");
  localStorage.removeItem("session_id");
  localStorage.removeItem("usercode");
  sessionStorage.removeItem("login_password_hint");
  sessionStorage.removeItem("home_data_loaded");
  sessionStorage.removeItem("jobs_data_loaded");
  sessionStorage.removeItem("jobs_hot_loaded");
  if (!redirect) return;
  if (router) {
    router.replace("/login");
    return;
  }
  window.location.replace("/login");
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
