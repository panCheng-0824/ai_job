package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewAuditLogEntity;

@Mapper
public interface InterviewAuditLogMapper extends BaseMapper<InterviewAuditLogEntity> {
}
