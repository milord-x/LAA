const API = "";
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/subtitles`;

const btnStart    = document.getElementById("btnStart");
const btnStop     = document.getElementById("btnStop");
const statusDot   = document.getElementById("statusDot");
const statusMsg   = document.getElementById("statusMsg");
const subtitleBox = document.getElementById("subtitleBox");
const keywordsEl  = document.getElementById("keywords");
const avatarImg   = document.getElementById("avatarImg");
const avatarLabel = document.getElementById("avatarLabel");
const summaryPanel = document.getElementById("summaryPanel");
const summaryText  = document.getElementById("summaryText");
const micSelect    = document.getElementById("micSelect");
const langBtns     = document.querySelectorAll(".lang-btn");

let ws          = null;
let wsReady     = false;
let audioCtx    = null;
let mediaStream = null;
let workletNode = null;

// ── Microphone list ──────────────────────────────────────────────────────────

async function initMicList() {
  // Request permission once so browser reveals device labels
  try {
    const s = await navigator.mediaDevices.getUserMedia({ audio: true });
    s.getTracks().forEach(t => t.stop()); // release immediately
  } catch (_) {}
  await fillMicSelect();
}

async function fillMicSelect() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const mics = devices.filter(d => d.kind === "audioinput");
    const prev = micSelect.value;
    micSelect.innerHTML = "";
    mics.forEach((d, i) => {
      const opt = document.createElement("option");
      opt.value = d.deviceId;
      opt.textContent = d.label || `Микрофон ${i + 1}`;
      micSelect.appendChild(opt);
    });
    if (prev && [...micSelect.options].some(o => o.value === prev)) {
      micSelect.value = prev;
    }
  } catch (e) {
    console.warn("[Mic] enumerate failed:", e.message);
  }
}

// Re-fill list when devices change (user plugs in headset etc.)
navigator.mediaDevices.addEventListener("devicechange", fillMicSelect);

// ── Session ──────────────────────────────────────────────────────────────────

async function startSession() {
  const deviceId = micSelect.value;
  try {
    const constraints = deviceId ? { deviceId: { exact: deviceId } } : true;
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: constraints, video: false });
    console.log("[Mic] using:", micSelect.options[micSelect.selectedIndex]?.textContent);
  } catch (e) {
    alert("Нет доступа к микрофону: " + e.message);
    return;
  }

  setStatus("Подключение...");
  let data;
  try {
    const res = await fetch(`${API}/session/start`, { method: "POST" });
    data = await res.json();
  } catch (e) {
    alert("Сервер недоступен: " + e.message);
    stopCapture();
    return;
  }

  setActive(true);
  setStatus("Открытие канала...");

  try {
    await openWSAndWait();
  } catch (e) {
    setActive(false);
    stopCapture();
    return;
  }

  setStatus("Запись");
  await startCapture();
}

async function stopSession() {
  stopCapture();
  if (ws) { ws.close(); ws = null; }
  wsReady = false;
  setStatus("Генерация резюме...");

  try {
    const res = await fetch(`${API}/session/stop`, { method: "POST" });
    const data = await res.json();
    setActive(false);
    if (data.session_id) await fetchSummary(data.session_id);
  } catch (_) {
    setActive(false);
  }
}

// ── WebSocket ────────────────────────────────────────────────────────────────

function openWSAndWait() {
  return new Promise((resolve, reject) => {
    ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    ws.onopen  = () => { wsReady = true; resolve(); };
    ws.onmessage = ({ data }) => {
      try {
        const p = JSON.parse(data);
        if (p.type === "subtitle") appendSubtitle(p);
      } catch (_) {}
    };
    ws.onerror = (e) => { console.error("[WS] error", e); reject(e); };
    ws.onclose = (e) => { wsReady = false; console.log("[WS] closed", e.code); };
  });
}

// ── Audio capture ────────────────────────────────────────────────────────────

async function startCapture() {
  audioCtx = new AudioContext({ sampleRate: 16000 });
  if (audioCtx.state === "suspended") await audioCtx.resume();

  await audioCtx.audioWorklet.addModule("/static/recorder-worklet.js");

  const source = audioCtx.createMediaStreamSource(mediaStream);
  workletNode  = new AudioWorkletNode(audioCtx, "recorder-processor");

  let n = 0;
  workletNode.port.onmessage = ({ data: msg }) => {
    if (msg.type === "init") {
      console.log("[Audio] worklet rate:", msg.sampleRate);
      return;
    }
    if (msg.type === "chunk" && wsReady) {
      n++;
      const header = new ArrayBuffer(8);
      const v = new DataView(header);
      v.setUint32(0, 0x4C414100, false);
      v.setUint32(4, msg.sampleRate, true);
      const frame = new Uint8Array(8 + msg.buffer.byteLength);
      frame.set(new Uint8Array(header), 0);
      frame.set(new Uint8Array(msg.buffer), 8);
      ws.send(frame.buffer);
      if (n % 5 === 1) console.log(`[Audio] chunk #${n} ${msg.buffer.byteLength}B`);
    }
  };

  source.connect(workletNode);
}

