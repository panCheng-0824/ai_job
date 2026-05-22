<script setup>
import { onBeforeUnmount, ref } from "vue";

const props = defineProps({
  compact: { type: Boolean, default: false }
});

const emit = defineEmits(["recognized"]);
const imageUrl = ref("");
const lang = ref("ch");
const useAngle = ref(true);
const file = ref(null);
const loading = ref(false);
const error = ref("");
const summary = ref("尚未执行识别");
const items = ref([]);
const viewMode = ref("block");
const aggregateText = ref("");
const selectedFileName = ref("未选择文件");
const history = ref([]);
const imagePreviewUrl = ref("");
const previewTip = ref("预览区域");
const showOverlay = ref(false);
const fileInputRef = ref(null);
let objectUrl = "";

function pickFile() {
  fileInputRef.value?.click();
}

function applySelectedFile(selected) {
  if (!selected) {
    file.value = null;
    selectedFileName.value = "未选择文件";
    return;
  }
  file.value = selected;
  selectedFileName.value = `已选择：${selected.name}（${Math.ceil(selected.size / 1024)}KB）`;
  const lower = selected.name.toLowerCase();
  const isImage = /\.(png|jpe?g|bmp|webp|tiff?)$/i.test(lower);
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = "";
  if (isImage) {
    objectUrl = URL.createObjectURL(selected);
    imagePreviewUrl.value = objectUrl;
    previewTip.value = "当前预览：本地图片";
  } else {
    imagePreviewUrl.value = "";
    previewTip.value = `已选 ${selected.name}（PDF/Word 无缩略图，可直接点「识别当前文件」）`;
  }
}

function onFileChange(evt) {
  applySelectedFile(evt.target.files?.[0] || null);
  if (evt.target) evt.target.value = "";
}

function previewByUrl() {
  const url = imageUrl.value.trim();
  if (!url) {
    error.value = "请输入图片链接";
    return;
  }
  if (!/^https?:\/\//i.test(url)) {
    error.value = "图片链接需以 http:// 或 https:// 开头";
    return;
  }
  file.value = null;
  selectedFileName.value = "未选择文件";
  imagePreviewUrl.value = url;
  previewTip.value = "当前预览：链接图片";
}

function onDropFile(evt) {
  const dropped = evt.dataTransfer?.files?.[0];
  if (!dropped) return;
  applySelectedFile(dropped);
}

async function run() {
  error.value = "";
  loading.value = true;
  try {
    let resp;
    if (file.value) {
      const form = new FormData();
      form.append("file", file.value);
      form.append("lang", lang.value);
      form.append("use_angle_cls", useAngle.value ? "true" : "false");
      resp = await fetch("/api/ocr/recognize-upload", { method: "POST", body: form });
    } else if (imageUrl.value.trim()) {
      resp = await fetch("/api/ocr/recognize-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_url: imageUrl.value.trim(),
          lang: lang.value,
          use_angle_cls: useAngle.value
        })
      });
    } else {
      throw new Error("请先选择文件或输入链接");
    }
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "识别失败");
    items.value = data.items || [];
    aggregateText.value = items.value.map((item) => String(item.text || "").trim()).filter(Boolean).join("\n");
    const modeLabel =
      data.mode === "text_extract"
        ? "文本抽取"
        : data.mode === "ocr"
          ? "OCR"
          : "";
    const typeLabel = data.file_type ? ` · ${data.file_type}` : "";
    summary.value = `识别完成${modeLabel ? `（${modeLabel}${typeLabel}）` : ""}，共 ${data.count || 0} 条`;
    history.value.unshift({
      time: new Date().toLocaleString(),
      source: file.value ? "上传识别" : "链接识别",
      name: file.value ? file.value.name : (imageUrl.value.trim() || "-"),
      count: Number(data.count || 0)
    });
    if (history.value.length > 10) history.value.pop();
    emit("recognized", {
      text: aggregateText.value,
      fileName: file.value ? file.value.name : imageUrl.value.trim(),
      count: Number(data.count || 0),
      mode: data.mode || ""
    });
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function openOverlay() {
  if (!imagePreviewUrl.value) return;
  showOverlay.value = true;
}

function closeOverlay() {
  showOverlay.value = false;
}

onBeforeUnmount(() => {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
});
</script>

