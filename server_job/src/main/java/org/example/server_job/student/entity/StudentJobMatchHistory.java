package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 学生智能匹配历史：单次匹配的诉求、设置、岗位结果与推荐理由。
 * 每名学生由业务层维护最多 {@code 5} 条，超出时删除最旧记录。
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
