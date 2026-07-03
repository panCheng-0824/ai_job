package org.example.server_job.student.entity;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 学生自助画像扩展：联系方式、求职意向、能力标签等（与学籍 t_biz_* 合并展示）。
 */
@Data
@TableName("student_profile_ext")
public class StudentProfileExt {

    @TableId
    private String studentId;

    private String phone;

    private String email;

    private String avatarUrl;

    private String campusExperience;

    /** JSON 字符串：求职意向 */
    private String jobIntentJson;

    /** JSON 字符串：能力标签与雷达 */
    private String abilityJson;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
