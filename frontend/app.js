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

let ws = null;
let wsReady = false; // true only after ws.onopen fires
let currentSessionId = null;
let audioCtx = null;
let mediaStream = null;
let workletNode = null;
let actualSampleRate = null;

async function startSession() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  } catch (e) {
    alert("Нет доступа к микрофону: " + e.message);
    return;
  }

  const res = await fetch(`${API}/session/start`, { method: "POST" });
  const data = await res.json();
  currentSessionId = data.session_id;

  setActive(true);
  // Open WS first, capture starts only after socket is open
  await openWSAndWait();
  await startCapture();
}

async function stopSession() {
  stopCapture();
  if (ws) { ws.close(); ws = null; }
  wsReady = false;

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

      // Send a 5-byte header: 1 byte magic (0xAA) + 4 bytes uint32 LE sample rate
      // followed by raw float32 PCM samples.
      // Backend uses this to detect and resample if rate != 16000.
      const header = new ArrayBuffer(5);
      const hView = new DataView(header);
      hView.setUint8(0, 0xAA);
      hView.setUint32(1, msg.sampleRate, true); // little-endian

      const combined = new Uint8Array(5 + byteLen);
      combined.set(new Uint8Array(header), 0);
      combined.set(new Uint8Array(msg.buffer), 5);

      ws.send(combined.buffer);
    }
  };

  source.connect(workletNode);
  workletNode.connect(audioCtx.destination);
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
  if (!active) summaryPanel.classList.add("hidden");
}

btnStart.addEventListener("click", startSession);
btnStop.addEventListener("click", stopSession);
