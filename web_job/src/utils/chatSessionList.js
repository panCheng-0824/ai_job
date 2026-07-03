/** 会话列表 API 响应归一化 */
export function normalizeChatSessionsResponse(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.sessions)) return data.sessions;
  return [];
}

/** 将 init / 详情文档转为侧栏列表项 */
export function mapSessionDocumentToListItem(doc) {
  if (!doc?.session_id) return null;
  return {
    session_id: doc.session_id,
    student_id: doc.student_id,
    usercode: doc.usercode,
    username: doc.username,
    role_name: doc.role_name,
    model_level: doc.model_level,
    created_at: doc.created_at,
    history: Array.isArray(doc.history) ? doc.history : []
  };
}

/** 侧栏卡片标题：优先首条用户消息，否则角色名 */
export function sessionCardTitle(session) {
  const hist = session?.history || [];
  const firstUser = hist.find((h) => h?.role === "user" && String(h.content || "").trim());
  if (firstUser) {
    const text = String(firstUser.content).trim().replace(/\s+/g, " ");
    return text.length > 32 ? `${text.slice(0, 32)}…` : text;
  }
  return session?.role_name || session?.session_id || "新会话";
}

export function sessionCardSubtitle(session) {
  const parts = [session?.role_name || session?.usercode, session?.model_level || "-"].filter(Boolean);
  return parts.join(" · ");
}

/**
 * 将新会话插入列表头部（去重）。
 * @param {object[]} list
 * @param {object} doc
 */
export function upsertChatSession(list, doc) {
  const item = mapSessionDocumentToListItem(doc);
  if (!item) return list || [];
  const rest = (list || []).filter((s) => s.session_id !== item.session_id);
  return [item, ...rest];
}
