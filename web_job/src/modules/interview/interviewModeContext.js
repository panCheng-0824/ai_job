/**
 * 遮层面试模式 — 隐藏 message_context JSON 构造。
 * key 规范与 server_job InterviewRedisKeys 对齐。
 */

/** 整场 ctx Redis key */
export function buildCtxKey(studentId, recordId) {
  const sid = String(studentId || "").trim();
  const rid = String(recordId || "").trim();
  return `interview:ctx:${sid}:${rid}`;
}

/** 单题 qsess Redis key */
export function buildQuestionSessionKey(chatSessionId, studentId, recordId, questionId) {
  const cs = String(chatSessionId || "").trim();
  const sid = String(studentId || "").trim();
  const rid = String(recordId || "").trim();
  const qid = String(questionId || "").trim();
  return `interview:qsess:${cs}:${sid}:${rid}:${qid}`;
}

/** 点击「进入」遮层：action=start */
export function buildInterviewStartContext({
  studentId,
  recordId,
  interviewSessionId,
  chatSessionId,
  planId,
  ctxKey
} = {}) {
  return JSON.stringify({
    mode: "interview",
    action: "start",
    student_id: String(studentId || "").trim(),
    record_id: String(recordId || "").trim(),
    interview_session_id: String(interviewSessionId || "").trim(),
    chat_session_id: String(chatSessionId || "").trim(),
    plan_id: String(planId || "").trim(),
    ctx_key: ctxKey || buildCtxKey(studentId, recordId)
  });
}

/** 遮层内每轮回答：action=answer */
export function buildInterviewAnswerContext(session, answerText) {
  if (!session) return "";
  const payload = {
    mode: "interview",
    action: "answer",
    student_id: session.studentId,
    record_id: session.recordId,
    interview_session_id: session.interviewSessionId,
    chat_session_id: session.chatSessionId,
    ctx_key: session.ctxKey,
    question_session_key: session.questionSessionKey || "",
    question_id: session.questionId || "",
    seq_no: session.seqNo ?? 0,
    payload: { answer_text: String(answerText || "").trim() }
  };
  return JSON.stringify(payload);
}

/** 从 SSE interview_progress 更新本地遮层会话状态 */
export function mergeProgressIntoSession(session, progress) {
  if (!session || !progress || progress.mode !== "interview") return session;
  const prevSeq = session.seqNo;
  const nextSeq = progress.seq_no ?? session.seqNo;
  const questionChanged =
    progress.question_advanced === true ||
    (prevSeq != null && nextSeq != null && Number(prevSeq) !== Number(nextSeq));
  const listIndex =
    progress.current_question_index != null
      ? progress.current_question_index
      : session.currentQuestionIndex;
  return {
    ...session,
    questionSessionKey: progress.question_session_key || session.questionSessionKey,
    questionId: progress.question_id || session.questionId,
    seqNo: nextSeq,
    currentQuestionIndex: listIndex,
    questionTotal: progress.question_total ?? session.questionTotal,
    questionAnswered: progress.question_answered ?? session.questionAnswered,
    evaluatorStatus: progress.evaluator_status || session.evaluatorStatus,
    phase: progress.phase || session.phase,
    currentQuestionText:
      progress.current_question_text ||
      (questionChanged ? "" : session.currentQuestionText)
  };
}
