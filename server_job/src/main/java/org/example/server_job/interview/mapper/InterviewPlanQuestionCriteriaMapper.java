package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewPlanQuestionCriteriaEntity;

/** 大纲题目评分标准表数据访问。 */
@Mapper
public interface InterviewPlanQuestionCriteriaMapper
        extends BaseMapper<InterviewPlanQuestionCriteriaEntity> {
}
