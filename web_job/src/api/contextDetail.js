import { apiGet } from "./client";
import { fmtRegisteredCapital } from "../utils/formatCompany";
import { richTextToPlain } from "../utils/richText";
import { fetchResumeStore } from "../modules/resume/api";
import { formatSectionItemsText, normalizeSectionItems } from "../modules/resume/sectionsModel";
import { pickSeriesDefaultVersion, stripTimeCopySuffix } from "../modules/resume/storage";

/** 送入模型的隐藏上下文最大字符数 */
const MESSAGE_CONTEXT_MAX = 12000;

/**
 * 字段标签：与 server_job 0605 schema（t_biz_jobs_info / t_biz_compary_info）对齐。
 */
const JOB_FIELD_LABELS = {
  id: "岗位ID",
  jobid: "岗位ID",
  yrdw: "用人单位ID",
  companyId: "用人单位ID",
  zwmc: "职位名称",
  jobName: "职位名称",
  zwlbText: "职位类别",
  salaryRange: "月薪级别",
  xqrs: "需求人数",
  vacancies: "需求人数",
  jzrq: "截止日期",
  gzdd: "工作地点",
  address: "工作地点",
  area: "工作地区",
  xlyqText: "学历要求",
  education: "学历要求",
  nlqxText: "能力需求",
  xbyqText: "性别要求",
  sxqText: "实习期",
  gjzText: "关键字",
  companyName: "用人单位",
  companyType: "公司性质",
  industry: "行业类型",
  hylx: "行业类型",
  lxr: "联系人",
  lxryx: "联系人邮箱",
  lxrdh: "联系人电话",
  lxrsjh: "联系人手机",
  sxsj: "生效时间",
  createTime: "创建时间",
  synRag: "知识库同步状态",
  ragMdPath: "知识库文档路径",
  content: "职位描述",
  zwms: "职位描述"
};

const COMPANY_FIELD_LABELS = {
  id: "企业ID",
  wid: "企业ID",
  gsmc: "公司名称",
  companyName: "公司名称",
  companyType: "单位性质",
  companySize: "公司规模",
  hylx: "行业类型",
  area: "行业类型",
  region: "办公地区",
  address: "办公地址",
  dwzcdz: "注册地址",
  website: "单位邮箱",
  dwyx: "单位邮箱",
  gszy: "公司主页",
  zczj: "注册资金（万元）",
  dwjj: "单位简介",
  jglx: "机构类型",
  zzjgdm: "组织机构代码",
  lxr: "联系人",
  lxrdh: "联系人电话",
  lxrsjh: "联系人手机"
};

function clip(text, max = MESSAGE_CONTEXT_MAX) {
  const s = String(text || "").trim();
  if (s.length <= max) return s;
  return `${s.slice(0, max)}\n…（已截断）`;
}

/** 取非空字符串；兼容 camelCase 与历史 snake_case */
function pick(obj, ...keys) {
  if (!obj || typeof obj !== "object") return "";
  for (const key of keys) {
    const v = obj[key];
    if (v === null || v === undefined) continue;
    const s = String(v).trim();
    if (s) return s;
  }
  return "";
}

function line(label, value) {
  const s = value === null || value === undefined ? "" : String(value).trim();
  if (!s) return "";
  return `${label}：${s}`;
}

/** 多键回退后按统一标签输出一行 */
function lineFrom(obj, label, ...keys) {
  return line(label, pick(obj, ...keys));
}

function blockSection(title, lines) {
  const body = (lines || []).filter(Boolean);
  if (!body.length) return "";
  return `【${title}】\n${body.join("\n")}`;
}

function formatSynRag(raw) {
  const v = raw === null || raw === undefined ? "" : String(raw).trim();
  if (v === "1") return "已同步";
  if (v === "0") return "未同步";
  return v;
}

function formatEpoch(ms) {
  const n = Number(ms);
  if (!n || Number.isNaN(n)) return "";
  try {
    return new Date(n).toLocaleString("zh-CN", { hour12: false });
  } catch {
    return "";
  }
}

/**
 * 岗位详情 → 模型隐藏文本（0605 t_biz_jobs_info）。
 * @param {Record<string, unknown>} job GET /api/jobs/{id} 响应
 */
