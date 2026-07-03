<script setup>
/**
 * 我的简历页壳层：侧栏 + 工作区（模板 | 编辑 | 右栏）对齐设计稿 9/10/11。
 */
import "../../styles/resume-studio.css";
import HomeTopBar from "../home/HomeTopBar.vue";

defineProps({
  embed: { type: Boolean, default: false },
  drawerOpen: { type: Boolean, default: false },
  drawerTitle: { type: String, default: "" },
  templatesOpen: { type: Boolean, default: true },
  topBarTitle: { type: String, default: "" },
  topBarSubtitle: { type: String, default: "" },
  studentName: { type: String, default: "" }
});

defineEmits(["close-drawer", "update:templatesOpen"]);
</script>

<template>
  <div :class="embed ? 'resume-page resume-page--embed' : 'home-main'">
    <HomeTopBar
      v-if="!embed && topBarTitle"
      :title="topBarTitle"
      :subtitle="topBarSubtitle"
      :student-name="studentName"
    />
    <div class="rs-body">
      <div v-if="$slots.alerts" class="rs-alerts">
        <slot name="alerts" />
      </div>

      <div
        class="rs-workspace"
        :class="{
          'rs-workspace--templates-collapsed': !templatesOpen && !embed,
          'rs-workspace--with-rail': drawerOpen
        }"
      >
        <aside
          v-if="!embed"
          class="rs-templates"
          :class="{ 'rs-templates--collapsed': !templatesOpen }"
        >
          <slot name="templates" />
        </aside>

        <div class="rs-editor">
          <slot name="editor-prefix" />
          <div class="rs-editor-sheet-wrap">
            <slot name="editor" />
          </div>
        </div>

        <aside v-if="drawerOpen" class="rs-rail" aria-label="简历侧栏">
          <div class="rs-rail-head">
            <h3>{{ drawerTitle }}</h3>
            <button type="button" class="rs-rail-close" @click="$emit('close-drawer')">收起</button>
          </div>
          <div class="rs-rail-body">
            <slot name="drawer" />
          </div>
        </aside>
      </div>
    </div>

    <button
      v-if="drawerOpen && !embed"
      type="button"
      class="rs-rail-scrim"
      aria-label="关闭侧栏"
      @click="$emit('close-drawer')"
    />
  </div>
</template>

<style scoped>
.home-main {
  position: relative;
}
.resume-page--embed {
  min-height: 100dvh;
  height: 100dvh;
  overflow: hidden;
  background: #eef1f8;
  display: flex;
  flex-direction: column;
}
.resume-embed-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-width: none;
  margin: 0;
  padding: 10px 12px;
}
.resume-page--embed .rs-workspace {
  grid-template-columns: minmax(0, 1fr);
}
</style>
