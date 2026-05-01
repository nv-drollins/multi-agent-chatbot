const answer = document.getElementById("answer");
const traceBox = document.getElementById("trace");
const terminal = document.getElementById("terminal");
const sources = document.getElementById("sources");
const timeline = document.getElementById("timeline");
const runState = document.getElementById("runState");
const preview = document.getElementById("preview");
const videoPreview = document.getElementById("videoPreview");
const imageFile = document.getElementById("imageFile");
const videoFile = document.getElementById("videoFile");
const docFile = document.getElementById("docFile");
const docContext = document.getElementById("docContext");
const appPrompt = document.getElementById("appPrompt");

const DEFAULT_APP_PROMPT = "Build a local briefing page from the active image, video, and document context. Include evidence, upload stats, GPU telemetry, and suggested next actions.";

let imageData = "";
let imageDirty = false;
let videoData = "";
let videoDirty = false;
let hasImageContext = false;
let hasVideoContext = false;
let activeDocuments = [];
let activeRole = "";

async function api(path, payload) {
  const res = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload || {})
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || res.statusText);
  return json;
}

async function getJson(path) {
  const res = await fetch(path);
  return res.json();
}

function setBusy(text) {
  runState.textContent = text || "Ready";
  document.querySelectorAll("button").forEach(btn => btn.disabled = Boolean(text));
}

async function refreshStatus() {
  const status = await getJson("/api/status");
  activeDocuments = status.active_documents || [];
  hasImageContext = Boolean(status.active_image);
  hasVideoContext = Boolean(status.active_video);
  document.getElementById("gpuScope").textContent = `GPU scope ${status.demo_gpu_index}`;
  renderModelChips(status.model_roles || {});
  const imageText = status.active_image ? "active image" : "no image";
  const videoText = status.active_video ? "active video" : "no video";
  const docText = activeDocuments.length ? `${activeDocuments.length} doc${activeDocuments.length === 1 ? "" : "s"}` : "no doc";
  document.getElementById("docStatus").textContent = `${imageText} / ${videoText} / ${docText}`;
  docContext.textContent = activeDocuments.length ? activeDocuments.join(", ") : "No uploaded document";
  renderGpu(status.gpu || []);
  renderTimeline(status.events || []);
}

function renderModelChips(roles) {
  const chips = {
    supervisor: document.getElementById("supervisorChip"),
    vision: document.getElementById("visionChip"),
    document: document.getElementById("documentChip"),
    app: document.getElementById("appChip"),
    embedding: document.getElementById("embedChip")
  };
  const labels = {
    supervisor: "Supervisor",
    vision: "Vision",
    document: "Document",
    app: "Coding Agent",
    embedding: "Embeddings"
  };
  Object.entries(chips).forEach(([role, el]) => {
    if (!el) return;
    el.textContent = `${labels[role]}: ${roles[role] || "local"}`;
    el.classList.toggle("active", role === activeRole);
  });
}

function setActiveRole(role) {
  activeRole = role || "";
  document.querySelectorAll(".model-chip").forEach(chip => {
    chip.classList.toggle("active", chip.dataset.role === activeRole);
  });
}

function renderGpu(gpus) {
  const wrap = document.getElementById("gpuMeters");
  wrap.innerHTML = "";
  const gpu = gpus.find(item => item.demo_gpu) || gpus[0];
  if (!gpu) {
    wrap.innerHTML = `<div class="meter"><strong>No GPU telemetry</strong></div>`;
    return;
  }
  const memPct = Math.round((gpu.memory_used_mib / gpu.memory_total_mib) * 100);
  const util = Math.round(gpu.utilization_gpu_pct || 0);
  const powerPct = Math.min(Math.round((Number(gpu.power_w || 0) / 600) * 100), 100);
  const tempPct = Math.min(Math.round((Number(gpu.temperature_c || 0) / 90) * 100), 100);
  const div = document.createElement("div");
  div.className = "gpu-card";
  div.innerHTML = `
    <strong>GPU ${escapeHtml(gpu.index)} - ${escapeHtml(gpu.name)}</strong>
    <div class="gauge-grid">
      ${gaugeHtml("Memory", memPct, `${Math.round(gpu.memory_used_mib)} / ${Math.round(gpu.memory_total_mib)} MiB`)}
      ${gaugeHtml("Utilization", util, `${util}%`)}
      ${gaugeHtml("Power", powerPct, `${Number(gpu.power_w || 0).toFixed(0)} W`)}
      ${gaugeHtml("Temperature", tempPct, `${Number(gpu.temperature_c || 0).toFixed(0)} C`)}
    </div>
  `;
  wrap.appendChild(div);
}

