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
  $("#result-time").textContent = formatTime(r.seconds_taken);
  const box = $("#result-words");
  box.textContent = "";
  r.words.forEach((w) => {
    box.appendChild(el("span", { class: `w w-${w.status}` }, w.word));
    box.appendChild(document.createTextNode(" "));
  });
  loadQuiz(); // fetch questions now so Story Quiz opens without waiting
};
$("#result-next").addEventListener("click", () => go("story-quiz"));

// ---------- Record button helper (Story Quiz and Practice Again) ----------
// First tap starts the mic ("Done" appears), second tap stops it and calls onAudio(blob).

function recordButton(btn, listening, startLabel, onAudio) {
  btn.addEventListener("click", async () => {
    if (!btn.classList.contains("recording")) {
      try {
        await mic.start();
      } catch (err) {
        onAudio(null, micErrorText(err));
        return;
      }
      btn.textContent = "Done";
      btn.classList.add("recording");
      listening.classList.remove("hidden");
    } else {
      btn.disabled = true;
      btn.classList.remove("recording");
      listening.classList.add("hidden");
      btn.textContent = "Checking...";
      const audio = await mic.stop();
      await onAudio(audio);
      btn.textContent = startLabel;
      btn.disabled = false;
    }
  });
}

function showFeedback(node, text) {
  node.textContent = text;
  node.classList.remove("hidden");
}

// ---------- Story Quiz ----------
// Questions are fetched while My Result is showing, so they are usually ready.

const quiz = { questions: null, index: 0, loading: null };

function loadQuiz() {
  quiz.questions = null;
  quiz.index = 0;
  quiz.loading = api(`/quiz/${state.reading.reading_id}`)
    .then((q) => (quiz.questions = q.questions))
    .catch(() => (quiz.questions = []));
}

function hasPracticeWords() {
  return state.reading.words.some((w) => w.status === "red");
}

async function showQuestion() {
  $("#quiz-feedback").classList.add("hidden");
  $("#quiz-next").classList.add("hidden");
  $("#quiz-btn").classList.remove("hidden");
  if (!quiz.questions) {
    $("#quiz-question").textContent = "Getting your questions ready...";
    await quiz.loading;
  }
  if (!quiz.questions.length) return go(hasPracticeWords() ? "practice-again" : "all-done");
  const q = quiz.questions[quiz.index];
  $("#quiz-count").textContent = `${quiz.index + 1} of ${quiz.questions.length}`;
  $("#quiz-question").textContent = q.question;
}

onEnter["story-quiz"] = showQuestion;

recordButton($("#quiz-btn"), $("#quiz-listening"), "Answer", async (audio, error) => {
  if (!audio) return showFeedback($("#quiz-feedback"), error);
  const q = quiz.questions[quiz.index];
  const form = new FormData();
  form.append("reading_id", state.reading.reading_id);
  form.append("question", q.question);
  if (q.question_id) form.append("question_id", q.question_id);
  form.append("audio", audio, "answer.webm");
  try {
    const r = await api("/quiz/answer", { method: "POST", body: form });
    showFeedback($("#quiz-feedback"), r.message);
    $("#quiz-btn").classList.add("hidden");
    $("#quiz-next").classList.remove("hidden");
  } catch {
    showFeedback($("#quiz-feedback"), "Let's try again! Tap Answer and say it out loud.");
  }
});

$("#quiz-next").addEventListener("click", () => {
  quiz.index += 1;
  if (quiz.index < quiz.questions.length) showQuestion();
  else go(hasPracticeWords() ? "practice-again" : "all-done");
});

// ---------- Practice Again ----------

const practice = { id: null, targets: [] };

onEnter["practice-again"] = async () => {
  $("#practice-result").classList.add("hidden");
  $("#practice-next").classList.add("hidden");
  $("#practice-btn").classList.remove("hidden");
  const box = $("#practice-sentences");
  box.textContent = "Getting your practice words ready...";
  try {
    const p = await api("/practice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reading_id: state.reading.reading_id }),
    });
    practice.id = p.practice_id;
    practice.targets = p.target_words;
    box.textContent = "";
    p.sentences.forEach((s) => {
      const line = el("p");
      s.split(" ").forEach((word) => {
        const target = p.target_words.includes(word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, ""));
        line.appendChild(target ? el("span", { class: "w w-red" }, word) : document.createTextNode(word));
        line.appendChild(document.createTextNode(" "));
      });
      box.appendChild(line);
    });
  } catch {
    go("all-done");
  }
};

function wrongWords(n) {
  return `${n} wrong word${n === 1 ? "" : "s"}`;
}

recordButton($("#practice-btn"), $("#practice-listening"), "Start", async (audio, error) => {
  if (!audio) return showFeedback($("#practice-result"), error);
  const form = new FormData();
  form.append("audio", audio, "practice.webm");
  try {
    const r = await api(`/practice/${practice.id}/check`, { method: "POST", body: form });
    showFeedback($("#practice-result"), `Before: ${wrongWords(r.wrong_before)}. Now: ${wrongWords(r.wrong_after)}.`);
    $("#practice-btn").classList.add("hidden");
    $("#practice-next").classList.remove("hidden");
  } catch {
    showFeedback($("#practice-result"), "Let's try again! Tap Start and read the sentences.");
  }
});

$("#practice-next").addEventListener("click", () => go("all-done"));

// ---------- Teacher's Class View (with Heatmap) ----------

let classData = [];

function band(accuracy) {
  if (accuracy === null || accuracy === undefined) return "none";
  if (accuracy >= 0.9) return "good";
  if (accuracy >= 0.75) return "almost";
  return "help";
}

function renderClass() {
  const sort = $("#sort-select").value;
  const rows = [...classData];
  if (sort === "help") {
    // lowest score first; pupils with no reading yet go last
    rows.sort((a, b) => (a.latest_accuracy ?? 2) - (b.latest_accuracy ?? 2));
  } else {
    rows.sort((a, b) => (b.last_read_at || "").localeCompare(a.last_read_at || ""));
  }
  const newest = classData.reduce((best, p) => (p.last_read_at && (!best || p.last_read_at > best.last_read_at) ? p : best), null);

  const tbody = $("#class-rows");
  tbody.textContent = "";
  rows.forEach((p) => {
    const tr = el("tr", newest && p.id === newest.id ? { class: "newest" } : {});
    tr.appendChild(el("td", {}, p.class_no ? `${p.first_name} (${p.class_no})` : p.first_name));
    tr.appendChild(el("td", {}, p.latest_accuracy === null ? "–"
      : `${Math.round(p.latest_accuracy * 100)}% (${p.latest_words_correct}/${p.latest_total_words})`));
    tr.appendChild(el("td", {}, p.latest_seconds === null ? "–" : formatTime(p.latest_seconds)));
    tr.appendChild(el("td", {}, p.trouble_words.join(", ") || "–"));
    tr.appendChild(el("td", {}, p.tip || "–"));
    const heat = el("div", { class: "heat" });
    for (let i = 0; i < 5; i++) {
      const acc = p.last5[i];
      heat.appendChild(el("span", { class: `cell ${band(acc)}` }, acc === undefined ? "–" : String(Math.round(acc * 100))));
    }
    const td = el("td");
    td.appendChild(heat);
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
}

onEnter["class-view"] = async () => {
  refreshStatus();
  classData = await api("/teacher/class");
  renderClass();
};

$("#sort-select").addEventListener("change", renderClass);

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
