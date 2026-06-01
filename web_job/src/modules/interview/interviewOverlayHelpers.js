/**
 * 遮层面试模式 — 进度、题干、面试官话术等派生逻辑。
 */

/** 阶段中文标签 */
export function phaseLabel(phase) {
  const map = {
    ready: "准备开始",
    self_intro: "自我介绍",
    question: "答题中",
    completed: "已全部完成"
  };
  return map[String(phase || "").trim()] || "面试进行中";
}

/** 题目是否已完结 */
export function isQuestionCompleted(status) {
  const s = String(status || "pending").toLowerCase();
  return s === "completed" || s === "answered" || s === "summarized";
}

/** 按 seq_no 升序取第一道未作答题（重新进入时用） */
export function pickFirstIncompleteQuestion(questions) {
  const list = (Array.isArray(questions) ? [...questions] : []).sort(
    (a, b) => Number(a.seq_no ?? 0) - Number(b.seq_no ?? 0)
  );
  return list.find((q) => !isQuestionCompleted(q.answer_status)) || null;
}

/** 是否已有答题进度（用于区分开始/继续文案） */
export function hasInterviewProgress(questions) {
  const list = Array.isArray(questions) ? questions : [];
  return list.some((q) => isQuestionCompleted(q.answer_status));
}

/** 从 API 题目列表取当前题 */
export function pickCurrentQuestionItem(questions, session) {
  const list = Array.isArray(questions) ? questions : [];
  if (!list.length) return null;
  const seq = session?.seqNo;
  if (seq != null) {
    const hit = list.find((q) => Number(q.seq_no) === Number(seq));
    if (hit) return hit;
  }
  const qid = String(session?.questionId || "").trim();
  if (qid) {
    const hit = list.find((q) => String(q.question_id) === qid);
    if (hit) return hit;
  }
  const idx = Number(session?.currentQuestionIndex ?? 0);
  return list[idx] || list[0];
}

/** 合并 progress SSE 后刷新当前题干 */
export function resolveQuestionText(session, questions, overrideSeq) {
  const seq = overrideSeq != null ? overrideSeq : session?.seqNo;
  if (seq != null) {
    const bySeq = findQuestionBySeq(questions, seq);
    const fromList = String(bySeq?.question_text || "").trim();
    if (fromList) return fromList;
  }
  const fromSession = String(session?.currentQuestionText || "").trim();
  if (fromSession) return fromSession;
  const item = pickCurrentQuestionItem(questions, session);
  return String(item?.question_text || "").trim();
}

/** 从 interview_turn.interviewer 提取展示话术 */
export function extractInterviewerDisplay(interviewer) {
  if (!interviewer || typeof interviewer !== "object") return "";
  const parts = [
    interviewer.question_text,
    interviewer.followup_text,
    interviewer.thinking_hint && `提示：${interviewer.thinking_hint}`
  ];
  return parts.map((p) => String(p || "").trim()).filter(Boolean).join("\n");
}

/** 答题状态展示 */
export function answerStatusMeta(status) {
  const s = String(status || "pending").toLowerCase();
  if (s === "completed" || s === "answered" || s === "summarized") {
    return { label: "本题已完结", tone: "done" };
  }
  if (s === "in_progress") {
    return { label: "作答中", tone: "active" };
  }
  return { label: "待作答", tone: "pending" };
}

/** 进度百分比（0～100） */
export function progressPercent(session) {
  const total = Number(session?.questionTotal);
  const answered = Number(session?.questionAnswered ?? 0);
  if (!total || total <= 0) return 0;
  return Math.min(100, Math.round((answered / total) * 100));
}

/** 将 progress / 题目同步到 session 的可显示题号（seq_no 优先） */
export function resolveDisplayQuestionIndex(session) {
  if (session?.seqNo != null) return Number(session.seqNo);
  return Number(session?.currentQuestionIndex ?? 0);
}

/** 按 seq_no 在答题列表中查找题目 */
export function findQuestionBySeq(questions, seqNo) {
  const target = Number(seqNo);
  if (Number.isNaN(target)) return null;
  const list = Array.isArray(questions) ? questions : [];
  return list.find((q) => Number(q.seq_no) === target) || null;
}

/**
 * 进度圆点类型：done=已答(绿)、live=答题中(蓝)、pending=待答(灰)。
 *
 * liveSeqNo 为当前正在作答的题号（session.seq_no）。
 */
export function resolveProgressDotKind(question, liveSeqNo) {
  const st = String(question?.answer_status || "pending").toLowerCase();
  if (isQuestionCompleted(st)) return "done";
  const seq = Number(question?.seq_no ?? -1);
  if (seq === Number(liveSeqNo)) return "live";
  return "pending";
}

/** 圆点是否可点击（已答回看 / 答题中切回） */
export function isProgressDotClickable(kind) {
  return kind === "done" || kind === "live";
}

/**
 * 已答题目回看：由 API 答题记录构造遮层对话流（无多轮明细时用汇总作答）。
 */
export function buildReviewTurnsFromAnswerItem(item) {
  if (!item || typeof item !== "object") return [];
  const turns = [];
  const qText = String(item.question_text || "").trim();
  if (qText) turns.push({ role: "interviewer", text: qText });
  const answer = String(item.answer_text || "").trim();
  if (answer) {
    turns.push({ role: "user", text: answer });
  } else {
    turns.push({ role: "user", text: "（本题暂无作答记录）" });
  }
  const comment = String(item.evaluator_comment || "").trim();
  const score = item.score;
  if (comment || score != null) {
    const parts = [];
    if (score != null) parts.push(`得分：${score}`);
    if (comment) parts.push(comment);
    turns.push({ role: "interviewer", text: parts.join("\n") });
  }
  return turns;
}

/**
 * 用 session.seqNo / questionAnswered 校准本地题目 answer_status。
 *
 * Redis/SSE 往往比 MySQL 列表快，重新进入时避免圆点与题干 seq 不一致。
 */
export function reconcileQuestionStatuses(questions, session) {
  if (!session || !Array.isArray(questions)) return questions;
  const liveSeq = Number(session.seqNo ?? 0);
  return questions.map((q) => {
    const seq = Number(q.seq_no ?? 0);
    const st = String(q.answer_status || "pending").toLowerCase();
    if (isQuestionCompleted(st)) return q;
    if (seq < liveSeq) {
      return { ...q, answer_status: "completed" };
    }
    if (seq === liveSeq) {
      return { ...q, answer_status: st === "pending" ? "in_progress" : q.answer_status };
    }
    return q;
  });
}
