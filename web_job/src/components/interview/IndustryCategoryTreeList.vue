<script setup>
/**
 * 行业分类树形列表：一级可展开/收起二级，支持选中与高亮。
 */
import { ref } from "vue";

const props = defineProps({
  tree: { type: Array, default: () => [] },
  selectedId: { type: String, default: "" },
  /** 搜索命中时强制展开的一级 id 列表 */
  autoExpandIds: { type: Array, default: () => [] },
  /** 当前搜索词，用于空结果提示 */
  searchKeyword: { type: String, default: "" },
  /** 只读模式：隐藏编辑/删除，用于大纲筛选等场景 */
  readonly: { type: Boolean, default: false },
  /** 0=一/二级均可选；2=仅二级可选（一级点击仅展开） */
  selectableLevel: { type: Number, default: 0 }
});

const emit = defineEmits(["select", "edit", "delete", "add-child"]);

/** 已展开的一级 category_id；默认全部收缩 */
const expandedIds = ref(new Set());

function isExpanded(id) {
  if (props.autoExpandIds.includes(id)) return true;
  return expandedIds.value.has(id);
}

function toggleExpand(id, event) {
  event?.stopPropagation();
  const next = new Set(expandedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expandedIds.value = next;
}

function childCount(l1) {
  return (l1.children || []).length;
}

/** 一级行点击：selectableLevel=2 时仅展开，不选中 */
function onL1RowClick(l1) {
  if (props.selectableLevel === 2) {
    const next = new Set(expandedIds.value);
    next.add(l1.category_id);
    expandedIds.value = next;
    return;
  }
  emit("select", l1.category_id);
}
</script>

<template>
  <div class="tree-panel" :class="{ 'pick-l2-only': selectableLevel === 2 }">
    <p v-if="searchKeyword && !tree.length" class="empty">未找到与「{{ searchKeyword }}」匹配的分类。</p>
    <p v-else-if="!tree.length" class="empty">{{ readonly ? "暂无行业分类。" : "暂无行业分类，请点击「新增一级」。" }}</p>

    <section v-for="l1 in tree" :key="l1.category_id" class="l1-block">
      <div
        class="l1-row"
        :class="{ selected: selectableLevel !== 2 && selectedId === l1.category_id, disabled: l1.status === 'disabled', 'readonly-row': readonly }"
        @click="onL1RowClick(l1)"
      >
        <button
          type="button"
          class="expand-btn"
          :class="{ expanded: isExpanded(l1.category_id) }"
          :aria-expanded="isExpanded(l1.category_id)"
          :title="isExpanded(l1.category_id) ? '收起二级' : '展开二级'"
          @click="toggleExpand(l1.category_id, $event)"
        >
          <span class="chevron" aria-hidden="true" />
        </button>

        <div class="title-wrap">
          <span class="level">一级</span>
          <strong class="name">{{ l1.category_name }}</strong>
          <span v-if="l1.status === 'disabled'" class="badge-off">停用</span>
        </div>

        <span class="child-badge">{{ childCount(l1) }}</span>

        <div v-if="!readonly" class="row-actions" @click.stop>
          <button type="button" class="act" title="添加二级" @click="$emit('add-child', l1.category_id)">+</button>
          <button type="button" class="act" title="编辑" @click="$emit('edit', l1.category_id)">编</button>
          <button type="button" class="act danger" title="删除" @click="$emit('delete', l1.category_id)">删</button>
        </div>
      </div>

      <ul v-show="isExpanded(l1.category_id)" class="l2-list">
        <li
          v-for="l2 in l1.children || []"
          :key="l2.category_id"
          class="l2-row"
          :class="{ selected: selectedId === l2.category_id, disabled: l2.status === 'disabled', 'readonly-row': readonly }"
          @click="$emit('select', l2.category_id)"
        >
          <div class="title-wrap l2-title">
            <span class="level l2">二级</span>
            <span class="name">{{ l2.category_name }}</span>
            <span v-if="l2.status === 'disabled'" class="badge-off">停用</span>
          </div>
          <div v-if="!readonly" class="row-actions" @click.stop>
            <button type="button" class="act" title="编辑" @click="$emit('edit', l2.category_id)">编</button>
            <button type="button" class="act danger" title="删除" @click="$emit('delete', l2.category_id)">删</button>
          </div>
        </li>
        <li v-if="!childCount(l1)" class="l2-empty">
          {{ readonly ? "暂无二级分类" : "暂无二级，可点击「+」添加" }}
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.pick-l2-only .l1-row {
  cursor: pointer;
}

.pick-l2-only .l2-row {
  cursor: pointer;
}

.tree-panel {
  background: #fff;
  border: 1px solid var(--home-card-border, rgba(91, 106, 223, 0.12));
  border-radius: var(--home-radius-lg, 16px);
  padding: 10px;
  box-shadow: var(--home-card-shadow, 0 6px 24px rgba(91, 106, 223, 0.07));
}

.l1-block + .l1-block {
  margin-top: 6px;
}

.l1-row {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 6px;
  padding: 8px 8px 8px 4px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.l1-row.readonly-row {
  grid-template-columns: 28px minmax(0, 1fr) auto;
}

.l2-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 8px 10px 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.l2-row.readonly-row {
  grid-template-columns: minmax(0, 1fr);
}

.l1-row:hover,
.l2-row:hover {
  background: #f8fafc;
}

.l1-row.selected,
.l2-row.selected {
  background: #eef2ff;
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.28);
}

.l1-row.disabled,
.l2-row.disabled {
  opacity: 0.62;
}

.expand-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.expand-btn:hover {
  background: #eef2ff;
}

.chevron {
  display: block;
  width: 7px;
  height: 7px;
  border-right: 2px solid #6366f1;
  border-bottom: 2px solid #6366f1;
  transform: rotate(-45deg);
  transition: transform 0.2s ease;
  margin-top: -2px;
}

.expand-btn.expanded .chevron {
  transform: rotate(45deg);
  margin-top: 2px;
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.l2-title {
  padding-left: 18px;
}

.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
}

.level {
  flex-shrink: 0;
  font-size: 0.62rem;
  font-weight: 700;
  color: #4338ca;
  background: #eef2ff;
  padding: 1px 6px;
  border-radius: 4px;
}

.level.l2 {
  color: #047857;
  background: #ecfdf5;
}

.badge-off {
  flex-shrink: 0;
  font-size: 0.65rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 999px;
}

.child-badge {
  flex-shrink: 0;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 0.72rem;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.l2-list {
  list-style: none;
  margin: 2px 0 4px 14px;
  padding: 4px 0 4px 10px;
  border-left: 2px solid #e5e7eb;
}

.l2-row + .l2-row {
  margin-top: 2px;
}

.row-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.act {
  min-width: 28px;
  height: 28px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 7px;
  padding: 0 6px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.act:hover {
  border-color: #c7d2fe;
  color: #4f46e5;
  background: #f5f3ff;
}

.act.danger {
  color: #dc2626;
  border-color: #fecaca;
}

.act.danger:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}

.l2-empty,
.empty {
  color: #9ca3af;
  font-size: 0.82rem;
  padding: 8px 12px 8px 18px;
}
</style>
