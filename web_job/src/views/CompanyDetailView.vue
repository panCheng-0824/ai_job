<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { apiDelete, apiGet, apiPost, getStudentId } from "../api/client";
import { resolveDictLabel } from "../utils/dictLabel";
import { fmtRegisteredCapital } from "../utils/formatCompany";
import { sanitizeRichHtml } from "../utils/richText";

const route = useRoute();
const company = ref(null);
/** 单位性质展示文案（后端未翻译时前端按 job_dwxz 字典兜底） */
const companyTypeLabel = ref("-");
const jobs = ref([]);
const error = ref("");

const coTagDefs = ref([]);
const coTagLabelMap = computed(() => {
  const m = {};
  (coTagDefs.value || []).forEach((t) => {
    if (t?.id) m[t.id] = t.label || t.id;
  });
  return m;
});

const ctx = ref(null);
const reviewStars = ref(5);
const reviewComment = ref("");
const selectedTagIds = ref([]);
const reviewHint = ref("");
const publicReviews = ref(null);

const normalizedJobs = computed(() =>
  (jobs.value || []).map((item) => ({
    job_id: item.id,
    job_title: item.jobName,
    city: item.address,
    district: item.area,
    salary_range_month: item.salaryRange,
    salary_months: "-",
    company_relation: {
      company_name: item.companyName,
      credit_code: item.companyId
    }
  }))
);

const creditCode = computed(() => String(route.params.credit_code || "").trim());

/** 空值统一展示为「-」 */
function fmt(v) {
  if (v === null || v === undefined) return "-";
  const s = String(v).trim();
  return s || "-";
}

