package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewSessionEntity;

@Mapper
public interface InterviewSessionMapper extends BaseMapper<InterviewSessionEntity> {
}
