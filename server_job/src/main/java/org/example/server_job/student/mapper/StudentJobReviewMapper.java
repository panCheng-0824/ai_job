package org.example.server_job.student.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.example.server_job.student.entity.StudentJobReview;

import java.util.List;
import java.util.Map;

@Mapper
public interface StudentJobReviewMapper extends BaseMapper<StudentJobReview> {

    @Select("""
            SELECT t.tag_id AS tag_id, COUNT(*) AS cnt
            FROM student_job_review_tag t
            INNER JOIN student_job_review r ON r.id = t.job_review_id
            WHERE r.job_id = #{jobId}
            GROUP BY t.tag_id
            ORDER BY cnt DESC, t.tag_id ASC
            """)
    List<Map<String, Object>> tagDistributionForJob(@Param("jobId") String jobId);
}
