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
  if (!res.ok) {
    const err = new Error(`${path} failed: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// 503 = the server is up but Whisper (speech to text) is not loaded, so retrying won't help.
function retryText(err, retry) {
  if (err && err.status === 503) return "Dindin can't listen yet. Please ask your teacher to check the setup.";
  return retry;
}

function el(tag, attrs = {}, text = "") {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  if (text) node.textContent = text;
  return node;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatLongTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m} min ${String(s).padStart(2, "0")} sec`;
}

function initials(name) {
  return name.split(/\s+/).filter(Boolean).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
}

// Line icons from the Figma design (24x24, stroke = currentColor)
const ICON_PATHS = {
  arrow: '<path d="m9 18 6-6-6-6"/>',
  book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5z"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  mic: '<rect x="8" y="3" width="8" height="12" rx="4"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  sparkles: '<path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2z"/><path d="m19 14 .7 2.3L22 17l-2.3.7L19 20l-.7-2.3L16 17l2.3-.7z"/>',
};

function icon(name, size = 20) {
  return `<svg aria-hidden="true" class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none"><g stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2">${ICON_PATHS[name]}</g></svg>`;
}

// Sets a button's look: label, optional icon (before or after), and color.
function setButton(btn, label, { iconName = null, after = false, color = "blue" } = {}) {
  const i = iconName ? icon(iconName) : "";
  btn.innerHTML = after ? `${escapeHtml(label)}${i}` : `${i}${escapeHtml(label)}`;
  btn.classList.toggle("btn-blue", color === "blue");
  btn.classList.toggle("btn-green", color === "green");
}

function setMood(node, mood) {
  if (!node) return;
  node.className = node.className.replace(/\bdindin-(encouraging|waving|celebrating|thinking|retry|reading)\b/g, "").trim();
  node.classList.add(`dindin-${mood}`);
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
  if (!target) return;
  e.preventDefault();
  if (target.dataset.go === "home") mic.cancel();
  go(target.dataset.go);
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
  // More than 9 pupils: compact tiles so a full class (40) fits on one screen
  const compact = pupils.length > 9;
  box.classList.toggle("tiles", compact);
  pupils.forEach((p, idx) => {
    const tile = el("button", { class: `name-tile name-${(idx % 6) + 1}${compact ? " tile" : ""}`, type: "button" });
    const sub = p.class_no ? `No. ${p.class_no} · Grade ${p.grade}` : `Grade ${p.grade}`;
    tile.innerHTML = `<span>${escapeHtml(initials(p.first_name))}</span>` +
      `<strong>${escapeHtml(p.first_name)}<small>${escapeHtml(sub)}</small></strong>${icon("arrow", 22)}`;
    tile.addEventListener("click", () => { state.pupil = p; go("pick-story"); });
    box.appendChild(tile);
  });
};

// ---------- Pick a Story ----------

const STORY_ART = ["meadow", "seed", "rain"];
const LANGUAGES = { en: "English", fil: "Filipino" };

onEnter["pick-story"] = async () => {
  const box = $("#story-cards");
  box.textContent = "";
  const stories = await api("/stories");
  stories.forEach((s, idx) => {
    const tile = el("button", { class: "story-choice-card", type: "button" });
    tile.innerHTML = `
      <span class="story-art story-art-${STORY_ART[idx % STORY_ART.length]}">${icon("book", 42)}<i></i></span>
      <span class="story-card-copy">
        <small>Grade ${escapeHtml(s.grade_level)}</small>
        <strong>${escapeHtml(s.title)}</strong>
        <span>${escapeHtml(LANGUAGES[s.language] || s.language || "")}</span>
      </span>
      <span class="story-go">${icon("arrow", 22)}</span>`;
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
  const btn = $("#read-btn");
  setButton(btn, "Start", { iconName: "mic", color: "blue" });
  btn.disabled = false;
  btn.classList.remove("recording");
  $("#timer").textContent = "0:00";
  $("#read-help-main").innerHTML = `Ready, <span class="pupil-name">${escapeHtml(state.pupil?.first_name || "")}</span>?`;
  $("#read-prompt-main").textContent = "Read when you're ready.";
  $("#read-prompt-sub").textContent = "The words will be checked after you finish.";
  $("#mic-error").textContent = message;
  $("#mic-error").classList.toggle("hidden", !message);
}

onEnter["read-aloud"] = () => {
  $("#story-title").textContent = state.story.title;
  $("#story-text").textContent = state.story.full_text;
  $("#placeholder-note").classList.toggle("hidden", !state.story.placeholder);
  resetReadAloud();
  api("/health").then((h) => {
    if (h.whisper_loaded) return;
    resetReadAloud(retryText({ status: 503 }));
    $("#read-btn").disabled = true;
  }).catch(() => {});
};

$("#read-back").addEventListener("click", () => { mic.cancel(); resetReadAloud(); go("pick-story"); });

$("#read-btn").addEventListener("click", async () => {
  const btn = $("#read-btn");
  if (!btn.classList.contains("recording")) {
    try {
      await mic.start();
    } catch (err) {
      resetReadAloud(micErrorText(err));
      return;
    }
    startedAt = Date.now();
    timerId = setInterval(() => ($("#timer").textContent = formatTime((Date.now() - startedAt) / 1000)), 250);
    btn.classList.add("recording");
    setButton(btn, "Done", { iconName: "check", color: "green" });
    $("#read-help-main").textContent = "Dindin is listening";
    $("#read-prompt-main").textContent = "Take your time.";
    $("#read-prompt-sub").textContent = "Tap Done only when you finish the whole story.";
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
  } catch (err) {
    go("read-aloud");
    resetReadAloud(retryText(err, "Let's try again! Tap Start and read the story."));
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

const WORD_CLASS = { green: "correct-word", red: "practice-word", grey: "skipped-word" };

onEnter["my-result"] = () => {
  const r = state.reading;
  $("#result-score").textContent = `${r.words_correct} of ${r.total_words} words correct`;
  $("#result-message").textContent = "Nice reading! Here is what Dindin heard.";
  $("#result-cheer").textContent = kindMessage(r.words_correct, r.total_words);
  $("#result-time").textContent = formatLongTime(r.seconds_taken);
  const box = $("#result-words");
  box.textContent = "";
  r.words.forEach((w) => {
    box.appendChild(el("span", { class: WORD_CLASS[w.status] || "skipped-word" }, w.word));
  });
  $("#done-score").textContent = `${r.words_correct} / ${r.total_words}`;
  loadQuiz(); // fetch questions now so Story Quiz opens without waiting
};
$("#result-next").addEventListener("click", () => go("story-quiz"));

// ---------- Record button helper (Story Quiz and Practice Again) ----------
// First tap starts the mic ("Done" appears), second tap stops it and calls onAudio(blob).

function recordButton(btn, labels, hooks) {
  btn.addEventListener("click", async () => {
    if (!btn.classList.contains("recording")) {
      try {
        await mic.start();
      } catch (err) {
        hooks.onAudio(null, micErrorText(err));
        return;
      }
      btn.classList.add("recording");
      setButton(btn, labels.done, { iconName: "check", color: "green" });
      hooks.onListen();
    } else {
      btn.disabled = true;
      btn.classList.remove("recording");
      setButton(btn, "Checking...", { color: "green" });
      const audio = await mic.stop();
      await hooks.onAudio(audio);
      setButton(btn, labels.start, { iconName: "mic", color: "blue" });
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
  quiz.answered = 0;
  quiz.loading = api(`/quiz/${state.reading.reading_id}`)
    .then((q) => (quiz.questions = q.questions))
    .catch(() => (quiz.questions = []));
}

function hasPracticeWords() {
  return state.reading.words.some((w) => w.status === "red");
}

function setVoiceBox(mode, main, sub) {
  const box = $("#voice-box");
  box.classList.toggle("is-answered", mode === "answered");
  box.classList.toggle("is-listening", mode === "listening");
  $("#voice-icon").innerHTML = icon(mode === "answered" ? "check" : "mic", 22);
  $("#voice-main").textContent = main;
  $("#voice-sub").textContent = sub;
}

function finishQuiz() {
  const total = quiz.questions ? quiz.questions.length : 0;
  $("#done-quiz").textContent = total ? `${quiz.answered} / ${total}` : "–";
  go(hasPracticeWords() ? "practice-again" : "all-done");
}

async function showQuestion() {
  $("#quiz-feedback").classList.add("hidden");
  $("#quiz-next").classList.add("hidden");
  $("#quiz-btn").classList.remove("hidden");
  setMood($("#quiz-mascot"), "thinking");
  $("#quiz-mascot-msg").textContent = "I'm listening.";
  setVoiceBox("idle", "Tap Answer, then say it out loud.", "Speak clearly when you're ready.");
  if (!quiz.questions) {
    $("#quiz-question").textContent = "Getting your questions ready...";
    await quiz.loading;
  }
  if (!quiz.questions.length) return finishQuiz();
  const q = quiz.questions[quiz.index];
  const n = quiz.questions.length;
  $("#quiz-eyebrow").textContent = `${state.story.title} · Question ${quiz.index + 1} of ${n}`;
  $("#quiz-num").textContent = quiz.index + 1;
  $("#quiz-question").textContent = q.question;
  $("#quiz-next-label").textContent = quiz.index + 1 < n ? "Next question" : hasPracticeWords() ? "Practice words" : "All done";
}

onEnter["story-quiz"] = showQuestion;

recordButton($("#quiz-btn"), { start: "Answer", done: "I've answered" }, {
  onListen: () => setVoiceBox("listening", "Listening for your answer...", "Tap \u201cI've answered\u201d when you finish."),
  onAudio: async (audio, error) => {
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
      setVoiceBox("answered", "Dindin heard you.", "Your answer stays on this laptop.");
      $("#quiz-feedback").innerHTML = `${icon("sparkles")}<span>${escapeHtml(r.message)}</span>`;
      $("#quiz-feedback").classList.remove("hidden");
      setMood($("#quiz-mascot"), "encouraging");
      $("#quiz-mascot-msg").textContent = "Wonderful!";
      $("#quiz-btn").classList.add("hidden");
      $("#quiz-next").classList.remove("hidden");
    } catch (err) {
      setVoiceBox("idle", "Let's try again!", retryText(err, "Tap Answer and say it out loud."));
    }
  },
});

$("#quiz-next").addEventListener("click", () => {
  quiz.index += 1;
  if (quiz.index < quiz.questions.length) showQuestion();
  else finishQuiz();
});

// ---------- Practice Again ----------

const practice = { id: null, targets: [] };

onEnter["practice-again"] = async () => {
  $("#practice-result").classList.add("hidden");
  $("#practice-result-box").classList.add("hidden");
  $("#practice-next").classList.add("hidden");
  $("#practice-listening").classList.add("hidden");
  $("#practice-btn").classList.remove("hidden");
  setMood($("#practice-mascot"), "retry");
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
      s.split(" ").forEach((word, i) => {
        if (i) line.appendChild(document.createTextNode(" "));
        const target = p.target_words.includes(word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, ""));
        line.appendChild(target ? el("mark", {}, word) : document.createTextNode(word));
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

recordButton($("#practice-btn"), { start: "Start reading", done: "Done" }, {
  onListen: () => {
    $("#practice-listening").classList.remove("hidden");
    $("#practice-result").classList.add("hidden");
  },
  onAudio: async (audio, error) => {
    $("#practice-listening").classList.add("hidden");
    if (!audio) return showFeedback($("#practice-result"), error);
    const form = new FormData();
    form.append("audio", audio, "practice.webm");
    try {
      const r = await api(`/practice/${practice.id}/check`, { method: "POST", body: form });
      $("#practice-before").textContent = wrongWords(r.wrong_before);
      $("#practice-after").textContent = wrongWords(r.wrong_after);
      $("#practice-result-box").classList.remove("hidden");
      setMood($("#practice-mascot"), r.wrong_after < r.wrong_before ? "celebrating" : "encouraging");
      $("#practice-btn").classList.add("hidden");
      $("#practice-next").classList.remove("hidden");
    } catch (err) {
      showFeedback($("#practice-result"), retryText(err, "Let's try again! Tap Start reading and read the sentences."));
    }
  },
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

const SUPPORT = {
  good: ["On track", ""],
  almost: ["Keep an eye", "keep-eye"],
  help: ["Needs help", "needs-help"],
  none: ["No reading yet", "no-reading"],
};

function renderSummary() {
  const read = classData.filter((p) => p.latest_accuracy !== null && p.latest_accuracy !== undefined);
  $("#sum-pupils").textContent = classData.length;
  $("#sum-average").textContent = read.length
    ? `${Math.round((read.reduce((sum, p) => sum + p.latest_accuracy, 0) / read.length) * 100)}%`
    : "–";
  $("#sum-help").textContent = read.filter((p) => band(p.latest_accuracy) === "help").length;
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
  rows.forEach((p, idx) => {
    const isNewest = newest && p.id === newest.id;
    const tr = el("tr", isNewest ? { class: "newest" } : {});

    const nameTd = el("td");
    const nameCell = el("div", { class: "pupil-cell" });
    nameCell.appendChild(el("span", { class: `table-initial initial-${(idx % 6) + 1}` }, initials(p.first_name)));
    nameCell.appendChild(el("strong", {}, p.class_no ? `${p.first_name} (${p.class_no})` : p.first_name));
    if (isNewest) nameCell.appendChild(el("span", { class: "new-tag" }, "NEW"));
    nameTd.appendChild(nameCell);
    tr.appendChild(nameTd);

    const scoreTd = el("td");
    scoreTd.appendChild(el("strong", {}, p.latest_accuracy === null ? "–"
      : `${p.latest_words_correct} of ${p.latest_total_words} (${Math.round(p.latest_accuracy * 100)}%)`));
    tr.appendChild(scoreTd);
    tr.appendChild(el("td", {}, p.latest_seconds === null ? "–" : formatTime(p.latest_seconds)));
    tr.appendChild(el("td", {}, p.trouble_words.join(", ") || "–"));

    const [supportText, supportClass] = SUPPORT[band(p.latest_accuracy)];
    const supportTd = el("td");
    supportTd.appendChild(el("span", { class: `support-label ${supportClass}`.trim() }, supportText));
    tr.appendChild(supportTd);

    tr.appendChild(el("td", { class: "tip-cell" }, p.tip || "–"));

    const heat = el("div", { class: "heat" });
    // Left-pad with undefined so blank "–" cells appear on the left (oldest side),
    // keeping the newest reading always in the rightmost (last) cell.
    const padded = Array(5 - p.last5.length).fill(undefined).concat(p.last5);
    for (let i = 0; i < 5; i++) {
      const acc = padded[i];
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
  renderSummary();
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
