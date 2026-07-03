/**
 * 登录后壳层顶栏状态：各页面通过 composable 注册标题与副标题，由 HomeLayout 统一渲染。
 */
import { isRef, onBeforeUnmount, reactive, unref, watch } from "vue";

function defaultHeader() {
  return {
    title: "",
    subtitle: "",
    studentName: "",
    hidden: false,
    /** 'interview' 时在顶栏下展示面试模块二级导航 */
    sectionNav: null
  };
}

export const homePageHeader = reactive(defaultHeader());

function applyHeader(source) {
  const value = unref(source);
  if (!value) {
    Object.assign(homePageHeader, defaultHeader());
    return;
  }
  Object.assign(homePageHeader, defaultHeader(), value);
}

/**
 * @param {import('vue').MaybeRefOrGetter<object>} source 标题配置或 computed
 */
export function useHomePageHeader(source) {
  if (isRef(source) || typeof source === "function") {
    const stop = watch(source, applyHeader, { immediate: true, deep: true, flush: "post" });
    onBeforeUnmount(() => {
      stop();
      Object.assign(homePageHeader, defaultHeader());
    });
    return homePageHeader;
  }

  applyHeader(source);
  onBeforeUnmount(() => {
    Object.assign(homePageHeader, defaultHeader());
  });
  return homePageHeader;
}
