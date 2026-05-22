/**
 * 简历模版：除分段标题外，还定义填写引导、预览样式与切换时的字段映射。
 */

/** 切换模版时，同组字段可互相继承正文（避免「换了模版内容像丢了」） */
export const SECTION_ALIAS_GROUPS = [
  ["教育背景"],
  ["实习/工作经历", "主要经历", "销售与客户经历"],
  ["项目经历", "作品集/项目", "科研经历"],
  ["技能与证书", "技能与荣誉", "技术栈", "设计技能", "学术技能"],
  ["自我评价", "个人风格", "研究兴趣"],
  ["开源/竞赛", "获奖与展览", "论文与专利"],
  ["求职意向说明"],
  ["业绩亮点"]
];

/**
 * @typedef {{ placeholder?: string, hint?: string, rows?: number, multi?: boolean, entryLabel?: string }} SectionField
 */

/**
 * @typedef {Object} ResumeTemplate
 * @property {string} id
 * @property {string} name
 * @property {string} badge
 * @property {string} accent
 * @property {string} description
 * @property {string[]} highlights
 * @property {'full' | 'compact'} intentMode
 * @property {string[]} sectionKeys
 * @property {Record<string, SectionField>} sections
 */

/** @type {ResumeTemplate[]} */
export const RESUME_TEMPLATES = [
  {
    id: "standard_cn",
    name: "标准中文简历",
    badge: "校招通用",
    accent: "#4f46e5",
    description: "模块最全：区分实习/工作与项目，适合多数综合类、管培与职能岗。",
    highlights: ["5 个正文块", "实习/工作分开写", "证书与自评独立"],
    intentMode: "full",
    sectionKeys: ["教育背景", "实习/工作经历", "项目经历", "技能与证书", "自我评价"],
    sections: {
      教育背景: {
        placeholder:
          "例：2022.09–2026.06  XX大学  信息管理与信息系统  本科\n主修：数据结构、数据库…  GPA 3.6/4.0",
        hint: "时间倒序；写清学校、专业、学历，可附主修课程与成绩。",
        rows: 4
      },
      "实习/工作经历": {
        placeholder:
          "例：2025.07–2025.09  XX公司  产品助理实习生\n- 参与需求评审…\n- 输出 PRD 3 份…",
        hint: "每段经历单独成段：公司、岗位、时间 + 3～5 条成果（尽量量化）。",
        rows: 6
      },
      项目经历: {
        placeholder:
          "例：校园二手交易平台（队长）\n- 技术栈：Vue + Spring Boot\n- 负责…，上线后日活…",
        hint: "突出你在项目中的角色、难点与可量化结果。",
        rows: 6
      },
      技能与证书: {
        placeholder: "例：英语 CET-6；熟练使用 Office / SQL；驾驶证 C1…",
        hint: "语言、工具、证书分行列出，与目标岗位相关的放前面。",
        rows: 4
      },
      自我评价: {
        placeholder: "例：逻辑清晰、沟通主动，有跨部门协作与从 0 到 1 落地经验…",
        hint: "2～4 句即可，避免空泛形容词，最好对应上文经历。",
        rows: 3
      }
    }
  },
  {
    id: "compact_cn",
    name: "简洁一页",
    badge: "一页纸",
    accent: "#059669",
    description: "仅 4 个正文块，经历合并书写；求职意向可写入「求职意向说明」以控制篇幅。",
    highlights: ["4 个正文块", "经历合并为一栏", "适合一页投递"],
    intentMode: "compact",
    sectionKeys: ["教育背景", "主要经历", "技能与荣誉", "求职意向说明"],
    sections: {
      教育背景: {
        placeholder: "例：XX大学 · 市场营销 · 本科 · 2026 届",
        hint: "一行概括即可，细节放到「主要经历」。",
        rows: 3
      },
      主要经历: {
        placeholder:
          "例：\n【实习】2025 夏 XX公司 运营实习生 — 负责活动复盘，转化率提升 12%\n【项目】校级创业赛 — 队长，获省赛银奖",
        hint: "实习、项目、学生工作可合并写在本栏，用【标签】分段。",
        rows: 8
      },
      技能与荣誉: {
        placeholder: "例：Excel 数据透视；校级奖学金；英语六级…",
        hint: "技能与荣誉混排，每条尽量一行，控制总字数。",
        rows: 4
      },
      求职意向说明: {
        placeholder:
          "例：意向岗位：市场/运营管培 | 城市：上海、杭州 | 到岗：2026.07\n补充：可接受出差，偏好互联网与消费品行业…",
        hint: "简洁模版建议在此写明岗位、城市、行业；上方「求职意向」可留空或作备注。",
        rows: 4
      }
    }
  },
  {
    id: "tech_cn",
    name: "技术向",
    badge: "研发 / 算法",
    accent: "#d97706",
    description: "突出技术栈、项目细节与开源/竞赛，自我评价偏工程能力而非软技能堆砌。",
    highlights: ["技术栈独立成栏", "项目可写架构", "含开源/竞赛"],
    intentMode: "full",
    sectionKeys: ["教育背景", "技术栈", "项目经历", "开源/竞赛", "自我评价"],
    sections: {
      教育背景: {
        placeholder: "例：XX大学  软件工程  本科  |  相关课程：OS、计网、机器学习…",
        hint: "可写与岗位相关的课程、实验室或导师方向。",
        rows: 3
      },
      技术栈: {
        placeholder:
          "例：\n语言：Java / Python / Go\n框架：Spring Boot、Vue3、PyTorch\n工具：Git、Docker、MySQL、Redis",
        hint: "按类别分组；只写熟练使用的，面试可能被深挖的放前面。",
        rows: 5
      },
      项目经历: {
        placeholder:
          "例：分布式任务调度平台\n- 背景：…\n- 职责：架构设计 / 核心模块…\n- 技术：Kafka + Redis + …\n- 结果：QPS …，延迟降低 …%",
        hint: "建议写清：背景、你的职责、技术选型、难点与量化指标。",
        rows: 8
      },
      "开源/竞赛": {
        placeholder: "例：GitHub xxx/star…；ACM 区域赛铜奖；Kaggle Top 10%…",
        hint: "无则写「暂无」或删去本栏内容；有链接可附 URL。",
        rows: 4
      },
      自我评价: {
        placeholder: "例：熟悉后端开发与性能调优，有完整项目交付与线上排障经验…",
        hint: "偏技术关键词，避免与「技术栈」「项目」重复罗列。",
        rows: 3
      }
    }
  },
  {
    id: "design_cn",
    name: "设计创意向",
    badge: "UI / 视觉",
    accent: "#db2777",
    description: "突出作品集与视觉能力，适合 UI、平面、新媒体与设计类岗位。",
    highlights: ["作品集独立成栏", "强调获奖与展览", "个人风格说明"],
    intentMode: "full",
    sectionKeys: ["教育背景", "作品集/项目", "设计技能", "获奖与展览", "个人风格"],
    sections: {
      教育背景: {
        placeholder: "例：XX大学  视觉传达设计  本科  |  主修：版式、品牌、交互基础…",
        hint: "可补充设计相关课程、工作室或导师项目。",
        rows: 3
      },
      "作品集/项目": {
        placeholder:
          "例：\n【品牌 VI】XX 文创品牌全案 — 负责 Logo 与延展，落地物料 12 件\n【UI】校园 App 改版 — Figma 高保真，用户测试后留存 +8%",
        hint: "每个作品写清：类型、你的角色、工具、成果；可附作品集链接。",
        rows: 8
      },
      设计技能: {
        placeholder: "例：Figma / PS / AI / AE；插画；动效基础；熟悉设计规范与组件库…",
        hint: "按熟练度排序，与目标岗位（UI、品牌、动效等）对齐。",
        rows: 4
      },
      获奖与展览: {
        placeholder: "例：全国大学生广告艺术节学院奖银奖；校级毕业展入选作品…",
        hint: "竞赛、展览、专利或媒体报道均可；无则可写「暂无」。",
        rows: 4
      },
      个人风格: {
        placeholder: "例：偏好简约信息层级与品牌叙事；善于将复杂需求拆解为可落地的视觉方案…",
        hint: "2～3 句概括审美与协作方式，避免空泛「有创意」。",
        rows: 3
      }
    }
  },
  {
    id: "sales_cn",
    name: "销售商务向",
    badge: "销售 / 市场",
    accent: "#dc2626",
    description: "以业绩与客户关系为主，适合销售、BD、客户经理与市场拓展岗。",
    highlights: ["业绩亮点专栏", "客户经历可量化", "证书与自评"],
    intentMode: "full",
    sectionKeys: ["教育背景", "销售与客户经历", "业绩亮点", "技能与证书", "自我评价"],
    sections: {
      教育背景: {
        placeholder: "例：XX大学  市场营销  本科  |  相关：消费者行为、商务谈判…",
        hint: "商科、管理类专业可写相关课程；非对口专业可强调 transferable 能力。",
        rows: 3
      },
      销售与客户经历: {
        placeholder:
          "例：2025.03–2025.08  XX科技  大客户销售实习生\n- 跟进 30+ 企业客户，签约 6 家，回款 80 万\n- 独立完成方案讲解与异议处理…",
        hint: "写清客户类型、跟进动作、签约/回款/转化率等可量化结果。",
        rows: 7
      },
      业绩亮点: {
        placeholder:
          "例：季度业绩 TOP 10%；单场活动获客 500+；复购率提升 15%；主导 cross-sell 方案 2 套…",
        hint: "用数字说话；可与上栏不重复，挑最强 3～5 条。",
        rows: 5
      },
      技能与证书: {
        placeholder: "例：CRM（Salesforce）；商务 PPT；驾照；英语流利；证券/基金从业（如有）…",
        hint: "工具、语言、行业证书；与目标行业相关的优先。",
        rows: 4
      },
      自我评价: {
        placeholder: "例：结果导向、抗压与陌拜经验丰富，擅长客户需求挖掘与长期关系维护…",
        hint: "突出商务软技能，与上文业绩呼应。",
        rows: 3
      }
    }
  },
  {
    id: "academic_cn",
    name: "学术科研向",
    badge: "保研 / 科研",
    accent: "#2563eb",
    description: "适合保研、考研复试、科研助理与实验室岗位，突出论文与科研经历。",
    highlights: ["科研经历专栏", "论文与专利", "研究兴趣"],
    intentMode: "full",
    sectionKeys: ["教育背景", "科研经历", "论文与专利", "学术技能", "研究兴趣"],
    sections: {
      教育背景: {
        placeholder:
          "例：XX大学  生物科学  本科  GPA 3.8/4.0  排名 5/120\n相关课程：分子生物学、生物信息学…",
        hint: "成绩、排名、核心课程；若有保研/推免资格可注明。",
        rows: 4
      },
      科研经历: {
        placeholder:
          "例：XX实验室（导师：张教授）2024.09–至今\n课题：…；职责：实验设计、数据分析；成果：…",
        hint: "实验室、导师、时间、课题、你的贡献；尽量量化（样本量、指标等）。",
        rows: 8
      },
      论文与专利: {
        placeholder:
          "例：\n[1] 作者排序，题目，期刊/会议，年份（在投/已发表）\n专利：一种…（申请号…，第几发明人）",
        hint: "按规范引用格式；在投需标注状态；无则写「暂无」。",
        rows: 6
      },
      学术技能: {
        placeholder: "例：Python / R；统计分析；Western Blot；测序数据分析；LaTeX；文献检索…",
        hint: "实验技术、统计与编程、写作工具分开列。",
        rows: 4
      },
      研究兴趣: {
        placeholder: "例：感兴趣方向：肿瘤免疫微环境；计划攻读方向：细胞生物学；希望加入…实验室…",
        hint: "写明方向与目标导师/实验室（如已知）；与申请场景一致。",
        rows: 4
      }
    }
  }
];

export function getTemplateById(id) {
  return RESUME_TEMPLATES.find((t) => t.id === id) || RESUME_TEMPLATES[0];
}

/** @param {ResumeTemplate} template @param {string} sectionKey @returns {SectionField} */
export function getSectionField(template, sectionKey) {
  const field = template.sections?.[sectionKey];
  return {
    placeholder: field?.placeholder || `填写${sectionKey}…`,
    hint: field?.hint || "",
    rows: field?.rows ?? 5
  };
}

export { mapSectionsOnTemplateChange } from "./sectionsModel";
