package org.example.server_job.ai.rag;

import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

/**
 * 单次批量 RAG 同步的运行状态：暂停（未开始的任务在闸门前阻塞）、取消（跳过未开始任务；进行中的照常跑完）。
 */
public final class RagSyncRunState {

    private final AtomicBoolean cancelled = new AtomicBoolean(false);
    private final AtomicBoolean paused = new AtomicBoolean(false);
    private final ReentrantLock pauseLock = new ReentrantLock();
    private final Condition unpaused = pauseLock.newCondition();

    public void pause() {
        paused.set(true);
    }

    public void resume() {
        paused.set(false);
        pauseLock.lock();
        try {
            unpaused.signalAll();
        } finally {
            pauseLock.unlock();
        }
    }

    /** 取消并唤醒在 pause 上等待的线程，使未开始的任务尽快退出。 */
    public void cancel() {
        cancelled.set(true);
        resume();
    }

    public boolean isCancelled() {
        return cancelled.get();
    }

    /**
     * 在真正执行单条同步前调用：若已暂停则阻塞；若已取消则立即返回（由调用方检查 {@link #isCancelled()}）。
     */
    public void awaitGate() throws InterruptedException {
        for (;;) {
            if (cancelled.get()) {
                return;
            }
            if (!paused.get()) {
                return;
            }
            pauseLock.lock();
            try {
                unpaused.await(400, TimeUnit.MILLISECONDS);
            } finally {
                pauseLock.unlock();
            }
        }
    }
}