function gaugeHtml(label, pct, value) {
  const safePct = Math.max(0, Math.min(Number(pct) || 0, 100));
  return `
    <div class="gauge">
      <div class="gauge-head">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
      <div class="bar"><span style="width:${safePct}%"></span></div>
    </div>
  `;
}

function renderTimeline(events) {
  timeline.innerHTML = "";
  events.slice().reverse().forEach(evt => {
    const div = document.createElement("div");
    div.className = "event";
    div.innerHTML = `
      <time>${escapeHtml(evt.ts)} ${escapeHtml(evt.agent)}</time>
      <p><strong>${escapeHtml(evt.action)}</strong><br>${escapeHtml(evt.detail)}</p>
    `;
    timeline.appendChild(div);
  });
}

async function run(label, path, payload = {}, role = "") {
  setActiveRole(role);
  setBusy(label);
  answer.innerHTML = `<p class="loading">${escapeHtml(label)} locally...</p>`;
  try {
    const data = await api(path, payload);
    renderResult(data);
    await refreshStatus();
    return data;
  } catch (err) {
    answer.innerHTML = `<p class="bad">${escapeHtml(err.message)}</p>`;
    return null;
  } finally {
    setBusy("");
  }
}

function renderResult(data) {
  if (data.active_role) setActiveRole(data.active_role);
  if (data.image) {
    hasImageContext = true;
    imageDirty = false;
    setContextMode("image");
  }
  if (data.video) {
    hasVideoContext = true;
    videoDirty = false;
    setContextMode("video");
  }
  if (data.documents) {
    activeDocuments = data.documents;
    setContextMode("document");
  }
  const artifact = data.artifact
    ? `<a class="artifact-link" href="${escapeHtml(data.artifact.url)}" target="_blank" rel="noopener">Open briefing page</a>`
    : "";
  answer.innerHTML = `<p>${escapeHtml(data.answer || "Done.").replaceAll("\n", "<br>")}</p>${artifact}`;
  renderTrace(data.steps || []);
  renderSources(data.sources || []);
  if (data.terminal) {
    terminal.textContent = data.terminal;
  } else if (data.patch) {
    terminal.textContent = data.patch + "\n\nBefore:\n" + (data.tests_before?.output || "") + "\nAfter:\n" + (data.tests_after?.output || "");
  } else if (data.tests_after?.output) {
    terminal.textContent = data.tests_after.output;
  } else if (data.tests_before?.output) {
    terminal.textContent = data.tests_before.output;
  } else {
    terminal.textContent = "";
  }
}

function renderTrace(steps) {
  traceBox.innerHTML = "";
  steps.forEach(step => {
    const div = document.createElement("div");
    div.className = "tool-call";
    div.innerHTML = `
      <span>${escapeHtml(step.agent)}</span>
      <strong>${escapeHtml(step.tool)}</strong>
      <p>${escapeHtml(step.detail)}</p>
    `;
    traceBox.appendChild(div);
  });
}

function renderSources(items) {
  document.getElementById("sourceCount").textContent = String(items.length);
  sources.innerHTML = "";
  items.forEach(item => {
    const div = document.createElement("div");
    div.className = "source";
    div.innerHTML = `
      <span class="src">${escapeHtml(item.kind || "")}:${escapeHtml(item.source || "")} score ${item.score ?? ""}</span>
      <p>${escapeHtml(item.text || "")}</p>
    `;
    sources.appendChild(div);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(file);
  });
}