/** 公司主页等外链：补全协议供 <a href> 使用 */
function normalizeExternalUrl(raw) {
  const s = String(raw || "").trim();
  if (!s) return "";
  if (/^https?:\/\//i.test(s)) return s;
  return `https://${s}`;
}

const kvRows = computed(() => {
  const c = company.value;
  if (!c) return [];
  return [
    ["企业名称", fmt(c.companyName || c.gsmc)],
    ["行业类型", fmt(c.area)],
    ["企业规模", fmt(c.companySize)],
    ["单位性质", fmt(companyTypeLabel.value)],
    ["办公地址", fmt(c.address)],
    ["办公地区", fmt(c.region)]
  ];
});

/** 折叠区块摘要：取前几条非空字段值 */
function fieldPreviewValue(field) {
  const v = String(field?.value ?? "").trim();
  return v && v !== "-" ? v : "";
}

function sectionPreview(fields, max = 2) {
  const parts = (fields || [])
    .map((f) => fieldPreviewValue(f))
    .filter(Boolean)
    .slice(0, max);
  return parts.length ? parts.join(" · ") : "点击展开查看";
}

const detailSections = computed(() => {
  const c = company.value || {};
  return [
    {
      title: "工商与规模",
      fields: [
        { label: "企业ID", value: fmt(c.id || c.wid) },
        { label: "机构类型", value: fmt(c.jglx) },
        { label: "组织机构代码", value: fmt(c.zzjgdm) },
        { label: "单位性质", value: fmt(companyTypeLabel.value) },
        { label: "单位类型", value: fmt(c.dwlx) },
        { label: "公司规模", value: fmt(c.companySize) },
        { label: "注册资金（万元）", value: fmtRegisteredCapital(c.zczj) },
        { label: "成立时间", value: fmt(c.clsj) },
        {
          label: "公司主页",
          value: fmt(c.gszy),
          href: c.gszy ? normalizeExternalUrl(c.gszy) : ""
        }
      ]
    },
    {
      title: "地址与联系",
      fields: [
        { label: "办公地址", value: fmt(c.address) },
        { label: "办公地区", value: fmt(c.region) },
        { label: "注册地址", value: fmt(c.dwzcdz) },
        { label: "单位邮箱", value: fmt(c.website) },
        { label: "联系人", value: fmt(c.lxr) },
        { label: "联系人职位", value: fmt(c.lxrzw) },
        { label: "联系人电话", value: fmt(c.lxrdh) },
        { label: "联系人手机", value: fmt(c.lxrsjh) },
        { label: "联系人邮箱", value: fmt(c.lxrdzyj) }
      ]
    }
  ];
});

/** 单位简介富文本（dwjj） */
const companyIntroHtml = computed(() => sanitizeRichHtml(company.value?.dwjj || ""));

const companyDetailPreview = ref(null);
const companyPreviewJson = computed(() =>
  companyDetailPreview.value ? JSON.stringify(companyDetailPreview.value, null, 2) : ""
);
const companyPreviewHint = computed(() => {
  const p = companyDetailPreview.value;
  const name = p?.companyName || company.value?.companyName;
  const jobCount = p?.关联岗位数 ?? p?.RAG打包预览?.关联岗位总数 ?? normalizedJobs.value?.length ?? 0;
  return name ? `${name} · ${jobCount} 岗打包` : "RAG 打包预览";
});

const loggedIn = computed(() => Boolean(getStudentId()));
const companyFollowed = computed(() => Boolean(ctx.value?.company_followed));
const hasMyReview = computed(() => Boolean(ctx.value?.my_company_review));

/** 已登录且本人尚未评价企业时展示「未评价」小标签 */
const showCompanyTipNoReview = computed(() => Boolean(company.value) && loggedIn.value && !hasMyReview.value);

const portraitLine = computed(() => {
  const j = publicReviews.value;
  if (!j || j.detail) return "";
  const fc = j.follower_count != null ? j.follower_count : 0;
  const dist = j.review_tag_distribution || [];
  const distStr = dist.length
    ? dist.map((x) => `${coTagLabelMap.value[x.tag_id] || x.tag_id} ${x.count} 次`).join("；")
    : "（尚无从评价汇总的标签次数，提交带标签的评价后此处会累计）";
  return `画像统计 · 关注人数：${fc}（全站学生）\n评价标签分布：${distStr}`;
});

const aggCoText = computed(() => {
  const j = publicReviews.value;
  if (!j) return "加载中…";
  if (j.detail) return j.detail;
  const fc = j.follower_count != null ? j.follower_count : 0;
  if (!j.count) return `暂时还没有评价。全站关注该企业：${fc} 人。`;
  const dist = (j.review_tag_distribution || [])
    .map((x) => `${coTagLabelMap.value[x.tag_id] || x.tag_id} ${x.count} 次`)
    .join("；");
  return (
    `共 ${j.count} 条评价，平均 ${j.avg_stars} 星 · 全站关注 ${fc} 人` + (dist ? ` · 标签分布：${dist}` : "")
  );
});

async function loadCoTagCatalog() {
  try {
    const c = await apiGet("/api/review-tags");
    coTagDefs.value = c.company_review_tags || [];
  } catch {
    coTagDefs.value = [];
  }
}

async function refreshCoContext() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) {
    ctx.value = null;
    return;
  }
  try {
    const q = new URLSearchParams({ student_id: sid, credit_code: cc });
    ctx.value = await apiGet(`/api/me/context?${q}`);
    const mr = ctx.value?.my_company_review;
    if (mr) {
      reviewStars.value = Math.min(5, Math.max(1, Number(mr.stars) || 5));
      reviewComment.value = mr.comment || "";
      selectedTagIds.value = [...(mr.tags || [])];
    } else {
      reviewStars.value = 5;
      reviewComment.value = "";
      selectedTagIds.value = [];
    }
  } catch {
    ctx.value = null;
  }
}

async function loadPublicCoReviews() {
  const cc = creditCode.value;
  if (!cc) return;
  try {
    publicReviews.value = await apiGet(`/api/companies/${encodeURIComponent(cc)}/reviews`);
  } catch (e) {
    publicReviews.value = { count: 0, items: [], detail: e.message };
  }
}

async function loadCompanyJobs(yrdw, limit = 12) {
  const code = String(yrdw || "").trim();
  if (!code) {
    jobs.value = [];
    return;
  }
  const params = new URLSearchParams({ yrdw: code, limit: String(limit) });
  try {
    jobs.value = await apiGet(`/api/jobs/by-company?${params}`);
  } catch {
    jobs.value = [];
  }
}

async function loadCompanyDetailPreview() {
  const cc = creditCode.value;
  if (!cc) {
    companyDetailPreview.value = null;
    return;
  }
  try {
    companyDetailPreview.value = await apiGet(
      `/api/companies/${encodeURIComponent(cc)}/detail-preview`
    );
  } catch {
    companyDetailPreview.value = null;
  }
}

