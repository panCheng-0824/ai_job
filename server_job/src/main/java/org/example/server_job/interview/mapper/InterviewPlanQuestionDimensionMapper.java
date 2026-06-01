package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewPlanQuestionDimensionEntity;

/** 大纲题目考察维度表数据访问。 */
@Mapper
public interface InterviewPlanQuestionDimensionMapper
        extends BaseMapper<InterviewPlanQuestionDimensionEntity> {
}
