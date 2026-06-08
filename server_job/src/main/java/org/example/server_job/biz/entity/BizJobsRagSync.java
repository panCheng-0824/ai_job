package org.example.server_job.biz.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 岗位 RAG 同步状态表 {@code t_biz_jobs_rag_sync}。
 * <p>与 {@link BizJobsInfo#jobid} 一对一，从岗位主表拆出以适配 0605 新 schema。</p>
 */
@Data
@TableName("t_biz_jobs_rag_sync")
public class BizJobsRagSync {

    @TableId("jobid")
    private String jobid;

    @TableField("syn_rag")
    private Integer synRag;

    @TableField("rag_md_path")
    private String ragMdPath;

    @TableField("synced_at")
    private LocalDateTime syncedAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
