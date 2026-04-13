const API = "";
// Use wss:// on HTTPS pages to avoid mixed-content block
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/subtitles`;

const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");
const statusDot = document.getElementById("statusDot");
const subtitleBox = document.getElementById("subtitleBox");
const keywordsEl = document.getElementById("keywords");
const avatarImg = document.getElementById("avatarImg");
const avatarLabel = document.getElementById("avatarLabel");
const summaryPanel = document.getElementById("summaryPanel");
const summaryText = document.getElementById("summaryText");
const statusMsg = document.getElementById("statusMsg");
const micSelect = document.getElementById("micSelect");
const langBtns = document.querySelectorAll(".lang-btn");

let ws = null;
let wsReady = false; // true only after ws.onopen fires
let currentSessionId = null;
let audioCtx = null;
let mediaStream = null;
let workletNode = null;
let actualSampleRate = null;

async function startSession() {
  // Get mic, fill selector if first time
  try {
    const deviceId = micSelect.value;
    const audioConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints, video: false });
    // After first permission grant, refresh list with real labels
    await fillMicSelect();
    console.log("[Mic] using:", micSelect.options[micSelect.selectedIndex]?.textContent);
  } catch (e) {
    alert("Нет доступа к микрофону: " + e.message);
    return;
  }

  statusMsg.textContent = "Подключение...";
  const res = await fetch(`${API}/session/start`, { method: "POST" });
  const data = await res.json();
  currentSessionId = data.session_id;

  setActive(true);
  statusMsg.textContent = "Открытие канала...";
  // Open WS first, capture starts only after socket is open
  await openWSAndWait();
  statusMsg.textContent = "Запись";
  await startCapture();
}

async function stopSession() {
  stopCapture();
  if (ws) { ws.close(); ws = null; }
  wsReady = false;
  statusMsg.textContent = "Генерация резюме...";

  const res = await fetch(`${API}/session/stop`, { method: "POST" });
  const data = await res.json();
  setActive(false);

  if (data.session_id) await fetchSummary(data.session_id);
}

function openWSAndWait() {
  return new Promise((resolve, reject) => {
    ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      console.log("[WS] connected");
      wsReady = true;
      resolve();
    };
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        console.log("[WS] subtitle:", payload.text);
        if (payload.type === "subtitle") appendSubtitle(payload);
      } catch (_) {}
    };
    ws.onerror = (e) => {
      console.error("[WS] error", e);
      setActive(false);
      reject(e);
    };
    ws.onclose = (e) => {
      console.log("[WS] closed", e.code);
      wsReady = false;
    };
  });
}

async function startCapture() {
  // Request 16000 Hz but the browser may return a different rate — worklet reports actual
  audioCtx = new AudioContext({ sampleRate: 16000 });
  if (audioCtx.state === "suspended") await audioCtx.resume();
  console.log("[Audio] AudioContext state:", audioCtx.state, "requested rate: 16000, actual:", audioCtx.sampleRate);

  await audioCtx.audioWorklet.addModule("/static/recorder-worklet.js");

  const source = audioCtx.createMediaStreamSource(mediaStream);
  workletNode = new AudioWorkletNode(audioCtx, "recorder-processor");

  let chunkCount = 0;
  workletNode.port.onmessage = (e) => {
    const msg = e.data;

    if (msg.type === "init") {
      actualSampleRate = msg.sampleRate;
      console.log("[Audio] actual sample rate reported by worklet:", actualSampleRate);
      return;
    }

    if (msg.type === "chunk") {
      chunkCount++;
      const byteLen = msg.buffer.byteLength;
      console.log(`[Audio] chunk #${chunkCount} bytes=${byteLen} sampleRate=${msg.sampleRate}`);

      if (!wsReady) {
        console.warn("[Audio] WS not ready, dropping chunk");
        return;
      }

      // 8-byte header: magic uint32 0x4C414100 ("LAA\0") + uint32 LE sample rate
      // This magic cannot appear as a valid IEEE-754 float (it's a denormal near-zero NaN cluster),
      // so it won't collide with real PCM data.
      const header = new ArrayBuffer(8);
      const hView = new DataView(header);
      hView.setUint32(0, 0x4C414100, false); // big-endian magic "LAA\0"
      hView.setUint32(4, msg.sampleRate, true); // little-endian sample rate

      const combined = new Uint8Array(8 + byteLen);
      combined.set(new Uint8Array(header), 0);
      combined.set(new Uint8Array(msg.buffer), 8);

      ws.send(combined.buffer);
    }
  };

  // Do NOT connect workletNode to destination — we only want to capture, not play back
  source.connect(workletNode);
  console.log("[Audio] capture started");
}

function stopCapture() {
  if (workletNode) { workletNode.disconnect(); workletNode = null; }
  if (audioCtx) { audioCtx.close(); audioCtx = null; }
  if (mediaStream) { mediaStream.getTracks().forEach((t) => t.stop()); mediaStream = null; }
}

function appendSubtitle(payload) {
  const div = document.createElement("div");
  div.className = "subtitle-chunk";
  div.textContent = payload.text;
  subtitleBox.appendChild(div);
  subtitleBox.scrollTop = subtitleBox.scrollHeight;

  if (payload.keywords && payload.keywords.length) renderKeywords(payload.keywords);
  if (payload.avatar_url) {
    avatarImg.src = payload.avatar_url + "?t=" + Date.now();
    avatarLabel.textContent = payload.text.slice(0, 60);
  }
}

function renderKeywords(words) {
  keywordsEl.innerHTML = "";
  words.forEach((w) => {
    const span = document.createElement("span");
    span.className = "keyword-tag";
    span.textContent = w;
    keywordsEl.appendChild(span);
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
    console.error("Summary fetch failed:", e);
  }
}

function setActive(active) {
  btnStart.disabled = active;
  btnStop.disabled = !active;
  statusDot.className = active ? "dot dot-active" : "dot dot-idle";
  if (!active) {
    summaryPanel.classList.add("hidden");
    statusMsg.textContent = "";
  }
}

async function fillMicSelect() {
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
  // Restore previous selection if still present
  if (prev && [...micSelect.options].some(o => o.value === prev)) {
    micSelect.value = prev;
  }
  console.log("[Mic] list updated:", mics.map(d => d.label).join(", "));
}

// Try to fill on load (labels may be empty without permission — that's OK)
fillMicSelect().catch(() => {});

// Language switcher
langBtns.forEach(btn => {
  btn.addEventListener("click", async () => {
    const mode = btn.dataset.mode;
    langBtns.forEach(b => b.classList.remove("active", "loading"));
    btn.classList.add("loading");
    try {
      const res = await fetch(`${API}/session/mode/${mode}`, { method: "POST" });
      if (res.ok) {
        langBtns.forEach(b => b.classList.remove("active", "loading"));
        btn.classList.add("active");
        console.log("[Lang] switched to", mode);
      }
    } catch (e) {
      console.error("[Lang] switch failed:", e);
      btn.classList.remove("loading");
    }
  });
});

// Load current mode from server on page load
fetch(`${API}/session/mode`).then(r => r.json()).then(d => {
  langBtns.forEach(b => b.classList.toggle("active", b.dataset.mode === d.mode));
}).catch(() => {});

btnStart.addEventListener("click", startSession);
btnStop.addEventListener("click", stopSession);
