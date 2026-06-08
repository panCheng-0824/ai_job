package org.example.server_job.biz.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.server_job.biz.entity.BizJobsRagSync;
import org.example.server_job.biz.mapper.BizJobsRagSyncMapper;
import org.example.server_job.biz.service.BizJobsRagSyncService;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 岗位 RAG 同步状态表 CRUD 实现。
 */
@Service
public class BizJobsRagSyncServiceImpl extends ServiceImpl<BizJobsRagSyncMapper, BizJobsRagSync>
        implements BizJobsRagSyncService {

    @Override
    public BizJobsRagSync findByJobId(String jobId) {
        if (jobId == null || jobId.isBlank()) {
            return null;
        }
        return getById(jobId.trim());
    }

    @Override
    public boolean isSynced(String jobId) {
        BizJobsRagSync row = findByJobId(jobId);
        return row != null && row.getSynRag() != null && row.getSynRag() == 1;
    }

    @Override
    public void markSynced(String jobId, String ragMdPath) {
        if (jobId == null || jobId.isBlank()) {
            return;
        }
        LocalDateTime now = LocalDateTime.now();
        BizJobsRagSync existing = findByJobId(jobId);
        if (existing == null) {
            BizJobsRagSync row = new BizJobsRagSync();
            row.setJobid(jobId.trim());
            row.setSynRag(1);
            row.setRagMdPath(ragMdPath);
            row.setSyncedAt(now);
            row.setUpdatedAt(now);
            save(row);
            return;
        }
        BizJobsRagSync update = new BizJobsRagSync();
        update.setJobid(existing.getJobid());
        update.setSynRag(1);
        update.setRagMdPath(ragMdPath);
        update.setSyncedAt(now);
        update.setUpdatedAt(now);
        updateById(update);
    }

    @Override
    public void markUnsynced(String jobId) {
        if (jobId == null || jobId.isBlank()) {
            return;
        }
        LocalDateTime now = LocalDateTime.now();
        BizJobsRagSync existing = findByJobId(jobId);
        if (existing == null) {
            BizJobsRagSync row = new BizJobsRagSync();
            row.setJobid(jobId.trim());
            row.setSynRag(0);
            row.setRagMdPath(null);
            row.setUpdatedAt(now);
            save(row);
            return;
        }
        BizJobsRagSync update = new BizJobsRagSync();
        update.setJobid(existing.getJobid());
        update.setSynRag(0);
        update.setRagMdPath(null);
        update.setUpdatedAt(now);
        updateById(update);
    }

    @Override
    public Map<String, BizJobsRagSync> mapByJobIds(Collection<String> jobIds) {
        Map<String, BizJobsRagSync> map = new HashMap<>();
        if (jobIds == null || jobIds.isEmpty()) {
            return map;
        }
        List<BizJobsRagSync> rows = list(
                Wrappers.<BizJobsRagSync>lambdaQuery().in(BizJobsRagSync::getJobid, jobIds)
        );
        for (BizJobsRagSync row : rows) {
            if (row.getJobid() != null) {
                map.put(row.getJobid(), row);
            }
        }
        return map;
    }
}