function stopCapture() {
  if (workletNode)  { workletNode.disconnect(); workletNode = null; }
  if (audioCtx)     { audioCtx.close(); audioCtx = null; }
  if (mediaStream)  { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }
}

// ── UI helpers ───────────────────────────────────────────────────────────────

function setActive(active) {
  btnStart.disabled  = active;
  btnStop.disabled   = !active;
  micSelect.disabled = active;  // lock mic selector during recording
  langBtns.forEach(b => b.disabled = active);
  statusDot.className = active ? "dot dot-active" : "dot dot-idle";
  if (!active) setStatus("");
}

function setStatus(msg) {
  statusMsg.textContent = msg;
}

function appendSubtitle({ text, keywords, avatar_url }) {
  const div = document.createElement("div");
  div.className = "subtitle-chunk";
  div.textContent = text;
  subtitleBox.appendChild(div);
  subtitleBox.scrollTop = subtitleBox.scrollHeight;

  if (keywords?.length) renderKeywords(keywords);
  if (avatar_url) {
    avatarImg.src = avatar_url + "?t=" + Date.now();
    avatarLabel.textContent = text.slice(0, 60);
  }
}

function renderKeywords(words) {
  keywordsEl.innerHTML = "";
  words.forEach(w => {
    const s = document.createElement("span");
    s.className = "keyword-tag";
    s.textContent = w;
    keywordsEl.appendChild(s);
  });
}

async function fetchSummary(sessionId) {
  try {
    const res = await fetch(`${API}/summary/${sessionId}`);
    if (!res.ok) return;
    const data = await res.json();
    summaryText.textContent = data.summary;
    summaryPanel.classList.remove("hidden");
    summaryPanel.scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    console.error("[Summary] fetch failed:", e);
  }
}

// ── Language switcher ────────────────────────────────────────────────────────

langBtns.forEach(btn => {
  btn.addEventListener("click", async () => {
    const mode = btn.dataset.mode;
    const isKZ = mode === "kz";
    langBtns.forEach(b => { b.classList.remove("active"); b.disabled = true; });
    setStatus(isKZ ? "Загрузка KZ модели (~10 сек)..." : "");
    try {
      const res = await fetch(`${API}/session/mode/${mode}`, { method: "POST" });
      if (res.ok) {
        langBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
      }
    } catch (e) {
      console.error("[Lang] switch failed:", e);
    } finally {
      langBtns.forEach(b => { b.disabled = false; });
      setStatus("");
    }
  });
});

// Sync lang buttons with server state on load
fetch(`${API}/session/mode`)
  .then(r => r.json())
  .then(d => langBtns.forEach(b => b.classList.toggle("active", b.dataset.mode === d.mode)))
  .catch(() => {});

// ── Init ─────────────────────────────────────────────────────────────────────

btnStart.addEventListener("click", startSession);
btnStop.addEventListener("click", stopSession);

// Request mic permission immediately so list shows real labels from the start
initMicList();
