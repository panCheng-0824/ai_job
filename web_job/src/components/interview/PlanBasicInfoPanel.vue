<script setup>
/**
 * 大纲详情页 — 基础信息只读展示（行业、岗位、简介、模块标签）。
 * 仅用于详情页，与编辑弹窗 PlanBasicFormSection 分离。
 */
import { computed } from "vue";
import { parseModuleTags } from "../../modules/interview/planBasicMeta";

const props = defineProps({
  detail: { type: Object, required: true }
});

const tags = computed(() => parseModuleTags(props.detail?.module_tags));

/** 行业文案拆成一级 / 二级，便于分层展示 */
const industryParts = computed(() => {
  const raw = String(props.detail?.industry_label || "").trim();
  if (!raw) return null;
  const segs = raw.split(/\s*\/\s*/).filter(Boolean);
  if (segs.length >= 2) {
    return { level1: segs[0], level2: segs.slice(1).join(" / ") };
  }
  return { single: raw };
});

const hasRole = computed(() => Boolean(String(props.detail?.target_role || "").trim()));
const hasAudience = computed(() => Boolean(String(props.detail?.suitable_audience || "").trim()));
const hasMeta = computed(() => industryParts.value || hasRole.value || hasAudience.value);
</script>

<template>
  <section class="info-panel">
    <header class="info-head">
      <h2>基础信息</h2>
      <p v-if="detail.plan_id" class="plan-id">ID {{ detail.plan_id }}</p>
    </header>

    <div v-if="hasMeta" class="meta-strip">
      <article v-if="industryParts" class="meta-item meta-industry">
        <div class="meta-icon" aria-hidden="true">行</div>
        <div class="meta-body">
          <p class="meta-label">所属行业</p>
          <p v-if="industryParts.single" class="meta-value">{{ industryParts.single }}</p>
          <p v-else class="meta-value industry-value">
            <span class="industry-l1">{{ industryParts.level1 }}</span>
            <span class="industry-sep">/</span>
            <span class="industry-l2">{{ industryParts.level2 }}</span>
          </p>
        </div>
      </article>

      <article v-if="hasRole" class="meta-item meta-role">
        <div class="meta-icon" aria-hidden="true">岗</div>
        <div class="meta-body">
          <p class="meta-label">目标岗位</p>
          <p class="meta-value">{{ detail.target_role }}</p>
        </div>
      </article>

      <article v-if="hasAudience" class="meta-item meta-audience">
        <div class="meta-icon" aria-hidden="true">人</div>
        <div class="meta-body">
          <p class="meta-label">适合人群</p>
          <p class="meta-value">{{ detail.suitable_audience }}</p>
        </div>
      </article>
    </div>

    <div v-if="detail.introduction" class="intro-box">
      <p class="intro-label">简介</p>
      <p class="intro-text">{{ detail.introduction }}</p>
    </div>

    <div v-if="tags.length" class="tags-block">
      <p class="tags-label">模块标签</p>
      <div class="tags">
        <span v-for="t in tags" :key="t" class="tag">{{ t }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.info-panel {
  background: #fff;
  border: 1px solid #eceff3;
  border-radius: 16px;
  padding: 18px 20px;
  margin-bottom: 16px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.info-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.info-head h2 {
  margin: 0;
  font-size: 1rem;
  color: #1f2937;
}

.plan-id {
  margin: 0;
  font-size: 0.72rem;
  color: #9ca3af;
  font-family: ui-monospace, monospace;
}

.meta-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid #e8ecf4;
  background: linear-gradient(180deg, #fcfdff 0%, #f8fafc 100%);
}

.meta-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 18px;
  min-width: 0;
  position: relative;
}

.meta-item:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 18px;
  bottom: 18px;
  right: 0;
  width: 1px;
  background: linear-gradient(180deg, transparent, #e2e8f0 20%, #e2e8f0 80%, transparent);
}

.meta-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.88rem;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.meta-industry .meta-icon {
  color: #4338ca;
  background: linear-gradient(145deg, #eef2ff, #e0e7ff);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.meta-role .meta-icon {
  color: #7c3aed;
  background: linear-gradient(145deg, #f5f3ff, #ede9fe);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.meta-audience .meta-icon {
  color: #0f766e;
  background: linear-gradient(145deg, #ecfdf5, #ccfbf1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.meta-body {
  min-width: 0;
  flex: 1;
}

.meta-label {
  margin: 0 0 6px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #94a3b8;
}

.meta-value {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.5;
  color: #1e293b;
  word-break: break-word;
}

.industry-value {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px;
  font-weight: 500;
}

.industry-l1 {
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 500;
}

.industry-sep {
  color: #cbd5e1;
  font-weight: 400;
  user-select: none;
}

.industry-l2 {
  color: #1e293b;
  font-weight: 700;
  font-size: 0.98rem;
}

.intro-box {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #fafbff 0%, #f8fafc 100%);
  border: 1px solid #e8ecff;
}

.intro-label,
.tags-label {
  margin: 0 0 8px;
  font-size: 0.72rem;
  font-weight: 700;
  color: #6b7280;
}

.intro-text {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.65;
  color: #4b5563;
  white-space: pre-wrap;
  word-break: break-word;
}

.tags-block {
  margin-top: 14px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 5px 11px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
}

@media (max-width: 768px) {
  .meta-strip {
    grid-template-columns: 1fr;
  }

  .meta-item:not(:last-child)::after {
    top: auto;
    bottom: 0;
    left: 18px;
    right: 18px;
    width: auto;
    height: 1px;
    background: #eef2f7;
  }
}

@media (min-width: 769px) and (max-width: 900px) {
  .meta-strip {
    grid-template-columns: 1fr 1fr;
  }

  .meta-industry {
    grid-column: 1 / -1;
  }

  .meta-industry::after {
    display: none;
  }

  .meta-industry {
    border-bottom: 1px solid #eef2f7;
  }
}
</style>
