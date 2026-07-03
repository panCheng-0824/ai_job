import { onBeforeUnmount, onMounted, ref } from "vue";

export function useIsMobile(breakpoint = 768) {
  const isMobile = ref(false);

  function check() {
    isMobile.value = window.innerWidth < breakpoint;
  }

  onMounted(() => {
    check();
    window.addEventListener("resize", check);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", check);
  });

  return { isMobile };
}
