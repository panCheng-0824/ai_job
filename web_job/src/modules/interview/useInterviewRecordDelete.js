/**
 * 面试记录删除：确认弹窗 + 调用后端。
 */
import { ref } from "vue";
import { deleteInterviewRecord } from "./api";

/**
 * @returns deleting 删除中；confirmAndDelete 确认后删除，成功返回 true
 */
export function useInterviewRecordDelete() {
  const deleting = ref(false);
  const deleteError = ref("");

  async function confirmAndDelete(studentId, recordId, title = "该面试记录") {
    const sid = String(studentId || "").trim();
    const rid = String(recordId || "").trim();
    if (!sid || !rid) {
      deleteError.value = "缺少学号或记录 ID";
      return false;
    }
    const label = String(title || "该面试记录").trim() || "该面试记录";
    if (!globalThis.confirm(`确定删除「${label}」？关联的答题与面试会话将一并删除，且不可恢复。`)) {
      return false;
    }
    deleting.value = true;
    deleteError.value = "";
    try {
      await deleteInterviewRecord(sid, rid);
      return true;
    } catch (e) {
      deleteError.value = e?.message || "删除失败";
      return false;
    } finally {
      deleting.value = false;
    }
  }

  return { deleting, deleteError, confirmAndDelete };
}
