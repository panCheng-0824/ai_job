<script setup>
/**
 * 学生画像详情页：对齐设计稿三栏布局（主内容 + 右侧数据栏）。
 */
import { computed, ref } from "vue";
import ProfileAbilityForm from "../profile/ProfileAbilityForm.vue";
import ProfileContactForm from "../profile/ProfileContactForm.vue";
import ProfileEditDrawer from "../profile/ProfileEditDrawer.vue";
import ProfileJobIntentForm from "../profile/ProfileJobIntentForm.vue";
import HomeAbilityRadar from "./HomeAbilityRadar.vue";
import HomeProfileRightRail from "./HomeProfileRightRail.vue";
import StudentAvatar from "./StudentAvatar.vue";
import { maskFieldRows, maskName, maskOrgText, maskEducation, maskStudentField } from "../../utils/studentDesensitize";

const props = defineProps({
  studentInfo: { type: Object, default: () => ({}) },
  baseFields: { type: Array, default: () => [] },
  awardInfoList: { type: Array, default: () => [] },
  jobIntent: { type: Object, default: () => ({}) },
  abilityTags: { type: Array, default: () => [] },
  suggestedTags: { type: Array, default: () => [] },
  radarValues: { type: Array, default: () => [72, 72, 72, 72, 72] },
  intentText: { type: String, default: "" },
  contactForm: { type: Object, default: () => ({}) },
  jobIntentForm: { type: Object, default: () => ({}) },
  abilityForm: { type: Object, default: () => ({}) },
  saving: { type: Boolean, default: false },
  avatarUploadHandler: { type: Function, default: null },
  summary: { type: Object, default: null },
  favorites: { type: Array, default: () => [] },
  recentJobs: { type: Array, default: () => [] },
  error: { type: String, default: "" }
});

const emit = defineEmits([
  "copy-json",
  "view-job",
  "view-more",
  "save-contact",
  "save-job-intent",
  "save-ability"
]);

const contactDrawerOpen = ref(false);
const intentDrawerOpen = ref(false);
const abilityTagsDrawerOpen = ref(false);
const abilityRadarDrawerOpen = ref(false);

const contactFormRef = ref(null);
const intentFormRef = ref(null);
const abilityTagsFormRef = ref(null);
const abilityRadarFormRef = ref(null);

const name = computed(() => maskName(props.studentInfo["姓名"]) || "同学");
const rawStudentId = computed(() => props.studentInfo["学号"] || "");
const displayStudentId = computed(() => maskStudentField("学号", rawStudentId.value) || "");
const avatarUrl = computed(() => props.studentInfo["头像"] || "");
const displayPhone = computed(() => maskStudentField("手机", props.studentInfo["手机"]));
const displayEmail = computed(() => maskStudentField("邮箱", props.studentInfo["邮箱"]));

const schoolLine = computed(() => {
  const s = props.studentInfo;
  return [
    maskStudentField("学校名称", s["学校名称"]),
    maskStudentField("院系名称", s["院系名称"]),
    maskStudentField("专业名称", s["专业名称"]),
    s["毕业年度"]
      ? `${s["毕业年度"]}届${maskEducation(s["学历"]) || ""}`
      : maskEducation(s["学历"])
  ]
    .filter(Boolean)
    .join(" | ");
});

const basicGrid = computed(() => {
  const pick = [
    "学号", "性别", "民族", "出生日期", "证件号", "学校名称", "专业名称", "平均绩点",
    "毕业年度", "学历", "院系名称", "班级名称", "体测成绩", "手机", "邮箱"
  ];
  return maskFieldRows(props.baseFields.filter((f) => pick.includes(f.label)));
});

const roleText = computed(() => {
  const roles = props.jobIntent["意向岗位"];
  if (Array.isArray(roles) && roles.length) return roles.join("、");
  return maskOrgText(props.studentInfo["专业名称"]) || "待设置";
});

const cityText = computed(() => {
  const cities = props.jobIntent["意向城市"];
  if (Array.isArray(cities) && cities.length) return cities.join("、");
  return "不限";
});

const salaryText = computed(() => props.jobIntent["期望薪资"] || "面议");

const queryText = computed(() => props.jobIntent["综合诉求"] || props.intentText || "待完善求职意向");

const campusText = computed(() => {
  const extra = props.studentInfo["校园经历补充"];
  if (extra) return extra;
  const n = props.awardInfoList?.length || 0;
  return n ? `共 ${n} 项官方奖惩/项目记录（可在「修改」中补充描述）` : "暂无校园经历，可点击修改补充";
});

const awardsSummary = computed(() => {
  const list = props.awardInfoList || [];
  if (!list.length) return "暂无奖惩记录";
  return list
    .slice(0, 4)
    .map((a) => `${a["奖项年度"] || ""} ${a["项目名称"] || a["项目类别"] || ""}`.trim())
    .filter(Boolean)
    .join("；");
});

