<script setup>
/**
 * 行业分类树形列表：选中、快捷操作。
 */
defineProps({
  tree: { type: Array, default: () => [] },
  selectedId: { type: String, default: "" }
});

defineEmits(["select", "edit", "delete", "add-l1", "add-l2"]);
</script>

<template>
  <div class="tree-panel">
    <div class="toolbar">
      <button type="button" class="btn primary" @click="$emit('add-l1')">+ 一级分类</button>
    </div>
    <p v-if="!tree.length" class="empty">暂无分类，请新增一级行业</p>
    <ul v-else class="tree">
      <li v-for="l1 in tree" :key="l1.category_id" class="l1">
        <div
          class="row"
          :class="{ active: selectedId === l1.category_id, disabled: l1.status === 'disabled' }"
          @click="$emit('select', l1.category_id)"
        >
          <span class="name">{{ l1.category_name }}</span>
          <span class="ops" @click.stop>
            <button type="button" title="编辑" @click="$emit('edit', l1.category_id)">✎</button>
            <button type="button" title="添加二级" @click="$emit('add-l2', l1.category_id)">+</button>
            <button type="button" title="删除" class="danger" @click="$emit('delete', l1.category_id)">×</button>
          </span>
        </div>
        <ul v-if="l1.children?.length" class="l2-list">
          <li
            v-for="l2 in l1.children"
            :key="l2.category_id"
            class="row l2"
            :class="{ active: selectedId === l2.category_id, disabled: l2.status === 'disabled' }"
            @click="$emit('select', l2.category_id)"
          >
            <span class="name">{{ l2.category_name }}</span>
            <span class="ops" @click.stop>
              <button type="button" @click="$emit('edit', l2.category_id)">✎</button>
              <button type="button" class="danger" @click="$emit('delete', l2.category_id)">×</button>
            </span>
          </li>
        </ul>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.tree-panel {
  background: #fff;
  border: 1px solid #eceff3;
  border-radius: 16px;
  padding: 12px;
}
.toolbar {
  margin-bottom: 10px;
}
.btn {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 0.85rem;
  cursor: pointer;
}
.btn.primary {
  border-color: #6366f1;
  background: #6366f1;
  color: #fff;
  font-weight: 600;
}
.tree,
.l2-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.l1 + .l1 {
  margin-top: 6px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid transparent;
}
.row:hover {
  background: #f9fafb;
}
.row.active {
  background: #eef2ff;
  border-color: #c7d2fe;
}
.row.disabled .name {
  color: #9ca3af;
  text-decoration: line-through;
}
.l2 {
  margin-left: 12px;
  margin-top: 4px;
  font-size: 0.9rem;
}
.name {
  font-weight: 600;
  color: #374151;
}
.ops button {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 2px 6px;
  font-size: 0.85rem;
  color: #6b7280;
}
.ops button.danger {
  color: #dc2626;
}
.empty {
  text-align: center;
  color: #9ca3af;
  padding: 24px;
  font-size: 0.9rem;
}
</style>
