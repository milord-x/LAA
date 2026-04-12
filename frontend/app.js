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

let ws = null;
let currentSessionId = null;
let audioCtx = null;
let mediaStream = null;
let workletNode = null;

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
  openWS();
  await startCapture();
}

async function stopSession() {
  stopCapture();
  if (ws) { ws.close(); ws = null; }

  const res = await fetch(`${API}/session/stop`, { method: "POST" });
  const data = await res.json();
  setActive(false);

  if (data.session_id) await fetchSummary(data.session_id);
}

function openWS() {
  ws = new WebSocket(WS_URL);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => console.log("[WS] connected");
  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      console.log("[WS] subtitle:", payload.text);
      if (payload.type === "subtitle") appendSubtitle(payload);
    } catch (_) {}
  };
  ws.onerror = (e) => { console.error("[WS] error", e); setActive(false); };
  ws.onclose = (e) => console.log("[WS] closed", e.code);
}

async function startCapture() {
  audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
  if (audioCtx.state === "suspended") await audioCtx.resume();
  console.log("[Audio] state:", audioCtx.state, "rate:", audioCtx.sampleRate);

  await audioCtx.audioWorklet.addModule("/static/recorder-worklet.js");

  const source = audioCtx.createMediaStreamSource(mediaStream);
  workletNode = new AudioWorkletNode(audioCtx, "recorder-processor");

  let chunkCount = 0;
  workletNode.port.onmessage = (e) => {
    chunkCount++;
    console.log(`[Audio] chunk #${chunkCount} ready, bytes: ${e.data.byteLength}`);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(e.data);
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