const preferenceText = computed(() => {
  if (props.intentText) {
    return `根据你的画像，偏好${props.intentText}方向岗位，建议优先关注匹配度≥85%的推荐结果，并结合城市与薪资区间筛选。`;
  }
  return "";
});

function openContactEdit() {
  contactDrawerOpen.value = true;
}
function openIntentEdit() {
  intentDrawerOpen.value = true;
}
function openAbilityEdit() {
  abilityTagsDrawerOpen.value = true;
}
function openRadarEdit() {
  abilityRadarDrawerOpen.value = true;
}

function submitContact() {
  const payload = contactFormRef.value?.getPayload?.();
  if (payload) emit("save-contact", payload);
}
function submitIntent() {
  const payload = intentFormRef.value?.getPayload?.();
  if (payload) emit("save-job-intent", payload);
}
function submitAbility() {
  const payload = abilityTagsFormRef.value?.getPayload?.();
  if (payload) emit("save-ability", payload);
}
function submitRadar() {
  const payload = abilityRadarFormRef.value?.getPayload?.();
  if (payload) emit("save-ability", payload);
}

defineExpose({
  closeDrawersOnSaved() {
    contactDrawerOpen.value = false;
    intentDrawerOpen.value = false;
    abilityTagsDrawerOpen.value = false;
    abilityRadarDrawerOpen.value = false;
  }
});
</script>

<template>
  <div class="profile-page">
    <p v-if="error" class="error">{{ error }}</p>

    <div class="profile-layout">
      <div class="profile-main">
        <section class="hero-card">
          <div class="hero-left">
            <StudentAvatar
              :name="name"
              :student-id="rawStudentId"
              :image-url="avatarUrl"
              size="xl"
              editable
              :upload-handler="avatarUploadHandler"
              title="点击上传头像"
            />
            <div>
              <h1>{{ name }}</h1>
              <p class="school-line">{{ schoolLine || "完善学校与专业信息" }}</p>
              <p class="contact-line">
                <span>学号 {{ displayStudentId || "-" }}</span>
                <span v-if="studentInfo['手机']">手机 {{ displayPhone }}</span>
                <span v-if="studentInfo['邮箱']">邮箱 {{ displayEmail }}</span>
              </p>
            </div>
          </div>
          <div class="hero-actions">
            <button type="button" class="btn-primary" @click="emit('copy-json')">导出画像报告</button>
          </div>
        </section>

        <section class="content-card">
          <header class="card-head">
            <h2>基础学生档案</h2>
            <button type="button" class="edit-link" @click="openContactEdit">修改</button>
          </header>
          <p class="readonly-hint">带 🔒 的字段来自学籍系统，不可修改</p>
          <div class="info-grid">
            <div v-for="item in basicGrid" :key="item.label" class="info-cell">
              <span class="label">
                {{ item.label }}
                <span v-if="!['手机', '邮箱'].includes(item.label)" class="lock" title="学籍只读">🔒</span>
              </span>
              <span class="value">{{ item.value ?? "-" }}</span>
            </div>
          </div>
          <div class="award-block">
            <div class="award-col">
              <strong>奖惩情况 <span class="lock" title="官方数据">🔒</span></strong>
              <p>{{ awardsSummary }}</p>
            </div>
            <div class="award-col">
              <strong>校园经历</strong>
              <p>{{ campusText }}</p>
            </div>
          </div>
        </section>

        <section class="content-card intent-card">
          <header class="card-head">
            <h2>求职意向</h2>
            <button type="button" class="edit-link" @click="openIntentEdit">修改</button>
          </header>
          <div class="intent-grid">
            <div class="intent-cell">
              <span>意向岗位</span>
              <strong>{{ roleText }}</strong>
            </div>
            <div class="intent-cell">
              <span>期望薪资</span>
              <strong>{{ salaryText }}</strong>
            </div>
            <div class="intent-cell">
              <span>意向城市</span>
              <strong>{{ cityText }}</strong>
            </div>
            <div class="intent-cell intent-cell--wide">
              <span>综合诉求</span>
              <strong>{{ queryText }}</strong>
            </div>
          </div>
        </section>

        <div class="dual-row">
          <section class="content-card">
            <header class="card-head">
              <h2>能力标签</h2>
              <button type="button" class="edit-link" @click="openAbilityEdit">编辑</button>
            </header>
            <div class="tag-list">
              <span v-for="tag in abilityTags" :key="tag" class="skill-tag">{{ tag }}</span>
              <span v-if="!abilityTags.length" class="skill-tag skill-tag--empty">待添加</span>
            </div>
          </section>
          <section class="content-card">
            <header class="card-head">
              <h2>能力雷达图</h2>
              <button type="button" class="edit-link" @click="openRadarEdit">调整</button>
            </header>
            <HomeAbilityRadar :values="radarValues" />
          </section>
        </div>
      </div>

      <HomeProfileRightRail
        :summary="summary"
        :favorites="favorites"
        :recent-jobs="recentJobs"
        :preference-text="preferenceText"
        @view-job="emit('view-job', $event)"
        @view-more="emit('view-more')"
      />
    </div>

    <ProfileEditDrawer
      :open="contactDrawerOpen"
      title="编辑联系方式与经历"
      subtitle="修改手机、邮箱与校园经历补充，学籍字段保持只读"
      :saving="saving"
      @close="contactDrawerOpen = false"
      @save="submitContact"
    >
      <ProfileContactForm ref="contactFormRef" :model-value="contactForm" :avatar-url="avatarUrl" />
    </ProfileEditDrawer>

    <ProfileEditDrawer
      :open="intentDrawerOpen"
      title="编辑求职意向"
      subtitle="设置目标岗位、城市、薪资与综合诉求"
      :saving="saving"
      @close="intentDrawerOpen = false"
      @save="submitIntent"
    >
      <ProfileJobIntentForm ref="intentFormRef" :model-value="jobIntentForm" />
    </ProfileEditDrawer>

    <ProfileEditDrawer
      :open="abilityTagsDrawerOpen"
      title="编辑能力标签"
      subtitle="完善技能标签，提升岗位匹配准确度"
      :saving="saving"
      @close="abilityTagsDrawerOpen = false"
      @save="submitAbility"
    >
      <ProfileAbilityForm
        ref="abilityTagsFormRef"
        :model-value="abilityForm"
        :suggested-tags="suggestedTags"
        section="tags"
      />
    </ProfileEditDrawer>

    <ProfileEditDrawer
      :open="abilityRadarDrawerOpen"
      title="调整能力雷达图"
      subtitle="按 0-100 调整五维能力自评"
      :saving="saving"
      @close="abilityRadarDrawerOpen = false"
      @save="submitRadar"
    >
      <ProfileAbilityForm
        ref="abilityRadarFormRef"
        :model-value="abilityForm"
        :suggested-tags="suggestedTags"
        section="radar"
      />
    </ProfileEditDrawer>
  </div>
