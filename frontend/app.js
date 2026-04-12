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

let ws = null;
let currentSessionId = null;

async function startSession() {
  const res = await fetch(`${API}/session/start`, { method: "POST" });
  const data = await res.json();
  currentSessionId = data.session_id;

  setActive(true);
  connectWS();
}

async function stopSession() {
  if (ws) { ws.close(); ws = null; }

  const res = await fetch(`${API}/session/stop`, { method: "POST" });
  const data = await res.json();

  setActive(false);

  if (data.session_id) {
    await fetchSummary(data.session_id);
  }
}

function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "subtitle") {
      appendSubtitle(payload);
    }
  };

  ws.onerror = () => setActive(false);
  ws.onclose = () => {};
}

function appendSubtitle(payload) {
  const div = document.createElement("div");
  div.className = "subtitle-chunk";
  div.textContent = payload.text;
  subtitleBox.appendChild(div);
  subtitleBox.scrollTop = subtitleBox.scrollHeight;

  if (payload.keywords && payload.keywords.length) {
    renderKeywords(payload.keywords);
  }

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
  }
}

btnStart.addEventListener("click", startSession);
btnStop.addEventListener("click", stopSession);
