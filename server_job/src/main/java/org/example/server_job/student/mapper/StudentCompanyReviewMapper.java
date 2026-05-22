package org.example.server_job.student.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.example.server_job.student.entity.StudentCompanyReview;

import java.util.List;
import java.util.Map;

@Mapper
public interface StudentCompanyReviewMapper extends BaseMapper<StudentCompanyReview> {

    @Select("""
            SELECT t.tag_id AS tag_id, COUNT(*) AS cnt
            FROM student_company_review_tag t
            INNER JOIN student_company_review r ON r.id = t.company_review_id
            WHERE r.credit_code = #{creditCode}
            GROUP BY t.tag_id
            ORDER BY cnt DESC, t.tag_id ASC
            """)
    List<Map<String, Object>> tagDistributionForCompany(@Param("creditCode") String creditCode);
}
