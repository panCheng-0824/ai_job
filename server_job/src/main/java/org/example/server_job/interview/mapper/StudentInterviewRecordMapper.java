package org.example.server_job.interview.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.interview.entity.StudentInterviewRecordEntity;

/** 学生面试总结记录表数据访问。 */
@Mapper
public interface StudentInterviewRecordMapper extends BaseMapper<StudentInterviewRecordEntity> {
}
