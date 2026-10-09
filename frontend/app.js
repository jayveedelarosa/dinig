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

// Pupil steps shown in the top bar as "Step X of 8"
const STEPS = ["pick-name", "pick-story", "read-aloud", "checking", "my-result", "story-quiz", "practice-again", "all-done"];

function updateTopbar(id) {
  $("#topbar").classList.toggle("hidden", id === "home"); // Home has its own top bar
  const step = STEPS.indexOf(id) + 1;
  $("#stepper").classList.toggle("invisible", step === 0); // no stepper on Class View
  if (step) {
    $("#stepper-text").textContent = `Step ${step} of ${STEPS.length}`;
    $("#stepper-fill").style.width = `${(step / STEPS.length) * 100}%`;
  }
}

function go(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("active", s.id === id));
  document.body.className = TEACHER_SCREENS.includes(id) ? "teacher" : "pupil";
  updateTopbar(id);
  document.querySelectorAll(".pupil-name").forEach((n) => (n.textContent = state.pupil ? state.pupil.first_name : ""));
  document.querySelectorAll(".story-name").forEach((n) => (n.textContent = state.story ? state.story.title : ""));
  window.scrollTo(0, 0);
  if (onEnter[id]) onEnter[id]();
}

document.addEventListener("click", (e) => {
  const target = e.target.closest("[data-go]");
  if (target) go(target.dataset.go);
});

// Logo in the top bar: stop any recording, then go Home
$("#brand-home").addEventListener("click", () => { mic.cancel(); resetReadAloud(); go("home"); });

// ---------- Light / dark theme ----------
// Light on every start. Dark only while the toggle is on; it is never saved.
// The class goes on <html> because go() replaces the <body> class.

document.querySelectorAll(".theme-toggle").forEach((btn) => btn.addEventListener("click", () => {
  const dark = document.documentElement.classList.toggle("theme-dark");
  document.querySelectorAll(".theme-toggle").forEach((b) => {
    b.querySelector(".theme-label").textContent = dark ? "Light" : "Dark";
    b.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  });
}));

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
  // Top bar pill: short status always visible, full text on hover
  $("#topbar-dot").className = "dot " + cls;
  $("#topbar-status").textContent = cls === "ok" ? "AI ready" : cls === "warn" ? "Backup mode" : "Not ready";
  $("#topbar-pill").className = "offline-pill " + (cls || "off");
  $("#topbar-pill").title = text;
}
onEnter["home"] = refreshStatus;

// ---------- Pick Your Name ----------

onEnter["pick-name"] = async () => {
  const box = $("#name-tiles");
  box.textContent = "";
  const pupils = await api("/pupils");
  pupils.forEach((p, i) => {
    // Colored initial badge (6 colors in turn), name, then grade and class number
    const tile = el("button", { class: `name-tile name-${(i % 6) + 1}`, type: "button" });
    tile.appendChild(el("span", { class: "name-initial", "aria-hidden": "true" }, initials(p.first_name)));
    const text = el("span", { class: "name-text" });
    text.appendChild(el("strong", {}, p.first_name));
    text.appendChild(el("small", {}, p.class_no ? `Grade ${p.grade} · No. ${p.class_no}` : `Grade ${p.grade}`));
    tile.appendChild(text);
    tile.addEventListener("click", () => { state.pupil = p; go("pick-story"); });
    box.appendChild(tile);
  });
};

function initials(name) {
  return /^\d/.test(name) ? name.slice(0, 2) : name.charAt(0).toUpperCase(); // class numbers keep their digits
}

// ---------- Pick a Story ----------