</template>

<style scoped>
.profile-page {
  width: 100%;
}
.profile-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 280px);
  gap: 16px;
  align-items: start;
}
.profile-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}
.hero-card,
.content-card {
  background: var(--home-card-bg, #fff);
  border: 1px solid var(--home-card-border);
  border-radius: var(--home-radius-lg, 16px);
  box-shadow: var(--home-card-shadow);
  padding: 18px 20px;
}
.hero-card {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.hero-left {
  display: flex;
  gap: 16px;
  align-items: center;
  min-width: 0;
}
.hero-left h1 {
  margin: 0 0 6px;
  font-size: 1.25rem;
  font-weight: 800;
  color: #0f172a;
}
.school-line {
  margin: 0 0 8px;
  font-size: 0.82rem;
  color: #64748b;
  line-height: 1.5;
}
.contact-line {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 0.76rem;
  color: #94a3b8;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.btn-primary {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: var(--home-primary, #5b6adf);
  color: #fff;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.card-head h2 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
}
.edit-link {
  font-size: 0.78rem;
  color: var(--home-primary, #5b6adf);
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: none;
  padding: 0;
}
.readonly-hint {
  margin: -6px 0 12px;
  font-size: 0.72rem;
  color: #94a3b8;
}
.lock {
  font-size: 0.65rem;
  opacity: 0.7;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 16px;
  margin-bottom: 14px;
}
.info-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-cell .label {
  font-size: 0.72rem;
  color: #94a3b8;
}
.info-cell .value {
  font-size: 0.84rem;
  color: #1e293b;
  font-weight: 500;
}
.award-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid #f1f5f9;
}
.award-col strong {
  display: block;
  font-size: 0.78rem;
  color: #475569;
  margin-bottom: 6px;
}
.award-col p {
  margin: 0;
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.55;
}
.intent-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.intent-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 10px;
}
.intent-cell--wide {
  grid-column: 1 / -1;
}
.intent-cell span {
  font-size: 0.72rem;
  color: #94a3b8;
}
.intent-cell strong {
  font-size: 0.84rem;
  color: #1e293b;
  font-weight: 600;
  word-break: break-word;
}
.dual-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.skill-tag {
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid #c7d2fe;
  background: #f8fafc;
  color: #4338ca;
  font-size: 0.76rem;
  font-weight: 500;
}
.skill-tag--empty {
  border-style: dashed;
  color: #94a3b8;
}
.error {
  color: var(--danger);
  font-size: 0.88rem;
  font-weight: 600;
  margin: 0 0 12px;
}
@media (max-width: 1200px) {
  .profile-layout {
    grid-template-columns: 1fr;
  }
  .dual-row {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 768px) {
  .info-grid,
  .intent-grid,
  .award-block {
    grid-template-columns: 1fr;
  }
  .hero-card {
    flex-direction: column;
  }
}
</style>