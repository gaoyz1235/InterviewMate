const form = document.querySelector("#start-form");
const startPanel = document.querySelector("#start-panel");
const interviewFields = document.querySelector("#interview-fields");
const projectDrillFields = document.querySelector("#project-drill-fields");
const questionFocus = document.querySelector("#question-focus");
const customFocusLabel = document.querySelector("#custom-focus-label");
const interviewPanel = document.querySelector("#interview-panel");
const resultPanel = document.querySelector("#result-panel");
const startButton = document.querySelector("#start-button");
const startError = document.querySelector("#start-error");
const messagesEl = document.querySelector("#messages");
const questionTypeEl = document.querySelector("#question-type");
const progressEl = document.querySelector("#progress");
const timerEl = document.querySelector("#timer");
const answerEl = document.querySelector("#answer");
const submitAnswerButton = document.querySelector("#submit-answer");
const finishNowButton = document.querySelector("#finish-now");
const restartButton = document.querySelector("#restart");

let sessionId = null;
let currentQuestion = null;
let currentMode = "interview";
let timerId = null;
let seconds = 0;
const maxSeconds = 180;

function startTimer() {
  clearInterval(timerId);
  seconds = 0;
  renderTimer();
  timerId = setInterval(() => {
    seconds += 1;
    renderTimer();
    if (seconds >= maxSeconds) {
      clearInterval(timerId);
      timerEl.classList.add("danger");
    }
  }, 1000);
}

function renderTimer() {
  const remaining = Math.max(maxSeconds - seconds, 0);
  const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
  const rest = String(remaining % 60).padStart(2, "0");
  timerEl.textContent = `${minutes}:${rest}`;
  timerEl.classList.toggle("warning", remaining <= 30 && remaining > 0);
}

function showQuestion(question, progress) {
  currentQuestion = question;
  questionTypeEl.textContent = question.question_type;
  progressEl.textContent = progress;
  appendMessage("assistant", question.question, question.question_type);
  answerEl.value = "";
  answerEl.focus();
  timerEl.classList.remove("warning", "danger");
  startTimer();
}

function appendMessage(role, content, meta = "") {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  const labelMap = {
    assistant: "AI 面试官",
    user: "我的回答",
    system: "流程提示",
  };
  item.innerHTML = `
    <div class="message-meta">${labelMap[role] || "系统"}${meta ? ` · ${meta}` : ""}</div>
    <div class="message-content"></div>
  `;
  item.querySelector(".message-content").textContent = content;
  messagesEl.appendChild(item);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "请求失败，请稍后重试。");
  }
  return data;
}

function getSelectedMode() {
  const selected = form.querySelector('input[name="mode"]:checked');
  return selected ? selected.value : "interview";
}

function updateModeFields() {
  const mode = getSelectedMode();
  interviewFields.classList.toggle("hidden", mode !== "interview");
  projectDrillFields.classList.toggle("hidden", mode !== "project_drill");
}

function updateCustomFocusField() {
  customFocusLabel.classList.toggle("hidden", questionFocus.value !== "自定义");
}

form.querySelectorAll('input[name="mode"]').forEach((input) => {
  input.addEventListener("change", updateModeFields);
});

questionFocus.addEventListener("change", updateCustomFocusField);
updateModeFields();
updateCustomFocusField();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  startError.textContent = "";
  startButton.disabled = true;
  try {
    const formData = new FormData(form);
    currentMode = getSelectedMode();
    const startUrl = currentMode === "project_drill" ? "/api/project-drills/start" : "/api/interviews/start";
    const data = await fetchJson(startUrl, {
      method: "POST",
      body: formData,
    });
    sessionId = data.session_id;
    messagesEl.innerHTML = "";
    startPanel.classList.add("hidden");
    resultPanel.classList.add("hidden");
    interviewPanel.classList.remove("hidden");
    showQuestion(data.question, data.progress);
  } catch (error) {
    startError.textContent = error.message;
  } finally {
    startButton.disabled = false;
  }
});

submitAnswerButton.addEventListener("click", async () => {
  const answer = answerEl.value.trim();
  if (!answer || !sessionId || !currentQuestion) {
    return;
  }

  clearInterval(timerId);
  submitAnswerButton.disabled = true;
  appendMessage("user", answer, `耗时 ${seconds} 秒`);
  answerEl.value = "";
  answerEl.disabled = true;
  try {
    const baseUrl = currentMode === "project_drill" ? "/api/project-drills" : "/api/interviews";
    const data = await fetchJson(`${baseUrl}/${sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question_id: currentQuestion.question_id,
        answer,
        elapsed_seconds: seconds,
      }),
    });
    if (data.action === "finish") {
      await renderSummary();
      return;
    }
    if (data.action === "continue") {
      appendMessage("system", "上一轮追问结束，进入下一道面试题。", data.progress);
    }
    showQuestion(data.question, data.progress);
  } catch (error) {
    appendMessage("assistant", error.message);
    answerEl.value = answer;
  } finally {
    submitAnswerButton.disabled = false;
    answerEl.disabled = false;
  }
});

finishNowButton.addEventListener("click", renderSummary);

restartButton.addEventListener("click", () => {
  clearInterval(timerId);
  sessionId = null;
  currentQuestion = null;
  currentMode = "interview";
  form.reset();
  updateModeFields();
  updateCustomFocusField();
  resultPanel.classList.add("hidden");
  interviewPanel.classList.add("hidden");
  startPanel.classList.remove("hidden");
});

async function renderSummary() {
  if (!sessionId) {
    return;
  }
  clearInterval(timerId);
  const baseUrl = currentMode === "project_drill" ? "/api/project-drills" : "/api/interviews";
  const summary = await fetchJson(`${baseUrl}/${sessionId}/finish`, { method: "POST" });
  interviewPanel.classList.add("hidden");
  resultPanel.classList.remove("hidden");
  document.querySelector("#total-score").textContent = `${summary.total_score}/100`;
  renderScores(summary.scores);
  renderList("#problem-list", summary.exposed_problems);
  renderList("#resume-suggestion-list", summary.resume_suggestions);
  renderList("#practice-suggestion-list", summary.practice_suggestions);
  renderTranscript(summary.transcript);
}

function renderScores(scores) {
  const scoreList = document.querySelector("#score-list");
  scoreList.innerHTML = "";
  scores.forEach((score) => {
    const card = document.createElement("article");
    card.className = "score-card";
    card.innerHTML = `<strong>${score.name}: ${score.score}/25</strong><p></p>`;
    card.querySelector("p").textContent = score.comment;
    scoreList.appendChild(card);
  });
}

function renderList(selector, items) {
  const list = document.querySelector(selector);
  list.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

function renderTranscript(transcript) {
  const transcriptEl = document.querySelector("#transcript");
  transcriptEl.innerHTML = "";
  transcript.forEach((item) => {
    appendTranscriptItem(transcriptEl, item);
  });
}

function appendTranscriptItem(parent, item) {
  const div = document.createElement("div");
  div.className = `message ${item.role}`;
  const elapsed = item.elapsed_seconds === null || item.elapsed_seconds === undefined ? "" : ` · ${item.elapsed_seconds} 秒`;
  div.innerHTML = `<div class="message-meta">${item.role === "assistant" ? "AI 面试官" : "我的回答"}${elapsed}</div><div class="message-content"></div>`;
  div.querySelector(".message-content").textContent = item.content;
  parent.appendChild(div);
}