async function loadCompany() {
  try {
    error.value = "";
    reviewHint.value = "";
    const cc = creditCode.value;
    const one = await apiGet(`/api/companies/${encodeURIComponent(cc)}`);
    company.value = one;
    companyTypeLabel.value = await resolveDictLabel("job_dwxz", one?.companyType);
    await loadCompanyJobs(one?.zzjgdm || one?.id, 12);

    await loadCoTagCatalog();
    if (getStudentId()) await refreshCoContext();
    else {
      ctx.value = null;
      reviewStars.value = 5;
      reviewComment.value = "";
      selectedTagIds.value = [];
    }
    await loadPublicCoReviews();
    await loadCompanyDetailPreview();
  } catch (err) {
    error.value = err.message || "加载失败";
    company.value = null;
    companyTypeLabel.value = "-";
    companyDetailPreview.value = null;
  }
}

async function toggleFollow() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) {
    window.alert("请先登录");
    return;
  }
  try {
    await apiPost("/api/me/follows/toggle", { student_id: sid, credit_code: cc });
    await refreshCoContext();
    await loadPublicCoReviews();
  } catch (e) {
    window.alert(e.message || "操作失败");
  }
}

async function submitCompanyReview() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) {
    window.alert("请先登录");
    return;
  }
  try {
    await apiPost("/api/me/reviews/company", {
      student_id: sid,
      credit_code: cc,
      stars: Number(reviewStars.value),
      comment: reviewComment.value.trim(),
      tags: [...selectedTagIds.value]
    });
    reviewHint.value = "已保存评价。";
    await loadPublicCoReviews();
    await refreshCoContext();
  } catch (e) {
    window.alert(e.message || "提交失败");
  }
}

async function deleteCompanyReview() {
  const sid = getStudentId();
  const cc = creditCode.value;
  if (!sid || !cc) return;
  if (!window.confirm("确定删除你对该企业的评价？（可稍后重新提交）")) return;
  try {
    const q = new URLSearchParams({ student_id: sid, credit_code: cc });
    const j = await apiDelete(`/api/me/reviews/company?${q}`);
    reviewHint.value = j.deleted ? "已删除评价。" : "当前没有可删除的评价。";
    await refreshCoContext();
    await loadPublicCoReviews();
  } catch (e) {
    window.alert(e.message || "删除失败");
  }
}

onMounted(loadCompany);

watch(
  () => route.params.credit_code,
  (newVal, oldVal) => {
    if (newVal && newVal !== oldVal) {
      loadCompany();
    }
  }
);
</script>

