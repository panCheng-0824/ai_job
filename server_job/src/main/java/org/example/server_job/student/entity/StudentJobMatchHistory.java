package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 学生智能匹配历史：单次匹配的诉求、设置、岗位结果与推荐理由。
 */
@Data
@TableName("student_job_match_history")
public class StudentJobMatchHistory {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String studentId;

    private String queryText;

    /** JSON 字符串：匹配设置 */
    private String settingsJson;

    /** JSON 字符串：岗位列表 */
    private String jobsJson;

    /** JSON 字符串：recommendation 对象 */
    private String recommendationJson;

    private Integer jobCount;

    private LocalDateTime createdAt;
}
