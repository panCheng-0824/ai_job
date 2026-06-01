package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.InterviewIndustryCategoryEntity;

/** 行业分类表数据访问。 */
@Mapper
public interface InterviewIndustryCategoryMapper extends BaseMapper<InterviewIndustryCategoryEntity> {
}
