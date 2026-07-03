<script setup>
import ResumeEditorHero from "./ResumeEditorHero.vue";
import ResumeSectionBlocks from "./ResumeSectionBlocks.vue";
import { sectionAllowsMultiple } from "../../modules/resume/sectionsModel";
import { getSectionField } from "../../modules/resume/templates";
import { maskStudentField } from "../../utils/studentDesensitize";

const props = defineProps({
  editorTitle: { type: String, default: "" },
  heroName: { type: String, default: "" },
  heroSubtitle: { type: String, default: "" },
  phone: { type: String, default: "" },
  email: { type: String, default: "" },
  avatarUrl: { type: String, default: "" },
  versionOpen: { type: Boolean, default: false },
  aiOpen: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  basic: { type: Object, required: true },
  intent: { type: Object, required: true },
  sections: { type: Object, required: true },
  sectionEditMode: { type: Object, required: true },
  currentTemplate: { type: Object, required: true },
  basicInfoKeys: { type: Array, default: () => [] },
  contactInfoKeys: { type: Array, default: () => [] },
  showImportIntent: { type: Boolean, default: false }
});

defineEmits([
  "change-avatar",
  "version-preview",
  "export",
  "ai-optimize",
  "toggle-edit-section",
  "update:items",
  "import-intent"
]);

function sectionField(key) {
  return getSectionField(props.currentTemplate, key);
}

function sectionEntryLabel(key) {
  if (key.includes("经历")) return "条经历";
  if (key.includes("项目") || key.includes("作品")) return "条记录";
  if (key.includes("论文") || key.includes("专利")) return "条";
  if (key.includes("竞赛") || key.includes("开源")) return "条";
  if (key.includes("获奖")) return "条";
  return "条";
}

function displayBasicValue(key) {
  const raw = props.basic[key];
  if (raw == null || String(raw).trim() === "") return "—";
  return maskStudentField(key, raw);
}
</script>

<template>
  <div class="resume-sheet">
    <div class="resume-sheet-title">{{ editorTitle }}</div>

    <ResumeEditorHero
      :name="heroName"
      :subtitle="heroSubtitle"
      :phone="phone"
      :email="email"
      :avatar-url="avatarUrl"
      :version-open="versionOpen"
      :ai-open="aiOpen"
      :saving="saving"
      @change-avatar="$emit('change-avatar', $event)"
      @version-preview="$emit('version-preview')"
      @export="(format) => $emit('export', format)"
      @ai-optimize="$emit('ai-optimize')"
    />

    <section class="resume-sheet-section">
      <div class="resume-section-head">
        <h3>基本信息</h3>
        <button type="button" class="resume-section-action" @click="$emit('toggle-edit-section', 'basic')">
          {{ sectionEditMode.basic ? "完成" : "修改" }}
        </button>
      </div>
      <div v-if="!sectionEditMode.basic" class="info-grid info-grid--body">
        <div v-for="key in basicInfoKeys" :key="key" class="info-cell">
          <span class="info-label">{{ key }}</span>
          <span class="info-value">{{ displayBasicValue(key) }}</span>
        </div>
      </div>
      <div v-else class="form-grid form-grid-basic info-grid--body">
        <label v-for="key in basicInfoKeys" :key="key" class="field">
          <span>{{ key }}</span>
          <input v-model="basic[key]" />
        </label>
      </div>
    </section>

    <section class="resume-sheet-section">
      <div class="resume-section-head">
        <h3>联系方式</h3>
        <button type="button" class="resume-section-action" @click="$emit('toggle-edit-section', 'contact')">
          {{ sectionEditMode.contact ? "完成" : "修改" }}
        </button>
      </div>
      <div v-if="!sectionEditMode.contact" class="info-grid info-grid--contact info-grid--body">
        <div v-for="key in contactInfoKeys" :key="key" class="info-cell">
          <span class="info-label">{{ key }}</span>
          <span class="info-value">{{ displayBasicValue(key) }}</span>
        </div>
      </div>
      <div v-else class="form-grid form-grid-contact info-grid--body">
        <label v-for="key in contactInfoKeys" :key="key" class="field">
          <span>{{ key }}</span>
          <input v-model="basic[key]" />
        </label>
      </div>
    </section>

    <section v-if="currentTemplate.intentMode === 'full'" class="resume-sheet-section">
      <div class="resume-section-head">
        <h3>求职意向</h3>
        <div class="resume-section-actions">
          <button v-if="showImportIntent" type="button" class="resume-section-action resume-section-action--ghost" @click="$emit('import-intent')">
            从画像导入
          </button>
          <button type="button" class="resume-section-action" @click="$emit('toggle-edit-section', 'intent')">
            {{ sectionEditMode.intent ? "完成" : "修改" }}
          </button>
        </div>
      </div>
      <div v-if="!sectionEditMode.intent" class="info-grid info-grid--intent info-grid--body">
        <div class="info-cell info-cell--wide">
          <span class="info-label">意向岗位</span>
          <span class="info-value">{{ intent.targetJobs || "—" }}</span>
        </div>
        <div class="info-cell info-cell--wide">
          <span class="info-label">意向企业</span>
          <span class="info-value">{{ intent.targetCompanies || "—" }}</span>
        </div>
      </div>
      <div v-else class="form-grid two-col info-grid--body">
        <label class="field field-wide">
          <span>意向岗位</span>
          <textarea v-model="intent.targetJobs" rows="3" placeholder="例如：前端开发、杭州、校招" />
        </label>
        <label class="field field-wide">
          <span>意向企业</span>
          <textarea v-model="intent.targetCompanies" rows="3" placeholder="例如：某行业头部、国企研究院等" />
        </label>
      </div>
    </section>

    <ResumeSectionBlocks
      v-for="key in currentTemplate.sectionKeys"
      :key="key"
      studio-mode
      :section-key="key"
      :items="sections[key] || []"
      :hint="sectionField(key).hint"
      :placeholder="sectionField(key).placeholder"
      :rows="sectionField(key).rows"
      :allow-multiple="sectionAllowsMultiple(currentTemplate, key)"
      :entry-label="sectionEntryLabel(key)"
      :accent="currentTemplate.accent"
      @update:items="$emit('update:items', key, $event)"
    />
  </div>
