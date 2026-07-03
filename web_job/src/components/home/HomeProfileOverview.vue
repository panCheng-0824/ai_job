<script setup>
/**
 * 首页左侧「画像速览」卡片。
 */
import { computed } from "vue";
import { useRouter } from "vue-router";
import HomeAbilityRadar from "./HomeAbilityRadar.vue";
import AwardDanmakuMarquee from "./AwardDanmakuMarquee.vue";
import HoverTip from "./HoverTip.vue";
import StudentAvatar from "./StudentAvatar.vue";
import { maskName, maskOrgText, maskEducation, maskStudentField } from "../../utils/studentDesensitize";

const props = defineProps({
  studentInfo: { type: Object, default: () => ({}) },
  awardList: { type: Array, default: () => [] },
  applicationCount: { type: Number, default: 0 },
  /** 专业/学历等概要（辅助信息） */
  intentText: { type: String, default: "" },
  /** 学生维护的能力标签 */
  abilityTags: { type: Array, default: () => [] },
  /** 能力雷达五维数值 */
  radarValues: { type: Array, default: () => [72, 72, 72, 72, 72] }
});

const router = useRouter();

const name = computed(() => maskName(props.studentInfo["姓名"]) || "同学");
const major = computed(() => maskOrgText(props.studentInfo["专业名称"]) || "-");
const education = computed(() => maskEducation(props.studentInfo["学历"]) || "");
const gradYear = computed(() => props.studentInfo["毕业年度"] || "");
const subtitle = computed(() => {
  const parts = [major.value];
  if (gradYear.value) parts.push(`${gradYear.value}届`);
  if (education.value) parts.push(education.value);
  return parts.filter((x) => x && x !== "-").join(" · ");
});
const gpa = computed(() => props.studentInfo["平均绩点"] ?? "-");
const studentId = computed(() => props.studentInfo["学号"] || "");
const avatarUrl = computed(() => props.studentInfo["头像"] || "");

const intentDisplay = computed(() => {
  const text = String(props.intentText || "").trim();
  if (text && text !== "待完善求职意向") return text;
  return "暂未设置求职意向，可在学生画像中完善。";
});

const hasIntent = computed(() => {
  const text = String(props.intentText || "").trim();
  return Boolean(text && text !== "待完善求职意向");
});

const rankDisplay = computed(() => {
  if (!props.awardList.length) return "—";
  return `前${Math.min(30, 10 + props.awardList.length * 3)}%`;
});

const tagItems = computed(() => {
  const fromProfile = (props.abilityTags || []).filter(Boolean);
  if (fromProfile.length) {
    return fromProfile.slice(0, 8).map((label) => ({ label, hint: "来自能力画像标签" }));
  }
  const items = [];
  const seen = new Set();
  for (const item of props.awardList || []) {
    const label = item["项目名称"] || item["项目类别"];
    if (!label) continue;
    const text = String(label).slice(0, 12);
    if (seen.has(text)) continue;
    seen.add(text);
    items.push({ label: text, hint: "来自奖惩 / 项目记录" });
  }
  const majorTag = props.studentInfo["专业名称"];
  if (majorTag) {
    const text = maskOrgText(String(majorTag)).slice(0, 12);
    if (!seen.has(text)) items.push({ label: text, hint: "来自学籍专业信息" });
  }
  if (education.value && !seen.has(education.value)) {
    items.push({ label: education.value, hint: "来自学籍学历信息" });
  }
  if (!items.length) return [{ label: "待完善标签", hint: "完善画像后将自动生成标签", empty: true }];
  return items.slice(0, 8);
});

const radarValuesDisplay = computed(() => {
  const v = props.radarValues;
  if (Array.isArray(v) && v.length === 5) return v;
  const gpaNum = Number.parseFloat(String(gpa.value));
  const base = Number.isFinite(gpaNum) ? Math.min(95, Math.round(gpaNum * 22)) : 72;
  const awardBoost = Math.min(12, (props.awardList?.length || 0) * 3);
  return [base, 68 + awardBoost, 70 + Math.floor(awardBoost / 2), 74 + awardBoost, 66 + awardBoost];
});

function goProfile() {
  router.push({ path: "/student", query: { tab: "profile" } });
}
</script>

