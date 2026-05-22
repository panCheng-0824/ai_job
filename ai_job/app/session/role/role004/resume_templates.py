"""
ROLE004 — 简历模版目录（与 web_job ``modules/resume/templates.js`` 对齐）。

维护 6 种模版的：
- ``template_id`` / 中文名称 / 适用场景说明
- ``section_keys`` 与各分段填写引导（hint / placeholder）
- ``basic`` 字段、``intent`` 字段约定
- 供 LLM 生成 JSON 与 ``normalize_resume_content`` 充填左侧表单使用

前端模版变更时请同步更新本文件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

IntentMode = Literal["full", "compact"]

# 与前端 SECTION_ALIAS_GROUPS 一致：切换模版时字段可互认
SECTION_ALIAS_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("教育背景",),
    ("实习/工作经历", "主要经历", "销售与客户经历"),
    ("项目经历", "作品集/项目", "科研经历"),
    ("技能与证书", "技能与荣誉", "技术栈", "设计技能", "学术技能"),
    ("自我评价", "个人风格", "研究兴趣"),
    ("开源/竞赛", "获奖与展览", "论文与专利"),
    ("求职意向说明",),
    ("业绩亮点",),
)

DEFAULT_TEMPLATE_ID = "standard_cn"

# 与 web_job prefillBasicFromPortrait / buildBasicForSave 键名一致
BASIC_FIELD_KEYS: Tuple[str, ...] = (
    "姓名",
    "学号",
    "手机",
    "邮箱",
    "学校",
    "院系",
    "专业",
    "班级",
    "学历",
    "毕业时间",
    "籍贯",
    "通信地址",
)

INTENT_FIELD_KEYS: Tuple[str, ...] = ("targetJobs", "targetCompanies")


@dataclass(frozen=True)
class SectionFieldSpec:
    """单个分段的填写说明（送入模型提示与文档）。"""

    key: str
    hint: str
    placeholder: str
    multi: bool = True
    rows: int = 5


@dataclass(frozen=True)
class ResumeTemplateSpec:
    """一种简历模版的完整规格。"""

    id: str
    name: str
    badge: str
    description: str
    highlights: Tuple[str, ...]
    intent_mode: IntentMode
    section_keys: Tuple[str, ...]
    sections: Tuple[SectionFieldSpec, ...]

    def section_map(self) -> Dict[str, SectionFieldSpec]:
        return {s.key: s for s in self.sections}

    def empty_sections_skeleton(self) -> Dict[str, List[Dict[str, str]]]:
        """前端 ``sections`` 空骨架：每键一条 ``{title, body}``。"""
        return {key: [{"title": "", "body": ""}] for key in self.section_keys}


def _sec(
    key: str,
    hint: str,
    placeholder: str,
    *,
    multi: bool = True,
    rows: int = 5,
) -> SectionFieldSpec:
    return SectionFieldSpec(key=key, hint=hint, placeholder=placeholder, multi=multi, rows=rows)


RESUME_TEMPLATES: Tuple[ResumeTemplateSpec, ...] = (
    ResumeTemplateSpec(
        id="standard_cn",
        name="标准中文简历",
        badge="校招通用",
        description="模块最全：区分实习/工作与项目，适合多数综合类、管培与职能岗。",
        highlights=("5 个正文块", "实习/工作分开写", "证书与自评独立"),
        intent_mode="full",
        section_keys=("教育背景", "实习/工作经历", "项目经历", "技能与证书", "自我评价"),
        sections=(
            _sec(
                "教育背景",
                "时间倒序；写清学校、专业、学历，可附主修课程与成绩。",
                "例：2022.09–2026.06  XX大学  信息管理与信息系统  本科\n主修：数据结构、数据库…  GPA 3.6/4.0",
                rows=4,
            ),
            _sec(
                "实习/工作经历",
                "每段经历单独成段：公司、岗位、时间 + 3～5 条成果（尽量量化）。",
                "例：2025.07–2025.09  XX公司  产品助理实习生\n- 参与需求评审…\n- 输出 PRD 3 份…",
                rows=6,
            ),
            _sec(
                "项目经历",
                "突出你在项目中的角色、难点与可量化结果。",
                "例：校园二手交易平台（队长）\n- 技术栈：Vue + Spring Boot\n- 负责…，上线后日活…",
                rows=6,
            ),
            _sec(
                "技能与证书",
                "语言、工具、证书分行列出，与目标岗位相关的放前面。",
                "例：英语 CET-6；熟练使用 Office / SQL；驾驶证 C1…",
                multi=False,
                rows=4,
            ),
            _sec(
                "自我评价",
                "2～4 句即可，避免空泛形容词，最好对应上文经历。",
                "例：逻辑清晰、沟通主动，有跨部门协作与从 0 到 1 落地经验…",
                multi=False,
                rows=3,
            ),
        ),
    ),
    ResumeTemplateSpec(
        id="compact_cn",
        name="简洁一页",
        badge="一页纸",
        description="仅 4 个正文块，经历合并书写；求职意向可写入「求职意向说明」以控制篇幅。",
        highlights=("4 个正文块", "经历合并为一栏", "适合一页投递"),
        intent_mode="compact",
        section_keys=("教育背景", "主要经历", "技能与荣誉", "求职意向说明"),
        sections=(
            _sec(
                "教育背景",
                "一行概括即可，细节放到「主要经历」。",
                "例：XX大学 · 市场营销 · 本科 · 2026 届",
                rows=3,
            ),
            _sec(
                "主要经历",
                "实习、项目、学生工作可合并写在本栏，用【标签】分段。",
                "例：\n【实习】2025 夏 XX公司 运营实习生 — 负责活动复盘，转化率提升 12%\n【项目】校级创业赛 — 队长，获省赛银奖",
                rows=8,
            ),
            _sec(
                "技能与荣誉",
                "技能与荣誉混排，每条尽量一行，控制总字数。",
                "例：Excel 数据透视；校级奖学金；英语六级…",
                multi=False,
                rows=4,
            ),
            _sec(
                "求职意向说明",
                "简洁模版建议在此写明岗位、城市、行业；上方「求职意向」可留空或作备注。",
                "例：意向岗位：市场/运营管培 | 城市：上海、杭州 | 到岗：2026.07\n补充：可接受出差…",
                multi=False,
                rows=4,
            ),
        ),
    ),
    ResumeTemplateSpec(
        id="tech_cn",
        name="技术向",
        badge="研发 / 算法",
        description="突出技术栈、项目细节与开源/竞赛，自我评价偏工程能力而非软技能堆砌。",
        highlights=("技术栈独立成栏", "项目可写架构", "含开源/竞赛"),
        intent_mode="full",
        section_keys=("教育背景", "技术栈", "项目经历", "开源/竞赛", "自我评价"),
        sections=(
            _sec(
                "教育背景",
                "可写与岗位相关的课程、实验室或导师方向。",
                "例：XX大学  软件工程  本科  |  相关课程：OS、计网、机器学习…",
                rows=3,
            ),
            _sec(
                "技术栈",
                "按类别分组；只写熟练使用的，面试可能被深挖的放前面。",
                "例：\n语言：Java / Python / Go\n框架：Spring Boot、Vue3、PyTorch\n工具：Git、Docker、MySQL、Redis",
                multi=False,
                rows=5,
            ),
            _sec(
                "项目经历",
                "建议写清：背景、你的职责、技术选型、难点与量化指标。",
                "例：分布式任务调度平台\n- 背景：…\n- 职责：架构设计…\n- 技术：Kafka + Redis…\n- 结果：QPS …，延迟降低 …%",
                rows=8,
            ),
            _sec(
                "开源/竞赛",
                "无则写「暂无」或留空；有链接可附 URL。",
                "例：GitHub xxx/star…；ACM 区域赛铜奖；Kaggle Top 10%…",
                multi=False,
                rows=4,
            ),
            _sec(
                "自我评价",
                "偏技术关键词，避免与「技术栈」「项目」重复罗列。",
                "例：熟悉后端开发与性能调优，有完整项目交付与线上排障经验…",
                multi=False,
                rows=3,
            ),
        ),
    ),
    ResumeTemplateSpec(
        id="design_cn",
        name="设计创意向",
        badge="UI / 视觉",
        description="突出作品集与视觉能力，适合 UI、平面、新媒体与设计类岗位。",
        highlights=("作品集独立成栏", "强调获奖与展览", "个人风格说明"),
        intent_mode="full",
        section_keys=("教育背景", "作品集/项目", "设计技能", "获奖与展览", "个人风格"),
        sections=(
            _sec(
                "教育背景",
                "可补充设计相关课程、工作室或导师项目。",
                "例：XX大学  视觉传达设计  本科  |  主修：版式、品牌、交互基础…",
                rows=3,
            ),
            _sec(
                "作品集/项目",
                "每个作品写清：类型、你的角色、工具、成果；可附作品集链接。",
                "例：\n【品牌 VI】XX 文创品牌全案 — 负责 Logo 与延展…\n【UI】校园 App 改版 — Figma 高保真…",
                rows=8,
            ),
            _sec(
                "设计技能",
                "按熟练度排序，与目标岗位（UI、品牌、动效等）对齐。",
                "例：Figma / PS / AI / AE；插画；动效基础…",
                multi=False,
                rows=4,
            ),
            _sec(
                "获奖与展览",
                "竞赛、展览、专利或媒体报道均可；无则可写「暂无」。",
                "例：全国大学生广告艺术节学院奖银奖；校级毕业展入选作品…",
                multi=False,
                rows=4,
            ),
            _sec(
                "个人风格",
                "2～3 句概括审美与协作方式，避免空泛「有创意」。",
                "例：偏好简约信息层级与品牌叙事…",
                multi=False,
                rows=3,
            ),
        ),
    ),
    ResumeTemplateSpec(
        id="sales_cn",
        name="销售商务向",
        badge="销售 / 市场",
        description="以业绩与客户关系为主，适合销售、BD、客户经理与市场拓展岗。",
        highlights=("业绩亮点专栏", "客户经历可量化", "证书与自评"),
        intent_mode="full",
        section_keys=("教育背景", "销售与客户经历", "业绩亮点", "技能与证书", "自我评价"),
        sections=(
            _sec(
                "教育背景",
                "商科、管理类专业可写相关课程；非对口专业可强调 transferable 能力。",
                "例：XX大学  市场营销  本科  |  相关：消费者行为、商务谈判…",
                rows=3,
            ),
            _sec(
                "销售与客户经历",
                "写清客户类型、跟进动作、签约/回款/转化率等可量化结果。",
                "例：2025.03–2025.08  XX科技  大客户销售实习生\n- 跟进 30+ 企业客户，签约 6 家…",
                rows=7,
            ),
            _sec(
                "业绩亮点",
                "用数字说话；可与上栏不重复，挑最强 3～5 条。",
                "例：季度业绩 TOP 10%；单场活动获客 500+；复购率提升 15%…",
                multi=False,
                rows=5,
            ),
            _sec(
                "技能与证书",
                "工具、语言、行业证书；与目标行业相关的优先。",
                "例：CRM（Salesforce）；商务 PPT；驾照；英语流利…",
                multi=False,
                rows=4,
            ),
            _sec(
                "自我评价",
                "突出商务软技能，与上文业绩呼应。",
                "例：结果导向、抗压与陌拜经验丰富…",
                multi=False,
                rows=3,
            ),
        ),
    ),
    ResumeTemplateSpec(
        id="academic_cn",
        name="学术科研向",
        badge="保研 / 科研",
        description="适合保研、考研复试、科研助理与实验室岗位，突出论文与科研经历。",
        highlights=("科研经历专栏", "论文与专利", "研究兴趣"),
        intent_mode="full",
        section_keys=("教育背景", "科研经历", "论文与专利", "学术技能", "研究兴趣"),
        sections=(
            _sec(
                "教育背景",
                "成绩、排名、核心课程；若有保研/推免资格可注明。",
                "例：XX大学  生物科学  本科  GPA 3.8/4.0  排名 5/120\n相关课程：分子生物学…",
                rows=4,
            ),
            _sec(
                "科研经历",
                "实验室、导师、时间、课题、你的贡献；尽量量化（样本量、指标等）。",
                "例：XX实验室（导师：张教授）2024.09–至今\n课题：…；职责：实验设计…",
                rows=8,
            ),
            _sec(
                "论文与专利",
                "按规范引用格式；在投需标注状态；无则写「暂无」。",
                "例：\n[1] 作者排序，题目，期刊/会议，年份（在投/已发表）\n专利：…",
                rows=6,
            ),
            _sec(
                "学术技能",
                "实验技术、统计与编程、写作工具分开列。",
                "例：Python / R；统计分析；Western Blot；LaTeX…",
                multi=False,
                rows=4,
            ),
            _sec(
                "研究兴趣",
                "写明方向与目标导师/实验室（如已知）；与申请场景一致。",
                "例：感兴趣方向：肿瘤免疫微环境；计划攻读方向：细胞生物学…",
                multi=False,
                rows=4,
            ),
        ),
    ),
)

_TEMPLATE_BY_ID: Dict[str, ResumeTemplateSpec] = {t.id: t for t in RESUME_TEMPLATES}


def list_template_ids() -> List[str]:
    return [t.id for t in RESUME_TEMPLATES]


def get_template(template_id: Optional[str]) -> ResumeTemplateSpec:
    tid = (template_id or "").strip() or DEFAULT_TEMPLATE_ID
    return _TEMPLATE_BY_ID.get(tid) or _TEMPLATE_BY_ID[DEFAULT_TEMPLATE_ID]


def resolve_template_id(
    *,
    explicit: str = "",
    context_cards: Optional[List[Dict[str, Any]]] = None,
    draft_content: Optional[Dict[str, Any]] = None,
) -> str:
    """
    解析本轮应使用的模版 id。

    优先级：显式参数 → resume_draft 卡片 payload → draft content 内 templateId → 默认 standard_cn。
    """
    if (explicit or "").strip():
        return get_template(explicit).id

    for card in context_cards or []:
        if not isinstance(card, dict):
            continue
        kind = str(card.get("type") or card.get("kind") or "").strip().lower()
        if kind != "resume_draft":
            continue
        payload = card.get("payload")
        if isinstance(payload, dict):
            tid = str(payload.get("template_id") or payload.get("templateId") or "").strip()
            if tid:
                return get_template(tid).id

    if isinstance(draft_content, dict):
        tid = str(draft_content.get("templateId") or draft_content.get("template_id") or "").strip()
        if tid:
            return get_template(tid).id

    return DEFAULT_TEMPLATE_ID


def map_section_key_to_template(raw_key: str, template: ResumeTemplateSpec) -> str:
    """将模型可能输出的别名分段键映射到当前模版合法键名。"""
    key = (raw_key or "").strip()
    if not key:
        return ""
    if key in template.section_keys:
        return key
    for group in SECTION_ALIAS_GROUPS:
        if key in group:
            for candidate in group:
                if candidate in template.section_keys:
                    return candidate
    return ""


def build_basic_skeleton() -> Dict[str, str]:
    return {k: "" for k in BASIC_FIELD_KEYS}


def build_intent_skeleton(template: ResumeTemplateSpec) -> Dict[str, str]:
    return {"targetJobs": "", "targetCompanies": ""}


def build_llm_template_guide(template_id: Optional[str] = None) -> str:
    """生成送入 LLM 的模版说明块（中文）。"""
    tpl = get_template(template_id)
    lines = [
        f"【目标模版】{tpl.name}（template_id={tpl.id}，{tpl.badge}）",
        f"【适用场景】{tpl.description}",
        f"【亮点】{'；'.join(tpl.highlights)}",
        f"【求职意向字段】intent_mode={tpl.intent_mode}；"
        + (
            "须输出 intent.targetJobs / intent.targetCompanies。"
            if tpl.intent_mode == "full"
            else "本模版篇幅紧凑，岗位/城市/行业建议写入分段「求职意向说明」，intent 可留空或简短备注。"
        ),
        "",
        "【sections 分段键名（必须完全一致，不得自创键名）】",
    ]
    for spec in tpl.sections:
        multi_note = "可多段" if spec.multi else "通常单段"
        lines.append(f"- 「{spec.key}」（{multi_note}）")
        lines.append(f"  填写要点：{spec.hint}")
        lines.append(f"  示例：{spec.placeholder[:200]}{'…' if len(spec.placeholder) > 200 else ''}")
    lines.append("")
    lines.append(
        "【sections 数组元素格式】每项为 {\"title\":\"小标题可选\",\"body\":\"正文\"}；"
        "body 内多条成果用换行并以 - 开头。"
    )
    return "\n".join(lines)


def build_llm_json_schema_block(template_id: Optional[str] = None) -> str:
    """生成 JSON 根结构说明（键名与模版绑定）。"""
    tpl = get_template(template_id)
    keys_json = ", ".join(f'"{k}"' for k in tpl.section_keys)
    basic_keys = ", ".join(f'"{k}": ""' for k in BASIC_FIELD_KEYS)
    return f"""{{
  "templateId": "{tpl.id}",
  "basic": {{ {basic_keys} }},
  "intent": {{ "targetJobs": "", "targetCompanies": "" }},
  "sections": {{
    键名必须且仅能使用：{keys_json}
    每键值为 [{{"title": "", "body": ""}}] 形式的数组
  }},
  "extraNotes": ""
}}"""


def template_catalog_markdown() -> str:
    """供维护者阅读的 6 模版一览（Markdown）。"""
    parts = ["# ROLE004 简历模版目录\n"]
    for tpl in RESUME_TEMPLATES:
        parts.append(f"## {tpl.name} (`{tpl.id}`)\n")
        parts.append(f"- 标签：{tpl.badge}\n")
        parts.append(f"- 说明：{tpl.description}\n")
        parts.append(f"- 分段：{'、'.join(tpl.section_keys)}\n")
    return "\n".join(parts)