<template>
  <div>
    <section class="hero">

      <h1>{{ company?.companyName || company?.gsmc || "加载中..." }}</h1>
      <p>企业ID（WID）：<code>{{ route.params.credit_code }}</code></p>
      <div v-if="showCompanyTipNoReview" class="hero-tip-row" aria-label="状态提示">
        <span class="tip-chip tip-chip--muted">未评价</span>
      </div>
      <p v-if="portraitLine" class="portrait muted">{{ portraitLine }}</p>
    </section>
    <div class="layout">
      <main class="panel">
        <div class="kv">
          <template v-for="([k, v], idx) in kvRows" :key="`${k}-${idx}`">
            <div class="k">{{ k }}</div>
            <div class="v">{{ v }}</div>
          </template>
        </div>
        <div v-if="loggedIn" class="btn-row">
          <button type="button" class="btn secondary" @click="toggleFollow">
            {{ companyFollowed ? "已关注（点击取消）" : "关注企业" }}
          </button>
          <router-link class="btn primary" to="/me">我的关注</router-link>
        </div>
        <p v-else class="muted">登录后可关注与评价企业。</p>
        <p v-if="loggedIn" class="muted fol-hint">
          {{ companyFollowed ? "该企业已在你的关注列表中。" : "关注后可在「我的」中快速回访。" }}
        </p>
        <details v-for="section in detailSections" :key="section.title" class="info-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">{{ section.title }}</span>
            <span class="info-fold-hint muted">{{ sectionPreview(section.fields) }}</span>
          </summary>
          <div class="info-fold-body">
            <div class="kv">
              <template v-for="field in section.fields" :key="`${section.title}-${field.label}`">
                <div class="k">{{ field.label }}</div>
                <div class="v">
                  <a
                    v-if="field.href"
                    :href="field.href"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="external-link"
                  >{{ field.value }}</a>
                  <template v-else>{{ field.value || "-" }}</template>
                </div>
              </template>
            </div>
          </div>
        </details>
        <details class="review-fold">
          <summary class="review-fold-summary">评价与口碑（点击展开）</summary>
          <div class="review-fold-body">
        <div class="review-box">
          <label>评价本企业（1～5 星）</label>
          <select v-model.number="reviewStars" class="review-input">
            <option :value="5">5 星</option>
            <option :value="4">4 星</option>
            <option :value="3">3 星</option>
            <option :value="2">2 星</option>
            <option :value="1">1 星</option>
          </select>
          <textarea v-model="reviewComment" class="review-input" rows="3" placeholder="可选：写几句评价" />
          <label class="tag-label">标签（可选，来自 config/review_tags.json）</label>
          <div class="tag-chips">
            <label v-for="t in coTagDefs" :key="t.id" class="chip-label">
              <input v-model="selectedTagIds" type="checkbox" :value="t.id" />
              {{ t.label || t.id }}
            </label>
          </div>
          <div class="btn-row tight">
            <button type="button" class="btn primary" :disabled="!loggedIn" @click="submitCompanyReview">
              提交 / 更新评价
            </button>
            <button
              v-if="hasMyReview"
              type="button"
              class="btn danger"
              :disabled="!loggedIn"
              @click="deleteCompanyReview"
            >
              删除我的评价
            </button>
          </div>
          <p class="muted">{{ reviewHint }}</p>
        </div>
        <h3 class="section-title">大家怎么说</h3>
        <p class="muted">{{ aggCoText }}</p>
        <ul class="list">
          <li v-for="(it, i) in publicReviews?.items || []" :key="`${it.student_id}-${i}`">
            <strong>{{ it.student_id }}</strong>
            · {{ "★".repeat(it.stars) }}{{ "☆".repeat(5 - it.stars) }}
            <div class="rev-comment">{{ it.comment || "（无评语）" }}</div>
            <div v-if="it.tags?.length" class="rev-tags">
              标签：{{ it.tags.map((id) => coTagLabelMap[id] || id).join("、") }}
            </div>
          </li>
        </ul>
          </div>
        </details>
        <details class="info-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">单位简介</span>
            <span class="info-fold-hint muted">{{ companyIntroHtml ? "点击展开查看" : "暂无单位简介" }}</span>
          </summary>
          <div class="info-fold-body">
            <div
              v-if="companyIntroHtml"
              class="rich-text-block"
              v-html="companyIntroHtml"
            />
            <p v-else class="muted">暂无单位简介</p>
          </div>
        </details>
        <details class="info-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">该企业发布的岗位</span>
            <span class="info-fold-hint muted">{{ normalizedJobs.length ? `${normalizedJobs.length} 个` : "暂无" }}</span>
          </summary>
          <div id="company-jobs" class="info-fold-body">
            <ul class="list">
              <li v-if="!normalizedJobs.length">暂无该企业岗位数据</li>
              <li v-for="item in normalizedJobs" :key="item.job_id">
                <router-link :to="`/jobs/${encodeURIComponent(item.job_id)}`">{{ item.job_title || "-" }}</router-link>
                <div class="post-meta">行业：{{ item.district || "-" }}</div>
                <div class="post-meta">薪资：{{ item.salary_range_month || "-" }}</div>
                <div class="post-meta">地址：{{ item.city || "-" }}</div>
              </li>
            </ul>
          </div>
        </details>
        <details v-if="companyPreviewJson" class="info-fold rag-debug-fold">
          <summary class="info-fold-summary">
            <span class="info-fold-title">RAG 打包预览（字典翻译）</span>
            <span class="info-fold-hint muted">{{ companyPreviewHint }} · 点击展开</span>
          </summary>
          <div class="info-fold-body">
            <p class="rag-debug-tip muted">
              「展示数据」为企业全量字段（字典已翻译为中文）；「RAG打包预览」为一岗一文档策略下嵌入岗位的企业区块，以及各关联岗位的完整打包 JSON（含 markdown 正文）。
            </p>
            <pre class="rag-debug-pre">{{ companyPreviewJson }}</pre>
          </div>
        </details>
        <p class="error">{{ error }}</p>
      </main>
    </div>
  </div>
</template>