function currentContextMode() {
  return document.querySelector("input[name='contextMode']:checked")?.value || "image";
}

function setContextMode(mode) {
  const item = document.querySelector(`input[name='contextMode'][value='${mode}']`);
  if (item) item.checked = true;
}

function shouldSendImageWithQuestion(mode) {
  return mode === "image" && imageData && imageDirty;
}

function shouldSendVideoWithQuestion(mode) {
  return mode === "video" && videoData && videoDirty;
}

function resetLocalUi() {
  imageData = "";
  imageDirty = false;
  videoData = "";
  videoDirty = false;
  hasImageContext = false;
  hasVideoContext = false;
  activeDocuments = [];
  imageFile.value = "";
  videoFile.value = "";
  docFile.value = "";
  preview.removeAttribute("src");
  videoPreview.removeAttribute("src");
  videoPreview.load();
  appPrompt.value = DEFAULT_APP_PROMPT;
  docContext.textContent = "No uploaded document";
  setContextMode("image");
  setActiveRole("");
  terminal.textContent = "";
  renderSources([]);
}

imageFile.addEventListener("change", event => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    imageData = reader.result;
    imageDirty = true;
    preview.src = imageData;
    setContextMode("image");
  };
  reader.readAsDataURL(file);
});

videoFile.addEventListener("change", event => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    videoData = reader.result;
    videoDirty = true;
    videoPreview.src = URL.createObjectURL(file);
    setContextMode("video");
  };
  reader.readAsDataURL(file);
});

document.getElementById("imageBtn").addEventListener("click", async () => {
  if (!imageData) {
    answer.innerHTML = `<p class="bad">Upload an image first.</p>`;
    return;
  }
  await run("Image ID Agent", "/api/image", {image_data: imageData}, "vision");
});

document.getElementById("videoBtn").addEventListener("click", async () => {
  const file = videoFile.files[0];
  if (!file || !videoData) {
    answer.innerHTML = `<p class="bad">Upload a short video first.</p>`;
    return;
  }
  await run("Video ID Agent", "/api/video", {video_data: videoData, name: file.name, mime: file.type || ""}, "vision");
});

document.getElementById("docBtn").addEventListener("click", async () => {
  const files = Array.from(docFile.files || []);
  if (!files.length) {
    answer.innerHTML = `<p class="bad">Upload a document first.</p>`;
    return;
  }
  setActiveRole("embedding");
  const documents = await Promise.all(files.map(async file => ({
    name: file.name,
    mime: file.type || "",
    data: await readFileAsDataURL(file)
  })));
  await run("Document RAG Agent", "/api/document", {documents}, "embedding");
});

document.getElementById("generateBtn").addEventListener("click", () => {
  const prompt = appPrompt.value.trim() || DEFAULT_APP_PROMPT;
  run("Coding Agent", "/api/generate", {prompt}, "app");
});

document.getElementById("resetBtn").addEventListener("click", async () => {
  const data = await run("Resetting", "/api/reset", {}, "supervisor");
  if (data?.ok) resetLocalUi();
  await refreshStatus();
});

document.getElementById("chatForm").addEventListener("submit", event => {
  event.preventDefault();
  const input = document.getElementById("question");
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  const mode = currentContextMode();
  const payload = {question, mode};
  if (shouldSendImageWithQuestion(mode)) payload.image_data = imageData;
  if (shouldSendVideoWithQuestion(mode)) {
    payload.video_data = videoData;
    payload.name = videoFile.files[0]?.name || "uploaded-video.mp4";
    payload.mime = videoFile.files[0]?.type || "";
  }
  const role = mode === "document" ? "document" : (mode === "video" || mode === "image" ? "vision" : "supervisor");
  run("Supervisor routing", "/api/chat", payload, role);
});

refreshStatus().catch(err => {
  answer.innerHTML = `<p class="bad">${escapeHtml(err.message)}</p>`;
});

setInterval(() => {
  refreshStatus().catch(() => {});
}, 2000);
