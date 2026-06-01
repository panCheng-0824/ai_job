package org.example.server_job.interview.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 面试行业分类实体，对应表 {@code interview_industry_category}。
 * 一级/二级同表，通过 {@code level} 与 {@code parent_id} 表达树形结构。
 */
@Data
@TableName("interview_industry_category")
public class InterviewIndustryCategoryEntity {

    @TableId(value = "category_id", type = IdType.INPUT)
    private String categoryId;

    @TableField("parent_id")
    private String parentId;

    /** 1=一级类目，2=二级类目（大纲仅绑定 level=2） */
    private Integer level;

    @TableField("category_code")
    private String categoryCode;

    @TableField("category_name")
    private String categoryName;

    private String description;

    @TableField("intent_keywords")
    private String intentKeywords;

    @TableField("enabled_for_intent")
    private Integer enabledForIntent;

    @TableField("enabled_for_classify")
    private Integer enabledForClassify;

    @TableField("sort_no")
    private Integer sortNo;

    private String status;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