<template>
  <section class="profile-card">
    <header class="profile-head">
      <h2>画像速览</h2>
      <button type="button" class="edit-btn" title="编辑画像" @click="goProfile">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0 0-3L17.5 4.5a2.1 2.1 0 0 0-3 0L4 15v5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
        </svg>
      </button>
    </header>

    <div class="profile-user">
      <StudentAvatar :name="name" :student-id="studentId" :image-url="avatarUrl" size="lg" />
      <div>
        <div class="name">{{ name }}</div>
        <div class="subtitle">{{ subtitle || "完善专业与届别信息" }}</div>
      </div>
    </div>

    <section class="intent-block" aria-label="求职意向">
      <div class="intent-head">
        <h3 class="intent-title">求职意向</h3>
      </div>
      <p class="intent-query" :class="{ 'intent-query--empty': !hasIntent }">
        {{ intentDisplay }}
      </p>
    </section>

    <div class="stat-row">
      <HoverTip tip="学籍系统中的平均绩点" place="bottom" class="stat-tip">
        <div class="stat-item">
          <strong>{{ gpa }}</strong>
          <span>GPA</span>
        </div>
      </HoverTip>
      <HoverTip tip="基于奖惩与成绩的参考估算，非官方排名" place="bottom" class="stat-tip">
        <div class="stat-item">
          <strong>{{ rankDisplay }}</strong>
          <span>专业排名</span>
        </div>
      </HoverTip>
      <HoverTip tip="已记录的岗位投递次数" place="bottom" class="stat-tip">
        <div class="stat-item">
          <strong>{{ applicationCount }}</strong>
          <span>投递数</span>
        </div>
      </HoverTip>
    </div>

    <section class="award-danmaku-block" aria-label="奖惩情况">
      <div class="award-danmaku-head">
        <h3 class="tags-title">奖惩情况</h3>
        <span v-if="awardList.length" class="award-count">{{ awardList.length }} 项</span>
      </div>
      <AwardDanmakuMarquee :awards="awardList" />
    </section>

    <div class="tags-block">
      <div class="tags-title">我的标签</div>
      <div class="tags-cloud">
        <HoverTip
          v-for="(tag, index) in tagItems"
          :key="tag.label"
          :tip="tag.hint"
          place="top"
          class="tag-tip"
        >
          <span
            class="tag"
            :class="{ 'tag--empty': tag.empty }"
            :style="{ animationDelay: `${index * 45}ms` }"
          >
            {{ tag.label }}
          </span>
        </HoverTip>
      </div>
    </div>

    <div class="radar-block">
      <div class="tags-title">能力雷达图</div>
      <HomeAbilityRadar :values="radarValuesDisplay" />
    </div>
  </section>
</template>

<style scoped>
.profile-card {
  background: var(--home-card-bg, #fff);
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border);
  box-shadow: var(--home-card-shadow);
  padding: 18px 16px 14px;
  animation: card-enter 0.45s ease-out backwards;
}
.profile-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.profile-head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
}
.edit-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: #f1f5f9;
  color: #64748b;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: background 0.16s ease, color 0.16s ease, transform 0.16s ease, box-shadow 0.16s ease;
}
.edit-btn:hover {
  background: #e0e7ff;
  color: #5b6adf;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(91, 106, 223, 0.15);
}
.edit-btn:active {
  transform: translateY(0);
}
.edit-btn svg {
  width: 16px;
  height: 16px;
}
.profile-user {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  padding: 4px;
  margin-left: -4px;
  border-radius: 12px;
  transition: background 0.18s ease;
}
.profile-user:hover {
  background: #f8fafc;
}
.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(145deg, #ddd6fe, #818cf8);
  color: #312e81;
  font-size: 1.5rem;
  font-weight: 800;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(91, 106, 223, 0.2);
}
.name {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}
.subtitle {
  margin-top: 4px;
  font-size: 0.78rem;
  color: #64748b;
}
.intent-block {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e0e7ff;
  background: linear-gradient(180deg, #f8faff 0%, #fff 100%);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.intent-block:hover {
  border-color: #c7d2fe;
  box-shadow: 0 4px 14px rgba(91, 106, 223, 0.08);
}
.intent-head {
  margin-bottom: 8px;
}
.intent-title {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}
.intent-query {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: #312e81;
  line-height: 1.55;
  word-break: break-word;
}
.intent-query--empty {
  font-weight: 500;
  color: #94a3b8;
}
.intent-meta {
  margin: 8px 0 0;
  font-size: 0.72rem;
  color: #64748b;
  line-height: 1.45;
}
.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f1f5f9;
}
.stat-tip {
  display: block;
  min-width: 0;
}
.stat-item {
  text-align: center;
  padding: 8px 4px;
  background: #fafbff;
  border-radius: 10px;
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}
.stat-tip:hover .stat-item,
.stat-tip:focus-visible .stat-item {
  transform: translateY(-2px);
  background: #f1f5ff;
  box-shadow: 0 4px 12px rgba(91, 106, 223, 0.1);
}
.stat-item strong {
  display: block;
  font-size: 1.05rem;
  color: #0f172a;
  font-weight: 800;
  animation: stat-pop 0.5s cubic-bezier(0.22, 1, 0.36, 1) backwards;
  animation-delay: 0.12s;
}
.stat-item span {
  display: block;
  margin-top: 4px;
  font-size: 0.72rem;
  color: #94a3b8;
}
.award-danmaku-block {
  margin-bottom: 14px;
}
.award-danmaku-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.award-danmaku-head .tags-title {
  margin-bottom: 0;
}
.award-count {
  font-size: 0.68rem;
  font-weight: 600;
  color: #94a3b8;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  transition: background 0.16s ease, color 0.16s ease;
}
.award-danmaku-head:hover .award-count {
  background: #e0e7ff;
  color: #6366f1;
}
.tags-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
  margin-bottom: 8px;
}
.tags-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}
.tag-tip {
  display: inline-flex;
}
.tag {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #64748b;
  font-size: 0.72rem;
  transition: transform 0.16s ease, background 0.16s ease, border-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
  animation: tag-in 0.35s ease-out backwards;
}
.tag-tip:hover .tag,
.tag-tip:focus-visible .tag {
  transform: translateY(-1px);
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #4338ca;
  box-shadow: 0 3px 10px rgba(91, 106, 223, 0.12);
}
.tag--empty {
  border-style: dashed;
  color: #94a3b8;
}
.radar-block {
  padding-top: 4px;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes stat-pop {
  from {
    opacity: 0;
    transform: scale(0.88);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes tag-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .profile-card,
  .stat-item strong,
  .tag {
    animation: none;
  }

  .edit-btn,
  .profile-user,
  .intent-block,
  .stat-item,
  .tag,
  .award-count {
    transition: none;
  }
}
</style>
