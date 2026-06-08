package org.example.server_job.biz.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.biz.entity.BizJobsRagSync;

/**
 * 岗位 RAG 同步状态数据访问。
 */
@Mapper
public interface BizJobsRagSyncMapper extends BaseMapper<BizJobsRagSync> {
}
