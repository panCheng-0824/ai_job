package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewPlanQuestionFollowupEntity;

/** 大纲题目预设追问表数据访问。 */
@Mapper
public interface InterviewPlanQuestionFollowupMapper
        extends BaseMapper<InterviewPlanQuestionFollowupEntity> {
}