<template>
  <div class="ocr-root" :class="{ 'ocr-root--compact': props.compact }">
    <main class="wrap">
      <h2 v-if="props.compact" class="pane-title">OCR 识别</h2>
      <section class="panel">

        <label>文件访问链接（图片或 PDF）</label>
        <div class="link-row">
          <input v-model="imageUrl" placeholder="图片或 PDF 链接，如 https://example.com/resume.pdf" @keydown.enter.prevent="previewByUrl" />
          <button class="btn secondary" @click="previewByUrl">预览链接</button>
        </div>
        <div class="upload-wrap" @dragover.prevent @drop.prevent="onDropFile">
          <div class="muted">或把简历文件（图片 / PDF / Word）拖拽到这里，也可以点击按钮上传</div>
          <div class="muted" style="margin-top: 6px;">{{ selectedFileName }}</div>
          <div class="upload-actions">
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*,.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              class="hidden-file"
              @change="onFileChange"
            />
            <button type="button" class="btn secondary" @click="pickFile">选择文件</button>
          </div>
          <div class="preview-wrap">
            <div class="muted">{{ previewTip }}</div>
            <img v-if="imagePreviewUrl" :src="imagePreviewUrl" class="preview-image" alt="待识别图片预览" @click="openOverlay" />
          </div>
        </div>
        <div class="row">
          <div>
            <label>语言</label>
            <select v-model="lang">
              <option value="ch">ch（中文）</option>
              <option value="en">en（英文）</option>
              <option value="chinese_cht">chinese_cht（繁体）</option>
            </select>
          </div>
          <label><input v-model="useAngle" type="checkbox" /> 角度分类</label>
          <button class="btn" :disabled="loading" @click="run">{{ loading ? "识别中..." : "识别当前文件" }}</button>
        </div>
      </section>
      <p class="summary">{{ summary }}</p>
      <p class="error">{{ error }}</p>
      <div v-if="items.length" class="toolbar">
        <button :class="{ active: viewMode === 'block' }" @click="viewMode='block'">分块展示</button>
        <button :class="{ active: viewMode === 'aggregate' }" @click="viewMode='aggregate'">聚合展示</button>
      </div>
      <div v-if="viewMode==='block'" class="result-list">
        <div v-for="(item, idx) in items" :key="idx" class="item">
          <p><strong>#{{ idx + 1 }}</strong> {{ item.text }}</p>
          <p>score: {{ Number(item.score || 0).toFixed(4) }}</p>
        </div>
      </div>
      <pre v-else class="aggregate">{{ aggregateText || "暂无聚合文本" }}</pre>
      <div class="raw-wrap">
        <div class="history-wrap">
          <div class="history-header">
            <strong style="font-size: 14px;">识别历史（本地临时）</strong>
            <button class="btn secondary" @click="history = []">清空历史</button>
          </div>
          <div class="history-list">
            <div v-if="!history.length" class="history-item">暂无历史记录</div>
            <div v-for="(item, idx) in history" v-else :key="idx" class="history-item">
              <div>时间：{{ item.time }}</div>
              <div>来源：{{ item.source }}</div>
              <div>图片：{{ item.name }}</div>
              <div>结果：{{ item.count }} 条</div>
            </div>
          </div>
        </div>
        <details>
          <summary>查看原始 JSON</summary>
          <pre>{{ JSON.stringify(items, null, 2) }}</pre>
        </details>
      </div>
    </main>
    <div v-if="showOverlay" class="preview-overlay" @click="closeOverlay">
      <img :src="imagePreviewUrl" class="overlay-image" alt="放大预览图片" />
    </div>
  </div>
</template>

<style scoped>
.wrap { max-width: 980px; margin: 0 auto; padding: 12px 20px 20px; }
.panel { border-radius: 16px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06); padding: 16px; }
label { display: block; margin: 10px 0 6px; color: var(--text-muted); font-size: 13px; font-weight: 600; }
input, select { width: 100%; border: 1px solid #d1d5db; border-radius: 10px; padding: 10px 12px; font-size: 14px; }
.row { display: grid; grid-template-columns: 1fr 170px 160px; gap: 10px; align-items: end; margin-top: 10px; }
.link-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 8px; align-items: center; }
.upload-wrap { margin-top: 14px; border: 2px dashed #c7d2fe; border-radius: 12px; padding: 16px; text-align: center; background: #fafaff; }
.upload-actions { margin-top: 10px; display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
.hidden-file { display: none; }
.preview-wrap { margin-top: 12px; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px; background: #fff; }
.preview-image { max-width: 100%; max-height: 240px; border-radius: 8px; border: 1px solid #eceff3; cursor: zoom-in; }
.ocr-root--compact .wrap { max-width: 100%; padding: 0; }
.ocr-root--compact .panel {
  border-radius: 14px;
  box-shadow: none;
  border: 1px solid #e5e7eb;
  padding: 14px;
}
.ocr-root--compact .preview-image { max-height: 180px; }
.ocr-root--compact .row {
  grid-template-columns: 1fr;
  gap: 12px;
}
@media (min-width: 720px) {
  .ocr-root--compact .row {
    grid-template-columns: 1fr auto auto;
    align-items: end;
  }
}
.pane-title {
  margin: 0 0 12px;
  font-size: 0.95rem;
  font-weight: 700;
  color: #374151;
}
.preview-overlay { position: fixed; inset: 0; z-index: 1200; background: rgba(0,0,0,.72); display: flex; align-items: center; justify-content: center; padding: 24px; cursor: zoom-out; }
.overlay-image { max-width: min(92vw, 1500px); max-height: 92vh; border-radius: 10px; box-shadow: 0 20px 46px rgba(0,0,0,.45); border: 1px solid rgba(255,255,255,.2); }
.summary { color: var(--text-muted); margin: 12px 0; font-size: 13px; }
.error { min-height: 0; }
.toolbar { margin-top: 12px; display: flex; gap: 8px; }
.toolbar button { border: 1px solid #d1d5db; background: #fff; color: var(--text-main); border-radius: 8px; padding: 8px 10px; cursor: pointer; }
.toolbar button.active { background: var(--primary-color); color: #fff; }
.result-list { margin-top: 12px; display: grid; gap: 8px; }
.item { border: 1px solid #eceff3; border-radius: 10px; padding: 10px; background: #fff; }
.aggregate { margin-top: 12px; border-radius: 10px; background: #fff; border: 1px solid #eceff3; color: #111; padding: 12px; white-space: pre-wrap; }
.raw-wrap { margin-top: 12px; }
.history-wrap { margin-top: 14px; border: 1px solid #eceff3; border-radius: 12px; padding: 10px; background: #fff; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.history-list { display: grid; gap: 8px; }
.history-item { border: 1px solid #eceff3; border-radius: 8px; padding: 8px; font-size: 12px; color: var(--text-muted); }
pre { margin: 0; border-radius: 10px; background: #0f172a; color: #f8fafc; padding: 12px; max-height: 38vh; overflow: auto; font-size: 12px; }
.muted { color: var(--text-muted); font-size: 13px; }
</style>
