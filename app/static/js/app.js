const form = document.querySelector("#start-form");
const panel = document.querySelector("#interview-panel");
const questionEl = document.querySelector("#question");
const timerEl = document.querySelector("#timer");

let timerId = null;
let seconds = 0;

function startTimer() {
  clearInterval(timerId);
  seconds = 0;
  timerId = setInterval(() => {
    seconds += 1;
    const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
    const rest = String(seconds % 60).padStart(2, "0");
    timerEl.textContent = `${minutes}:${rest}`;
  }, 1000);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const response = await fetch("/api/interviews/start", {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  questionEl.textContent = data.question;
  panel.classList.remove("hidden");
  startTimer();
});
