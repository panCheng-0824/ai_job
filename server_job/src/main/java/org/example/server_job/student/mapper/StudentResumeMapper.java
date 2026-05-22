package org.example.server_job.student.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.server_job.student.entity.StudentResume;

@Mapper
public interface StudentResumeMapper extends BaseMapper<StudentResume> {
}
