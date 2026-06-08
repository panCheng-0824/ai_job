package org.example.server_job.ai.rag;

import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 全服务同时只允许一批「流式批量 RAG 同步」；暂停/取消作用于当前批次。
 */
@Component
public class RagSyncBatchCoordinator {

    private final AtomicReference<RagSyncRunState> active = new AtomicReference<>();

    /** 若已有批次在进行则返回 empty。 */
    public Optional<RagSyncRunState> tryBeginRun() {
        RagSyncRunState state = new RagSyncRunState();
        if (active.compareAndSet(null, state)) {
            return Optional.of(state);
        }
        return Optional.empty();
    }

    public void endRun(RagSyncRunState expected) {
        active.compareAndSet(expected, null);
    }

    public void pauseCurrent() {
        RagSyncRunState s = active.get();
        if (s != null) {
            s.pause();
        }
    }

    public void resumeCurrent() {
        RagSyncRunState s = active.get();
        if (s != null) {
            s.resume();
        }
    }

    /** 与关闭 SSE 连接等价：取消当前批次并释放占槽，便于立即重新开始同步。 */
    public void cancelCurrent() {
        RagSyncRunState s = active.get();
        if (s != null) {
            s.cancel();
            endRun(s);
        }
    }
}
