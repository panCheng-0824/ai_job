package org.example.server_job.biz.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.server_job.biz.entity.BizJobsRagSync;

import java.util.Collection;
import java.util.Map;

/**
 * 岗位 RAG 同步状态维护与查询。
 */
public interface BizJobsRagSyncService extends IService<BizJobsRagSync> {

    BizJobsRagSync findByJobId(String jobId);

    boolean isSynced(String jobId);

    void markSynced(String jobId, String ragMdPath);

    void markUnsynced(String jobId);

    Map<String, BizJobsRagSync> mapByJobIds(Collection<String> jobIds);
}
