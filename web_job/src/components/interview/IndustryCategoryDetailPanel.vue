<script setup>
/**
 * 行业分类详情侧栏：内容区滚动 + 底部操作栏始终可见（不参与裁剪）。
 */
import { formatDateTime } from "../../modules/interview/formatters";

defineProps({
  detail: { type: Object, default: null },
  loading: { type: Boolean, default: false }
});

defineEmits(["edit", "delete", "add-child"]);
</script>

<template>
  <aside class="detail-panel">
    <p v-if="loading" class="muted">加载详情…</p>
    <p v-else-if="!detail" class="muted">点击左侧分类查看详情，或新建一级 / 二级类目。</p>

    <template v-else>
      <div v-if="detail.level === 1" class="quick-bar">
        <button type="button" class="detail-btn detail-btn-accent" @click="$emit('add-child', detail.category_id)">
          + 添加二级分类
        </button>
      </div>

      <div class="detail-scroll">
        <div class="head">
          <span class="level-tag">L{{ detail.level }}</span>
          <h2>{{ detail.category_name }}</h2>
          <span class="status" :class="detail.status">{{ detail.status === "active" ? "启用" : "停用" }}</span>
        </div>

        <dl class="meta">
          <div><dt>ID</dt><dd><code>{{ detail.category_id }}</code></dd></div>
          <div><dt>编码</dt><dd>{{ detail.category_code }}</dd></div>
          <div v-if="detail.parent_name"><dt>所属一级</dt><dd>{{ detail.parent_name }}</dd></div>
          <div v-if="detail.child_count != null"><dt>二级数量</dt><dd>{{ detail.child_count }}</dd></div>
          <div><dt>描述</dt><dd>{{ detail.description || "—" }}</dd></div>
          <div><dt>意图关键词</dt><dd>{{ detail.intent_keywords || "—" }}</dd></div>
          <div><dt>意图识别</dt><dd>{{ detail.enabled_for_intent ? "是" : "否" }}</dd></div>
          <div><dt>大纲分类</dt><dd>{{ detail.enabled_for_classify ? "是" : "否" }}</dd></div>
          <div><dt>排序</dt><dd>{{ detail.sort_no ?? 0 }}</dd></div>
          <div><dt>创建</dt><dd>{{ formatDateTime(detail.created_at) }}</dd></div>
          <div><dt>更新</dt><dd>{{ formatDateTime(detail.updated_at) }}</dd></div>
        </dl>
      </div>

      <footer class="actions">
        <button type="button" class="detail-btn detail-btn-primary" @click="$emit('edit', detail.category_id)">编辑</button>
        <button v-if="detail.level === 1" type="button" class="detail-btn detail-btn-outline" @click="$emit('add-child', detail.category_id)">
          添加二级
        </button>
        <button type="button" class="detail-btn detail-btn-danger" @click="$emit('delete', detail.category_id)">删除</button>
      </footer>
    </template>
  </aside>
</template>

<style scoped>
.detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.quick-bar {
  flex-shrink: 0;
  padding: 12px 16px 0;
}

.detail-btn-accent {
  width: 100%;
  border: 1px dashed #a5b4fc;
  background: #eef2ff;
  color: #4338ca;
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}

.detail-btn-accent:hover {
  background: #e0e7ff;
  border-color: #6366f1;
}

.detail-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 16px 8px;
  -webkit-overflow-scrolling: touch;
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.head h2 {
  font-size: 1.08rem;
  margin: 0;
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.level-tag {
  font-size: 0.72rem;
  font-weight: 700;
  background: #eef2ff;
  color: #4338ca;
  padding: 2px 8px;
  border-radius: 999px;
}

.status {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 999px;
}

.status.active {
  background: #d1fae5;
  color: #047857;
}

.status.disabled {
  background: #f3f4f6;
  color: #6b7280;
}

.meta {
  display: grid;
  gap: 10px;
  margin: 0;
  padding-bottom: 8px;
}

.meta div {
  display: grid;
  grid-template-columns: 84px 1fr;
  gap: 8px;
  font-size: 0.86rem;
}

.meta dt {
  color: #6b7280;
  margin: 0;
}

.meta dd {
  margin: 0;
  color: #1f2937;
  word-break: break-word;
}

.actions {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid #eceff3;
  background: #fff;
  box-shadow: 0 -6px 16px rgba(15, 23, 42, 0.06);
  position: relative;
  z-index: 5;
}

/* 独立类名，避免与全站 .btn（白字紫底）冲突导致白底看不见字 */
.detail-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.85rem;
  font-weight: 600;
  font-family: inherit;
  line-height: 1.25;
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
}

.detail-btn-primary {
  border: 1px solid #6366f1;
  background: #6366f1;
  color: #fff;
}

.detail-btn-outline {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
}

.detail-btn-outline:hover {
  border-color: #a5b4fc;
  background: #f5f3ff;
  color: #4338ca;
}

.detail-btn-danger {
  border: 1px solid #fecaca;
  color: #dc2626;
  background: #fff;
}

.detail-btn-danger:hover {
  background: #fef2f2;
}

.muted {
  color: #6b7280;
  text-align: center;
  padding: 48px 16px;
}
</style>