</template>

<style scoped>
.resume-sheet {
  background: #fff;
  border-radius: var(--home-radius-lg, 16px);
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
  flex-shrink: 0;
  overflow: hidden;
}
.resume-sheet-title {
  padding: 14px 22px 10px;
  font-size: 1rem;
  font-weight: 800;
  color: #1e293b;
  letter-spacing: 0.01em;
}
.resume-sheet-section {
  padding: 0 0 18px;
  border-top: 1px solid #eef2f6;
}
.resume-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
  padding: 10px 22px;
  background: linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #eef2f6;
}
.resume-section-head h3 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1e293b;
}
.resume-section-action {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
}
.resume-section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.resume-section-action--ghost {
  border-color: #c7d2fe;
  color: #5b6adf;
  background: #f8fafc;
}
.resume-section-action:hover {
  border-color: #c7d2fe;
  color: var(--home-primary, #5b6adf);
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px 18px;
}
.info-grid--body {
  padding: 0 22px;
}
.info-grid--contact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.info-grid--intent {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.info-cell {
  min-width: 0;
}
.info-label {
  display: block;
  font-size: 0.72rem;
  color: #94a3b8;
  margin-bottom: 4px;
}
.info-value {
  display: block;
  font-size: 0.84rem;
  color: #1e293b;
  line-height: 1.45;
  word-break: break-word;
}
.form-grid {
  display: grid;
  gap: 12px;
}
.form-grid.two-col {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.form-grid-basic {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.form-grid-contact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.field span {
  font-size: 0.76rem;
  font-weight: 600;
  color: #64748b;
}
.field input,
.field textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  font-size: 0.84rem;
  color: #1e293b;
}
.field textarea {
  resize: vertical;
  min-height: 72px;
}
.field-wide {
  grid-column: 1 / -1;
}
@media (max-width: 900px) {
  .info-grid,
  .info-grid--contact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .resume-sheet-title {
    padding: 10px 14px 8px;
  }
  .resume-section-head {
    padding: 10px 14px;
  }
  .info-grid--body {
    padding: 0 14px;
  }
}
@media (max-width: 760px) {
  .info-grid,
  .info-grid--contact,
  .info-grid--intent,
  .form-grid-basic,
  .form-grid-contact,
  .form-grid.two-col {
    grid-template-columns: 1fr;
  }
}
</style>
