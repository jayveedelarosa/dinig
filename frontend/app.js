// Dinig frontend: plain JavaScript, no build step, no internet.
// One page; each SITEMAP screen is a <section>. go("screen-id") switches screens.

const TEACHER_SCREENS = ["class-view"];

const state = {
  pupil: null,   // {id, first_name, ...}
  story: null,   // {id, title, full_text}
  reading: null, // POST /readings response
};

// ---------- Helpers ----------

const $ = (sel) => document.querySelector(sel);

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

function el(tag, attrs = {}, text = "") {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  if (text) node.textContent = text;
  return node;
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ---------- Navigation ----------

const onEnter = {}; // screen id -> function run when the screen opens

function go(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("active", s.id === id));
  document.body.className = TEACHER_SCREENS.includes(id) ? "teacher" : "pupil";
  document.querySelectorAll(".pupil-name").forEach((n) => (n.textContent = state.pupil ? state.pupil.first_name : ""));
  window.scrollTo(0, 0);
  if (onEnter[id]) onEnter[id]();
}

document.addEventListener("click", (e) => {
  const target = e.target.closest("[data-go]");
  if (target) go(target.dataset.go);
});

// ---------- Home: model status from /health ----------

async function refreshStatus() {
  let text = "Not ready";
  let cls = "";
  try {
    const h = await api("/health");
    if (h.whisper_loaded && h.ollama_ready && h.ffmpeg_found && h.db_ok) {
      text = "Ready: all local AI loaded";
      cls = "ok";
    } else if (h.whisper_loaded && h.ffmpeg_found && h.db_ok) {
      text = "Reading check ready (Qwen not running: using backup questions and tips)";
      cls = "warn";
    } else {
      const missing = [];
      if (!h.whisper_loaded) missing.push("Whisper");
      if (!h.ffmpeg_found) missing.push("ffmpeg");
      if (!h.db_ok) missing.push("database");
      text = "Missing: " + missing.join(", ");
    }
  } catch {
    text = "Server not reachable";
  }
  [["#status-dot", "#status-text"], ["#status-dot-2", "#status-text-2"]].forEach(([d, t]) => {
    $(d).className = "dot " + cls;
    $(t).textContent = text;
  });
}
onEnter["home"] = refreshStatus;

// ---------- Pick Your Name ----------

onEnter["pick-name"] = async () => {
  const box = $("#name-tiles");
  box.textContent = "";
  const pupils = await api("/pupils");
  pupils.forEach((p) => {
    const tile = el("button", { class: "tile" }, p.class_no ? `${p.first_name} (${p.class_no})` : p.first_name);
    tile.appendChild(el("span", { class: "sub" }, `Grade ${p.grade}`));
    tile.addEventListener("click", () => { state.pupil = p; go("pick-story"); });
    box.appendChild(tile);
  });
};

// ---------- Pick a Story ----------

onEnter["pick-story"] = async () => {
  const box = $("#story-cards");
  box.textContent = "";
  const stories = await api("/stories");
  stories.forEach((s) => {
    const tile = el("button", { class: "tile" }, s.title);
    tile.appendChild(el("span", { class: "sub" }, `Grade ${s.grade_level}`));
    tile.addEventListener("click", async () => {
      state.story = await api(`/stories/${s.id}`);
      go("read-aloud");
    });
    box.appendChild(tile);
  });
};

// ---------- Microphone (MediaRecorder, records .webm in the browser) ----------
// The audio goes only to our own server on localhost, which deletes it after scoring.

const mic = {
  recorder: null,
  chunks: [],
  async start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const type = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
    this.chunks = [];
    this.recorder = new MediaRecorder(stream, { mimeType: type });
    this.recorder.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
    this.recorder.start();
  },
  stop() {
    return new Promise((resolve) => {
      if (!this.recorder) return resolve(null);
      this.recorder.onstop = () => {
        this.recorder.stream.getTracks().forEach((t) => t.stop()); // turn the mic off
        this.recorder = null;
        resolve(new Blob(this.chunks, { type: "audio/webm" }));
      };
      this.recorder.stop();
    });
  },
  cancel() { if (this.recorder) this.stop(); },
};

function micErrorText(err) {
  if (err && err.name === "NotAllowedError") return "Please ask your teacher to allow the microphone.";
  if (err && err.name === "NotFoundError") return "No microphone found. Please plug one in.";
  return "The microphone is not working. Please ask your teacher.";
}

// ---------- Read Aloud ----------