function formatJobDetail(job) {
  if (!job) return "（未获取到岗位详情）";

  const basicLines = [
    lineFrom(job, JOB_FIELD_LABELS.id, "id", "job_id", "jobid"),
    lineFrom(job, JOB_FIELD_LABELS.jobName, "jobName", "zwmc", "job_name", "job_title"),
    lineFrom(job, JOB_FIELD_LABELS.zwlbText, "zwlbText"),
    lineFrom(job, JOB_FIELD_LABELS.companyName, "companyName", "company_name"),
    lineFrom(job, JOB_FIELD_LABELS.companyId, "companyId", "yrdw", "company_id"),
    lineFrom(job, JOB_FIELD_LABELS.companyType, "companyType", "company_type"),
    lineFrom(job, JOB_FIELD_LABELS.industry, "industry"),
    lineFrom(job, JOB_FIELD_LABELS.area, "area", "district"),
    lineFrom(job, JOB_FIELD_LABELS.address, "address", "gzdd", "city"),
    lineFrom(job, JOB_FIELD_LABELS.xlyqText, "xlyqText", "education"),
    lineFrom(job, JOB_FIELD_LABELS.nlqxText, "nlqxText"),
    lineFrom(job, JOB_FIELD_LABELS.salaryRange, "salaryRange", "salary_range_month", "salary"),
    lineFrom(job, JOB_FIELD_LABELS.sxqText, "sxqText"),
    lineFrom(job, JOB_FIELD_LABELS.vacancies, "vacancies", "xqrs"),
    lineFrom(job, JOB_FIELD_LABELS.jzrq, "jzrq"),
    lineFrom(job, JOB_FIELD_LABELS.gjzText, "gjzText"),
    lineFrom(job, JOB_FIELD_LABELS.xbyqText, "xbyqText")
  ];

  const contactLines = [
    lineFrom(job, JOB_FIELD_LABELS.lxr, "lxr"),
    lineFrom(job, JOB_FIELD_LABELS.lxryx, "lxryx"),
    lineFrom(job, JOB_FIELD_LABELS.lxrdh, "lxrdh"),
    lineFrom(job, JOB_FIELD_LABELS.lxrsjh, "lxrsjh")
  ];

  const metaLines = [
    lineFrom(job, JOB_FIELD_LABELS.sxsj, "sxsj"),
    lineFrom(job, JOB_FIELD_LABELS.createTime, "createTime", "create_time"),
    line(JOB_FIELD_LABELS.synRag, formatSynRag(pick(job, "synRag", "syn_rag"))),
    lineFrom(job, JOB_FIELD_LABELS.ragMdPath, "ragMdPath", "rag_md_path")
  ];

  const content = richTextToPlain(pick(job, "content", "zwms", "job_description", "description"));

  const sections = [
    blockSection("岗位概要", basicLines),
    blockSection("联系信息", contactLines),
    blockSection("时间与知识库", metaLines),
    content ? blockSection(JOB_FIELD_LABELS.content, [content]) : ""
  ].filter(Boolean);

  return clip(sections.join("\n\n") || "（岗位字段为空）");
}

/**
 * 企业详情 → 模型隐藏文本（0605 t_biz_compary_info）。
 * @param {Record<string, unknown>} company GET /api/companies/{creditCode} 响应
 */
function formatCompanyDetail(company) {
  if (!company) return "（未获取到企业详情）";

  const lines = [
    lineFrom(company, COMPANY_FIELD_LABELS.id, "id", "wid", "credit_code"),
    lineFrom(company, COMPANY_FIELD_LABELS.companyName, "companyName", "gsmc", "company_name"),
    lineFrom(company, COMPANY_FIELD_LABELS.companyType, "companyType", "company_type"),
    lineFrom(company, COMPANY_FIELD_LABELS.companySize, "companySize", "company_scale"),
    lineFrom(company, COMPANY_FIELD_LABELS.area, "area", "industry"),
    lineFrom(company, COMPANY_FIELD_LABELS.region, "region"),
    lineFrom(company, COMPANY_FIELD_LABELS.address, "address", "dwbgdz"),
    lineFrom(company, COMPANY_FIELD_LABELS.dwzcdz, "dwzcdz"),
    lineFrom(company, COMPANY_FIELD_LABELS.website, "website", "dwyx"),
    lineFrom(company, COMPANY_FIELD_LABELS.gszy, "gszy"),
    line(COMPANY_FIELD_LABELS.zczj, fmtRegisteredCapital(pick(company, "zczj"))),
    lineFrom(company, COMPANY_FIELD_LABELS.jglx, "jglx"),
    lineFrom(company, COMPANY_FIELD_LABELS.zzjgdm, "zzjgdm"),
    lineFrom(company, COMPANY_FIELD_LABELS.lxr, "lxr"),
    lineFrom(company, COMPANY_FIELD_LABELS.lxrdh, "lxrdh"),
    lineFrom(company, COMPANY_FIELD_LABELS.lxrsjh, "lxrsjh"),
    line(COMPANY_FIELD_LABELS.dwjj, richTextToPlain(pick(company, "dwjj")))
  ];

  return clip(blockSection("企业概要", lines) || "（企业字段为空）");
}

/**
 * 简历详情 → 模型隐藏文本（对齐 StudentResume API：content.basic / intent / sections）。
 * @param {import('../modules/resume/types').ResumeRecord | null} resume
 */