<style scoped>
.hero {
  max-width: 1100px;
  margin: 0 auto;
  padding: 42px 20px 16px;
}
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: #e0e7ff;
  color: var(--primary-color);
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 10px;
}
.hero h1 {
  font-size: clamp(1.9rem, 4.4vw, 2.8rem);
  margin-bottom: 8px;
}
.hero p {
  color: var(--text-muted);
  font-size: 0.95rem;
}
.hero-tip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
}
.tip-chip {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
}
.tip-chip--muted {
  background: #f1f5f9;
  color: #475569;
  border-color: #cbd5e1;
}
.review-fold {
  margin-top: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 0 12px 12px;
  background: #fafafa;
}
.review-fold-summary {
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--primary-color);
  padding: 12px 0 10px;
  list-style: none;
}
.review-fold-summary::-webkit-details-marker {
  display: none;
}
.review-fold-body {
  padding-top: 4px;
}
.info-fold {
  margin-top: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 0 12px 12px;
  background: #fafafa;
}
.info-fold-summary {
  cursor: pointer;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px 12px;
  padding: 12px 0 10px;
  list-style: none;
  user-select: none;
}
.info-fold-summary::-webkit-details-marker {
  display: none;
}
.info-fold-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--primary-color);
}
.info-fold-title::before {
  content: "▸ ";
  display: inline-block;
  transition: transform 0.15s ease;
  color: #94a3b8;
}
.info-fold[open] .info-fold-title::before {
  transform: rotate(90deg);
}
.info-fold-hint {
  font-size: 0.82rem;
  font-weight: 400;
  text-align: right;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.info-fold-body {
  padding-top: 2px;
  border-top: 1px solid #eceff3;
}
.rag-debug-tip {
  margin: 0 0 10px;
  font-size: 0.82rem;
}
.rag-debug-pre {
  margin: 0;
  border-radius: 10px;
  background: #0f172a;
  color: #f8fafc;
  padding: 12px;
  max-height: 48vh;
  overflow: auto;
  font-size: 0.78rem;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}
.portrait {
  margin-top: 10px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.layout {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px 70px;
}
.kv {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 8px 12px;
  font-size: 0.92rem;
}
.k {
  color: var(--text-muted);
}
.external-link {
  color: var(--primary-color);
  text-decoration: none;
  word-break: break-all;
}
.external-link:hover {
  text-decoration: underline;
}
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
  align-items: center;
}
.btn-row.tight {
  margin-top: 0;
}
.muted {
  color: var(--text-muted);
  font-size: 0.88rem;
}
.fol-hint {
  margin-top: 0;
  margin-bottom: 8px;
}
.review-box {
  margin-top: 12px;
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 12px;
}
.review-box label {
  font-size: 0.85rem;
  color: var(--text-muted);
  display: block;
  margin-bottom: 6px;
}
.tag-label {
  margin-top: 8px;
}
.review-input {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  padding: 8px;
  font-size: 0.9rem;
  margin-bottom: 8px;
}
.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin: 8px 0 12px;
}
.chip-label {
  font-size: 0.85rem;
  cursor: pointer;
  user-select: none;
}
.section-title {
  margin: 18px 0 10px;
  font-size: 1.05rem;
}
.list {
  list-style: none;
  display: grid;
  gap: 10px;
  padding: 0;
}
.list li {
  border: 1px solid #eceff3;
  border-radius: 12px;
  padding: 10px;
}
.list a {
  text-decoration: none;
  color: var(--primary-color);
  font-weight: 600;
}
.post-meta {
  font-size: 0.86rem;
  color: var(--text-muted);
  margin-top: 4px;
}
.rev-comment {
  margin-top: 6px;
  color: #6b7280;
  font-size: 0.88rem;
  white-space: pre-wrap;
}
.rev-tags {
  margin-top: 6px;
  font-size: 0.82rem;
  color: #4b5563;
}
.error {
  color: var(--danger);
  margin-top: 8px;
  min-height: 20px;
  font-size: 0.9rem;
  font-weight: 600;
}
.rich-text-block {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  background: #ffffff;
  color: #1f2937;
  font-size: 0.92rem;
  line-height: 1.8;
  word-break: break-word;
  max-height: 360px;
  overflow: auto;
}
.rich-text-block :deep(p) {
  margin: 0 0 0.75em;
}
.rich-text-block :deep(ul),
.rich-text-block :deep(ol) {
  margin: 0 0 0.75em;
  padding-left: 1.25em;
}
.rich-text-block :deep(img) {
  max-width: 100%;
  height: auto;
}
@media (max-width: 900px) {
  .kv {
    grid-template-columns: 1fr;
  }
}
</style>