let timerId = null;
let startedAt = 0;

function resetReadAloud(message = "") {
  clearInterval(timerId);
  $("#read-btn").textContent = "Start";
  $("#read-btn").disabled = false;
  $("#read-btn").classList.remove("recording");
  $("#listening").classList.add("hidden");
  $("#timer").textContent = "0:00";
  $("#mic-error").textContent = message;
  $("#mic-error").classList.toggle("hidden", !message);
}

onEnter["read-aloud"] = () => {
  $("#story-title").textContent = state.story.title;
  $("#story-text").textContent = state.story.full_text;
  $("#placeholder-note").classList.toggle("hidden", !state.story.placeholder);
  resetReadAloud();
};

$("#read-back").addEventListener("click", () => { mic.cancel(); resetReadAloud(); go("pick-story"); });

$("#read-btn").addEventListener("click", async () => {
  const btn = $("#read-btn");
  if (btn.textContent === "Start") {
    try {
      await mic.start();
    } catch (err) {
      resetReadAloud(micErrorText(err));
      return;
    }
    startedAt = Date.now();
    timerId = setInterval(() => ($("#timer").textContent = formatTime((Date.now() - startedAt) / 1000)), 250);
    btn.textContent = "Done";
    btn.classList.add("recording");
    $("#listening").classList.remove("hidden");
    $("#mic-error").classList.add("hidden");
  } else {
    btn.disabled = true;
    clearInterval(timerId);
    const seconds = (Date.now() - startedAt) / 1000;
    const audio = await mic.stop();
    go("checking");
    await sendReading(audio, seconds);
  }
});

// ---------- Checking: POST /readings ----------

async function sendReading(audio, seconds) {
  const form = new FormData();
  form.append("pupil_id", state.pupil.id);
  form.append("story_id", state.story.id);
  form.append("seconds_taken", seconds.toFixed(1));
  form.append("audio", audio, "reading.webm");
  try {
    state.reading = await api("/readings", { method: "POST", body: form });
    go("my-result");
  } catch {
    go("read-aloud");
    resetReadAloud("Let's try again! Tap Start and read the story.");
  }
}

// ---------- My Result ----------

function kindMessage(correct, total) {
  const name = state.pupil.first_name;
  const ratio = total ? correct / total : 0;
  if (ratio >= 0.9) return `Great reading, ${name}!`;
  if (ratio >= 0.75) return `Good job, ${name}! Keep going!`;
  return `Nice try, ${name}! Let's practice together.`;
}

onEnter["my-result"] = () => {
  const r = state.reading;
  $("#result-message").textContent = kindMessage(r.words_correct, r.total_words);
  $("#result-score").textContent = `${r.words_correct} of ${r.total_words} words correct`;
  $("#result-time").textContent = `Time: ${formatTime(r.seconds_taken)}`;
  const box = $("#result-words");
  box.textContent = "";
  r.words.forEach((w) => {
    box.appendChild(el("span", { class: `w w-${w.status}` }, w.word));
    box.appendChild(document.createTextNode(" "));
  });
};
$("#result-next").addEventListener("click", () => go("story-quiz"));

// ---------- Story Quiz / Practice Again (stubbed in Step 3) ----------

onEnter["story-quiz"] = () => {
  $("#quiz-count").textContent = "";
  $("#quiz-question").textContent = "(Questions come in Step 3.)";
  $("#quiz-next").classList.remove("hidden");
};
$("#quiz-next").addEventListener("click", () => go("practice-again"));

onEnter["practice-again"] = () => {
  $("#practice-sentences").textContent = "(Practice sentences come in Step 3.)";
  $("#practice-next").classList.remove("hidden");
};
$("#practice-next").addEventListener("click", () => go("all-done"));

// ---------- Class View (filled in Step 3) ----------

onEnter["class-view"] = async () => {
  refreshStatus();
  const rows = $("#class-rows");
  rows.textContent = "";
  const pupils = await api("/pupils");
  pupils.forEach((p) => {
    const tr = el("tr");
    tr.appendChild(el("td", {}, p.first_name));
    ["–", "–", "–", "–", "–"].forEach((t) => tr.appendChild(el("td", {}, t)));
    rows.appendChild(tr);
  });
};

$("#add-pupil").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  await api("/pupils", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ first_name: form.get("first_name"), grade: Number(form.get("grade")) }),
  });
  e.target.reset();
  onEnter["class-view"]();
});

go("home");
