package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewPlanBasicsEntity;

/** 大纲基础信息表数据访问。 */
@Mapper
public interface InterviewPlanBasicsMapper extends BaseMapper<InterviewPlanBasicsEntity> {
}
