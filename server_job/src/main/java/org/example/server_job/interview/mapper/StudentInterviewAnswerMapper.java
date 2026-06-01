package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.StudentInterviewAnswerEntity;

/** 学生逐题答题表数据访问。 */
@Mapper
public interface StudentInterviewAnswerMapper extends BaseMapper<StudentInterviewAnswerEntity> {
}
