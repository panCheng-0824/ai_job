package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewPlanQuestionEntity;

/** 大纲题目表数据访问。 */
@Mapper
public interface InterviewPlanQuestionMapper extends BaseMapper<InterviewPlanQuestionEntity> {
}