function formatResumeDetail(resume) {
  if (!resume?.content) return "（未获取到简历详情）";

  const c = resume.content;
  const basic = c.basic || {};
  const intent = c.intent || {};

  const headerLines = [
    line("简历名称", stripTimeCopySuffix(resume.displayName || "") || "未命名"),
    line("简历副本ID", pick(resume, "id")),
    line("简历系列ID", pick(resume, "seriesId", "series_id")),
    line("模板", pick(resume, "templateId", "template_id")),
    resume.isSeriesDefault ? line("本简历默认副本", "是") : "",
    resume.isDefault ? line("对话默认简历", "是") : "",
    line("最近更新", formatEpoch(resume.updatedAt))
  ];

  const basicLines = [
    line("姓名", pick(basic, "name", "姓名")),
    line("性别", pick(basic, "gender", "性别")),
    line("手机", pick(basic, "phone", "手机", "mobile")),
    line("邮箱", pick(basic, "email", "邮箱")),
    line("院校", pick(basic, "school", "学校")),
    line("专业", pick(basic, "major", "专业")),
    line("学历", pick(basic, "degree", "学历")),
    line("毕业年份", pick(basic, "gradYear", "grad_year", "毕业年份")),
    line("所在地", pick(basic, "city", "所在地", "城市"))
  ];

  const intentLines = [
    line("意向岗位", pick(intent, "targetJobs", "target_jobs")),
    line("意向企业", pick(intent, "targetCompanies", "target_companies")),
    line("意向城市", pick(intent, "targetCity", "target_city")),
    line("期望薪资", pick(intent, "expectedSalary", "expected_salary"))
  ];

  const sectionBlocks = [];
  const sections = c.sections || {};
  for (const [title, raw] of Object.entries(sections)) {
    const text = formatSectionItemsText(normalizeSectionItems(raw));
    if (text) sectionBlocks.push(blockSection(title, [text]));
  }

  const tail = [];
  if (c.extraNotes && String(c.extraNotes).trim()) {
    tail.push(blockSection("补充说明", [String(c.extraNotes).trim()]));
  }

  const parts = [
    blockSection("简历标识", headerLines),
    blockSection("基本信息", basicLines),
    blockSection("求职意向", intentLines),
    ...sectionBlocks,
    ...tail
  ].filter(Boolean);

  return clip(parts.join("\n\n") || "（简历内容为空）");
}

function buildJobCard(ref, job) {
  const id = pick(job, "id", "job_id", "jobid") || ref.ref_id;
  const title =
    ref.title ||
    pick(job, "jobName", "zwmc", "job_name", "job_title") ||
    id;
  const subtitle =
    ref.subtitle ||
    [pick(job, "address", "gzdd", "city"), pick(job, "area"), pick(job, "companyName")].filter(Boolean).join(" · ");
  return {
    type: "job",
    ref_id: id,
    title,
    subtitle,
    variant: ref.variant || "fav"
  };
}

function buildCompanyCard(ref, company) {
  const id = pick(company, "id", "wid", "credit_code") || ref.ref_id;
  const title = ref.title || pick(company, "companyName", "gsmc", "company_name") || id;
  const subtitle =
    ref.subtitle ||
    [pick(company, "area", "industry"), pick(company, "companySize"), pick(company, "address", "region")]
      .filter(Boolean)
      .join(" · ");
  return {
    type: "company",
    ref_id: id,
    title,
    subtitle,
    variant: ref.variant || "fol"
  };
}

/**
 * 拉取拖入目标的详情，返回展示卡片与送入模型的隐藏文本。
 * @param {{ type: string, ref_id: string, title?: string, subtitle?: string, variant?: string }} ref
 * @param {string} studentId
 */
export async function fetchContextDetail(ref, studentId) {
  const type = ref?.type;
  const id = ref?.ref_id;
  if (!type || !id) throw new Error("无效的引用");

  if (type === "job") {
    const job = await apiGet(`/api/jobs/${encodeURIComponent(id)}`);
    return {
      card: buildJobCard(ref, job),
      message_context: formatJobDetail(job)
    };
  }

  if (type === "company") {
    const company = await apiGet(`/api/companies/${encodeURIComponent(id)}`);
    return {
      card: buildCompanyCard(ref, company),
      message_context: formatCompanyDetail(company)
    };
  }

  if (type === "resume") {
    const sid = (studentId || "").trim();
    let resume = null;
    if (sid) {
      const store = await fetchResumeStore(sid);
      const list = store.resumes || [];
      resume = list.find((r) => r.id === id);
      if (!resume) {
        const bySeries = list.filter((r) => (r.seriesId || r.id) === id);
        resume = pickSeriesDefaultVersion(bySeries, store.defaultResumeId);
      }
      if (!resume && store.defaultResumeId) {
        resume = list.find((r) => r.id === store.defaultResumeId) || null;
      }
    }
    return {
      card: {
        type: "resume",
        ref_id: id,
        title: ref.title || stripTimeCopySuffix(resume?.displayName || "") || "简历",
        subtitle:
          ref.subtitle ||
          pick(resume?.content?.basic || {}, "school", "学校") ||
          pick(resume?.content?.intent || {}, "targetJobs") ||
          "",
        variant: "resume"
      },
      message_context: formatResumeDetail(resume)
    };
  }

  throw new Error(`不支持的引用类型：${type}`);
}