onEnter["pick-story"] = async () => {
  const box = $("#story-cards");
  box.textContent = "";
  const stories = await api("/stories");
  const covers = ["meadow", "seed", "rain"]; // the designer's three cover colors, in turn
  stories.forEach((s, i) => {
    const tile = el("button", { class: "story-choice-card", type: "button" });
    tile.innerHTML = `<span class="story-art story-art-${covers[i % 3]}"><svg class="icon icon-xl"><use href="#i-book"/></svg><i></i></span>`;
    const copy = el("span", { class: "story-card-copy" });
    copy.appendChild(el("small", {}, `Grade ${s.grade_level}`));
    copy.appendChild(el("strong", {}, s.title));
    tile.appendChild(copy);
    const arrow = el("span", { class: "story-go" });
    arrow.innerHTML = `<svg class="icon"><use href="#i-arrow"/></svg>`;
    tile.appendChild(arrow);
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

const quiz = { questions: null, index: 0, loading: null, answered: 0 };

function loadQuiz() {
  quiz.questions = null;
  quiz.index = 0;
  quiz.answered = 0; // shown on All Done
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
  $("#quiz-number").textContent = quiz.index + 1;
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
    quiz.answered += 1;
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

// Pupil mode never says "wrong" (docs/BRAND.md): missed words are "practice words"
function wrongWords(n) {
  return `${n} practice word${n === 1 ? "" : "s"}`;
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

// ---------- All Done ----------

onEnter["all-done"] = () => {
  const r = state.reading;
  $("#done-words").textContent = r ? `${r.words_correct} / ${r.total_words}` : "–";
  $("#done-quiz").textContent = quiz.questions && quiz.questions.length ? `${quiz.answered} / ${quiz.questions.length}` : "–";
};

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

  // Summary strip: pupils, average of each pupil's latest reading, and how many are below 75%
  const read = classData.filter((p) => p.latest_accuracy !== null);
  $("#sum-pupils").textContent = classData.length;
  $("#sum-average").textContent = read.length
    ? `${Math.round((read.reduce((sum, p) => sum + p.latest_accuracy, 0) / read.length) * 100)}%` : "–";
  $("#sum-help").textContent = read.filter((p) => band(p.latest_accuracy) === "help").length;

  const tbody = $("#class-rows");
  tbody.textContent = "";
  rows.forEach((p) => {
    const tr = el("tr", newest && p.id === newest.id ? { class: "newest" } : {});

    // Same initial-badge colors as Pick Your Name (color kept per pupil, whatever the sort)
    const td1 = el("td");
    const who = el("div", { class: `pupil-cell name-${(classData.indexOf(p) % 6) + 1}` });
    who.appendChild(el("span", { class: "name-initial table-initial", "aria-hidden": "true" }, initials(p.first_name)));
    who.appendChild(el("strong", {}, p.first_name));
    if (p.class_no) who.appendChild(el("small", {}, `No. ${p.class_no}`));
    if (tr.className === "newest") who.appendChild(el("span", { class: "new-tag" }, "NEW"));
    td1.appendChild(who);
    tr.appendChild(td1);

    tr.appendChild(el("td", { class: "score-cell" }, p.latest_accuracy === null ? "–"
      : `${Math.round(p.latest_accuracy * 100)}% (${p.latest_words_correct}/${p.latest_total_words})`));
    tr.appendChild(el("td", {}, p.latest_seconds === null ? "–" : formatTime(p.latest_seconds)));
    tr.appendChild(el("td", {}, p.trouble_words.join(", ") || "–"));
    tr.appendChild(el("td", { class: "tip-cell" }, p.tip || "–"));

    const support = el("td");
    support.appendChild(el("span", { class: `support-label ${band(p.latest_accuracy)}` }, SUPPORT[band(p.latest_accuracy)]));
    tr.appendChild(support);

    // Heatmap: blanks on the left (oldest side), so the newest reading is always the last cell
    const heat = el("div", { class: "heat" });
    const cells = [...Array(5 - p.last5.length).fill(undefined), ...p.last5];
    cells.forEach((acc) => {
      heat.appendChild(el("span", { class: `cell ${band(acc)}` }, acc === undefined ? "–" : String(Math.round(acc * 100))));
    });
    const td = el("td");
    td.appendChild(heat);
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
}

const SUPPORT = { good: "On track", almost: "Keep an eye", help: "Needs help", none: "No reading yet" };

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
