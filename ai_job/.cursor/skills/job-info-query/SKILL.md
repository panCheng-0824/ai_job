---
name: job-info-query
description: Query and rank suitable job and company records from local JSON data. Use when users ask for job recommendation, position matching, company matching, internship/job opportunities, or enterprise shortlist generation.
---

# 岗位信息查询 Skill

## 作用

根据用户提供的信息（如专业、技能、期望城市、薪资、经验、岗位方向），在本项目数据源中检索并返回：

1. 合适的岗位信息列表
2. 关联企业信息列表

数据源：
- `business_job.json`（岗位数据）
- `user_business.json`（企业数据）

## 触发时机

当用户出现以下意图时应优先使用本 Skill：
- 岗位推荐 / 岗位匹配
- 根据条件筛选岗位（城市、薪资、方向、技能）
- 推荐目标企业 / 企业列表
- 从学生背景反推可投递岗位

## 执行步骤

1. 提取用户约束
   - 硬条件：城市、岗位类别、薪资、学历、经验
   - 软条件：技能关键词、职业兴趣、发展方向
2. 在 `business_job.json` 中匹配岗位
   - 优先匹配 `job_title`、`job_category`、`skills_required`
   - 次级匹配 `city`、`salary_range_month`、`experience_required`
3. 生成岗位候选列表（按匹配度排序）
   - 必须给出匹配理由（2-3 条）
4. 基于岗位中的 `company_relation.credit_code` 去 `user_business.json` 查企业详情
5. 输出企业候选列表（按“岗位匹配关联度 + 企业信息完整度”排序）

## 输出格式（必须）

按以下结构组织回复，避免只给笼统建议：

```markdown
## 岗位推荐列表（Top N）
- 岗位：<job_title>（<job_id>）
  - 城市/薪资：<city> / <salary_range_month>
  - 匹配理由：<理由1>；<理由2>
  - 关键技能：<skills_required>
  - 企业：<company_name>

## 企业推荐列表（Top N）
- 企业：<company_name>（<credit_code>）
  - 行业/规模：<industry> / <employee_count_range>
  - 关联岗位：<job_title1>, <job_title2>
  - 推荐原因：<原因1>；<原因2>

## 补充建议
- <投递建议或信息缺口>
```

## 约束规则

- 不得编造不存在于 JSON 中的岗位或企业字段
- 如果匹配较弱，要明确说明“基于近似匹配”
- 如果用户条件不足，先给初版推荐，再补充“建议补充信息”
- 当岗位推荐为空时，仍需返回企业列表（可基于城市/行业近似）

## 检索优先级

优先级从高到低：
1. `skills_required` 精确包含
2. `job_title` / `job_category` 语义一致
3. `city` 一致
4. `experience_required` 接近
5. `salary_range_month` 区间接近

