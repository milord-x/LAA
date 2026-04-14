const API = "";
const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/subtitles`;

const btnStart    = document.getElementById("btnStart");
const btnStop     = document.getElementById("btnStop");
const statusDot   = document.getElementById("statusDot");
const statusMsg   = document.getElementById("statusMsg");
const subtitleBox = document.getElementById("subtitleBox");
const keywordsEl  = document.getElementById("keywords");
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
let sessionActive = false;  // single source of truth for session state
let langSwitching = false;  // prevent concurrent lang switches

// ── CWASA avatar ─────────────────────────────────────────────────────────────

let cwasaReady = false;
let avatarBusy = false;
const sigmlQueue = [];

function _drainQueue() {
  if (avatarBusy || sigmlQueue.length === 0) return;
  const sigml = sigmlQueue.shift();
  avatarBusy = true;
  try {
    CWASA.playSiGMLText(sigml, 0);
  } catch (e) {
    console.warn("[CWASA] playSiGMLText failed:", e.message);
    avatarBusy = false;
    _drainQueue();
  }
}

if (typeof CWASA !== "undefined") {
  CWASA.addHook("avatarready", () => {
    cwasaReady = true;
    console.log("[CWASA] avatar ready");
    _drainQueue();
  });
  CWASA.addHook("animidle", () => {
    avatarBusy = false;
    _drainQueue();
  });
}

function playSign(sigml) {
  if (!sigml || !cwasaReady) {
    if (sigml) { sigmlQueue.push(sigml); if (sigmlQueue.length > 5) sigmlQueue.shift(); }
    return;
  }
  sigmlQueue.push(sigml);
  if (sigmlQueue.length > 5) sigmlQueue.shift();
  _drainQueue();
}

// ── Microphone list ──────────────────────────────────────────────────────────

async function initMicList() {
  try {
    const s = await navigator.mediaDevices.getUserMedia({ audio: true });
    s.getTracks().forEach(t => t.stop());
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
    if (prev && [...micSelect.options].some(o => o.value === prev)) micSelect.value = prev;
  } catch (e) {
    console.warn("[Mic] enumerate failed:", e.message);
  }
}

navigator.mediaDevices.addEventListener("devicechange", fillMicSelect);

// ── Session ──────────────────────────────────────────────────────────────────

async function startSession() {
  if (sessionActive) return;  // guard double-click

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
  try {
    const res = await fetch(`${API}/session/start`, { method: "POST" });
    if (!res.ok) {
      alert("Ошибка сервера: " + res.status);
      stopCapture();
      return;
    }
    await res.json();
  } catch (e) {
    alert("Сервер недоступен: " + e.message);
    stopCapture();
    return;
  }

  sessionActive = true;
  setActive(true);
  setStatus("Открытие канала...");

  try {
    await openWSAndWait();
  } catch (e) {
    sessionActive = false;
    setActive(false);
    stopCapture();
    return;
  }

  setStatus("Запись");
  await startCapture();
}

async function stopSession() {
  if (!sessionActive) return;  // guard if already stopped

  sessionActive = false;
  stopCapture();
  if (ws) { ws.close(); ws = null; }
  wsReady = false;
  setActive(false);
  setStatus("Генерация резюме...");

  try {
    const res = await fetch(`${API}/session/stop`, { method: "POST" });
    const data = await res.json();
    if (data.session_id) await fetchSummary(data.session_id);
  } catch (_) {}
  setStatus("");
}

// ── WebSocket ────────────────────────────────────────────────────────────────

function openWSAndWait() {
  return new Promise((resolve, reject) => {
    ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    ws.onopen = () => { wsReady = true; resolve(); };
    ws.onmessage = ({ data }) => {
      try {
        const p = JSON.parse(data);
        if (p.type === "subtitle") appendSubtitle(p);
      } catch (_) {}
    };
    ws.onerror = (e) => { console.error("[WS] error", e); reject(e); };
    ws.onclose = (e) => {
      wsReady = false;
      console.log("[WS] closed", e.code);
      // If session was still active (unexpected disconnect) — reset UI
      if (sessionActive) {
        sessionActive = false;
        stopCapture();
        setActive(false);
        setStatus("Соединение прервано");
        setTimeout(() => setStatus(""), 3000);
      }
    };
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
    if (msg.type === "init") { console.log("[Audio] worklet rate:", msg.sampleRate); return; }
    if (msg.type === "chunk" && wsReady && ws?.readyState === WebSocket.OPEN) {
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
  micSelect.disabled = active;
  statusDot.className = active ? "dot dot-active" : "dot dot-idle";
  if (!active) setStatus("");
  _updateLangBtns();
}

function _updateLangBtns() {
  // Lang buttons: disabled only during switch, never just because session is active
  langBtns.forEach(b => { b.disabled = langSwitching; });
}

function setStatus(msg) {
  statusMsg.textContent = msg;
}

function appendSubtitle({ text, keywords, avatar_sigml }) {
  const div = document.createElement("div");
  div.className = "subtitle-chunk";
  div.textContent = text;
  subtitleBox.appendChild(div);
  subtitleBox.scrollTop = subtitleBox.scrollHeight;

  if (keywords?.length) renderKeywords(keywords);
  if (avatar_sigml) {
    avatarLabel.textContent = text.slice(0, 60);
    playSign(avatar_sigml);
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
  if (!sessionId) return;
  try {
    const res = await fetch(`${API}/summary/${sessionId}`);
    if (!res.ok) return;
    const data = await res.json();
    if (!data.summary) return;
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
    if (langSwitching) return;  // prevent concurrent switches

    const mode = btn.dataset.mode;
    const isKZ = mode === "kz";
    const prevActive = document.querySelector(".lang-btn.active");

    langSwitching = true;
    _updateLangBtns();
    setStatus(isKZ ? "Загрузка KZ модели (~10 сек)..." : "Смена языка...");

    try {
      const res = await fetch(`${API}/session/mode/${mode}`, { method: "POST" });
      if (res.ok) {
        langBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
      } else {
        // Restore previous active on failure
        prevActive?.classList.add("active");
        console.error("[Lang] switch failed:", res.status);
      }
    } catch (e) {
      prevActive?.classList.add("active");
      console.error("[Lang] switch failed:", e);
    } finally {
      langSwitching = false;
      _updateLangBtns();
      setStatus(sessionActive ? "Запись" : "");
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

initMicList();

if (typeof CWASA !== "undefined") {
  CWASA.init();
}
