const API = "";
const WS_URL = `ws://${location.host}/ws/subtitles`;

const btnStart = document.getElementById("btnStart");
const btnStop = document.getElementById("btnStop");
const statusDot = document.getElementById("statusDot");
const subtitleBox = document.getElementById("subtitleBox");
const keywordsEl = document.getElementById("keywords");
const avatarImg = document.getElementById("avatarImg");
const avatarLabel = document.getElementById("avatarLabel");
const summaryPanel = document.getElementById("summaryPanel");
const summaryText = document.getElementById("summaryText");

const SAMPLE_RATE = 16000;
const CHUNK_SEC = 3;

let ws = null;
let currentSessionId = null;
let audioCtx = null;
let mediaStream = null;
let processor = null;
let pcmBuffer = [];
let pcmSamples = 0;
const TARGET_SAMPLES = SAMPLE_RATE * CHUNK_SEC;

async function startSession() {
  // Request mic first
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
  openWS();
  startCapture();
}

async function stopSession() {
  stopCapture();

  if (ws) { ws.close(); ws = null; }

  const res = await fetch(`${API}/session/stop`, { method: "POST" });
  const data = await res.json();

  setActive(false);

  if (data.session_id) {
    await fetchSummary(data.session_id);
  }
}

function openWS() {
  ws = new WebSocket(WS_URL);
  ws.binaryType = "arraybuffer";

  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === "subtitle") appendSubtitle(payload);
    } catch (_) {}
  };

  ws.onerror = () => setActive(false);
  ws.onclose = () => {};
}

function startCapture() {
  audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
  const source = audioCtx.createMediaStreamSource(mediaStream);

  processor = audioCtx.createScriptProcessor(4096, 1, 1);
  processor.onaudioprocess = (e) => {
    const samples = e.inputBuffer.getChannelData(0); // Float32Array
    pcmBuffer.push(new Float32Array(samples));
    pcmSamples += samples.length;

    if (pcmSamples >= TARGET_SAMPLES) {
      flushChunk();
    }
  };

  source.connect(processor);
  processor.connect(audioCtx.destination);
}

function flushChunk() {
  const merged = new Float32Array(pcmSamples);
  let offset = 0;
  for (const buf of pcmBuffer) {
    merged.set(buf, offset);
    offset += buf.length;
  }
  pcmBuffer = [];
  pcmSamples = 0;

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(merged.buffer);
  }
}

function stopCapture() {
  if (processor) {
    processor.disconnect();
    processor = null;
  }
  if (audioCtx) {
    audioCtx.close();
    audioCtx = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  pcmBuffer = [];
  pcmSamples = 0;
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
