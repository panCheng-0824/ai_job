/**
 * 全站左下角导航轮盘 + 大浮框（iframe，带 _embed=1）
 * 依赖：body 末尾的 #portalWheelHost / #portalFrameBackdrop / #portalFramePanel 结构
 */
(function () {
  "use strict";

  var EMBED_Q = "_embed=1";

  function withEmbed(url) {
    try {
      var u = new URL(url, window.location.origin);
      u.searchParams.set("_embed", "1");
      return u.pathname + u.search + u.hash;
    } catch (e) {
      return url + (url.indexOf("?") >= 0 ? "&" : "?") + EMBED_Q;
    }
  }

  function stripEmbed(url) {
    try {
      var u = new URL(url, window.location.origin);
      u.searchParams.delete("_embed");
      return u.pathname + u.search + u.hash;
    } catch (e2) {
      return url;
    }
  }

  var WHEEL = [
    { path: "/student", label: "学生主页" },
    { path: "/resume", label: "我的简历" },
    { path: "/jobs", label: "岗位列表" },
    { path: "/companies", label: "企业列表" },
    { path: "/tools", label: "工具" },
    { path: "/student-chat", label: "对话助手" },
  ];

  function pathKey(pathname) {
    var p = pathname || "";
    if (p.startsWith("/student-chat")) return "/student-chat";
    if (p === "/student") return "/student";
    if (p === "/resume") return "/resume";
    if (p.startsWith("/jobs")) return "/jobs";
    if (p.startsWith("/companies")) return "/companies";
    if (p === "/tools" || p === "/data-search" || p === "/ocr") return "/tools";
    return "";
  }

  function openFrame(url, title) {
    var embedUrl = url.indexOf("_embed=") >= 0 ? url : withEmbed(url);
    var panel = document.getElementById("portalFramePanel");
    var iframe = document.getElementById("portalFrameIframe");
    var titleEl = document.getElementById("portalFrameTitle");
    if (!panel || !iframe) return;
    if (titleEl) titleEl.textContent = title || "页面";
    iframe.src = embedUrl;
    document.body.classList.add("portal-frame-open");
    panel.classList.remove("portal-frame--fullscreen");
    var fsBtn = document.getElementById("portalFrameBtnFs");
    if (fsBtn) fsBtn.textContent = "放大";
  }

  function closeFrame() {
    document.body.classList.remove("portal-frame-open");
    var panel = document.getElementById("portalFramePanel");
    var iframe = document.getElementById("portalFrameIframe");
    if (panel) {
      panel.classList.remove("portal-frame--fullscreen");
    }
    if (iframe) {
      iframe.src = "about:blank";
    }
    var fsBtn = document.getElementById("portalFrameBtnFs");
    if (fsBtn) fsBtn.textContent = "放大";
  }

  function toggleFullscreen() {
    var panel = document.getElementById("portalFramePanel");
    var fsBtn = document.getElementById("portalFrameBtnFs");
    if (!panel) return;
    var on = panel.classList.toggle("portal-frame--fullscreen");
    if (fsBtn) fsBtn.textContent = on ? "缩小" : "放大";
  }

  function goFullPage() {
    var iframe = document.getElementById("portalFrameIframe");
    if (!iframe || !iframe.src || iframe.src === "about:blank") return;
    try {
      var u = new URL(iframe.src, window.location.origin);
      u.searchParams.delete("_embed");
      window.open(u.pathname + u.search + u.hash, "_blank", "noopener,noreferrer");
    } catch (e) {
      window.open(stripEmbed(iframe.src), "_blank", "noopener,noreferrer");
    }
  }

  function initWheel() {
    if (document.documentElement.classList.contains("portal-embed")) return;

    var host = document.getElementById("portalWheelHost");
    if (!host) return;

    var fan = host.querySelector(".portal-wheel-fan");
    if (!fan) return;

    fan.innerHTML = "";
    var cur = pathKey(window.location.pathname);
    var n = WHEEL.length;
    /* 花瓣弧：从略偏右扫到偏上，逆时针为正角，CSS 内用 rotate(-a) */
    var petalStart = 30;
    var petalEnd = 150;
    var span = n <= 1 ? 0 : (petalEnd - petalStart) / (n - 1);

    WHEEL.forEach(function (item, i) {
      var deg = petalStart + span * i;
      var wrap = document.createElement("div");
      wrap.className = "portal-wheel-item";
      wrap.style.setProperty("--a", deg + "deg");
      wrap.style.setProperty("--i", String(i));
      if (cur && pathKey(item.path) === cur) wrap.classList.add("is-active");

      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = item.label;
      btn.addEventListener("click", function () {
        if (pathKey(window.location.pathname) === pathKey(item.path)) {
          closeFrame();
          return;
        }
        openFrame(item.path, item.label);
        host.classList.remove("portal-wheel-open");
      });

      wrap.appendChild(btn);
      fan.appendChild(wrap);
    });

    var trigger = host.querySelector(".portal-wheel-trigger");
    if (trigger) {
      trigger.addEventListener("click", function () {
        host.classList.toggle("portal-wheel-open");
      });
    }

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        closeFrame();
        host.classList.remove("portal-wheel-open");
      }
    });
  }

  function initFrameChrome() {
    var bd = document.getElementById("portalFrameBackdrop");
    var btnClose = document.getElementById("portalFrameBtnClose");
    var btnFs = document.getElementById("portalFrameBtnFs");
    var btnOpen = document.getElementById("portalFrameBtnOpenTab");
    if (bd) bd.addEventListener("click", closeFrame);
    if (btnClose) btnClose.addEventListener("click", closeFrame);
    if (btnFs) btnFs.addEventListener("click", toggleFullscreen);
    if (btnOpen) btnOpen.addEventListener("click", goFullPage);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initWheel();
      initFrameChrome();
    });
  } else {
    initWheel();
    initFrameChrome();
  }

  window.PortalNavWheel = {
    openFrame: openFrame,
    closeFrame: closeFrame,
    withEmbed: withEmbed,
  };
})();
