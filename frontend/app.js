const elements = {
  connectionStatus: document.querySelector("#connectionStatus"),
  connectionLabel: document.querySelector("#connectionLabel"),
  conversation: document.querySelector("#conversation"),
  errorMessage: document.querySelector("#errorMessage"),
  form: document.querySelector("#messageForm"),
  input: document.querySelector("#messageInput"),
  resetButton: document.querySelector("#resetButton"),
  sendButton: document.querySelector("#sendButton"),
  stageBusy: document.querySelector("#stageBusy"),
  stageContent: document.querySelector("#stageContent"),
  stageTitle: document.querySelector("#stageTitle"),
};

const SESSION_STORAGE_KEY = "spatial-classroom-session-id";
let sessionId = getOrCreateSessionId();
let isBusy = false;
let hasPendingAction = false;

function getOrCreateSessionId() {
  const saved = localStorage.getItem(SESSION_STORAGE_KEY);
  if (saved) return saved;

  const id = globalThis.crypto?.randomUUID?.() ?? `session-${Date.now()}`;
  localStorage.setItem(SESSION_STORAGE_KEY, id);
  return id;
}

function setBusy(value, showOverlay = value) {
  isBusy = value;
  elements.stageBusy.hidden = !(value && showOverlay);
  elements.input.disabled = value || hasPendingAction;
  elements.sendButton.disabled = value || hasPendingAction;
  elements.resetButton.disabled = value;
}

function setConnection(status, label) {
  elements.connectionStatus.className = `status-pill ${status}`.trim();
  elements.connectionLabel.textContent = label;
}

function showError(message) {
  elements.errorMessage.textContent = message;
  elements.errorMessage.hidden = false;
}

function clearError() {
  elements.errorMessage.hidden = true;
  elements.errorMessage.textContent = "";
}

function addMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}-message`;

  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "teacher" ? "Teacher" : "Student";

  const content = document.createElement("p");
  content.textContent = text;

  article.append(label, content);
  elements.conversation.append(article);
  elements.conversation.scrollTop = elements.conversation.scrollHeight;
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // Keep the status-based fallback for non-JSON server errors.
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

async function checkConnection() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("AI Core is unavailable");
    const health = await response.json();
    setConnection("connected", `Ready · ${health.provider}`);
  } catch {
    setConnection("error", "Offline");
    showError("Cannot reach AI Core. Make sure the FastAPI server is running.");
  }
}

async function sendStudentMessage(message) {
  if (isBusy) return;

  clearError();
  addMessage("student", message);
  setBusy(true);

  try {
    const output = await apiRequest(
      `/v1/sessions/${encodeURIComponent(sessionId)}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
    );
    await handleAgentOutput(output);
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
    elements.input.focus();
  }
}

async function submitActionResult(callId, result) {
  return apiRequest(
    `/v1/sessions/${encodeURIComponent(sessionId)}/actions/${encodeURIComponent(callId)}/result`,
    {
      method: "POST",
      body: JSON.stringify({ result }),
    },
  );
}

async function handleAgentOutput(output) {
  if (output.type === "speech") {
    addMessage("teacher", output.speech);
    return;
  }

  if (output.type !== "action" || !output.action) {
    throw new Error("AI Core returned an unsupported response.");
  }

  const { call_id: callId, type, payload } = output.action;
  hasPendingAction = true;

  if (type === "ui.show_image") {
    const success = await renderImage(payload);
    const feedback = await submitActionResult(callId, { success });
    hasPendingAction = false;
    await handleAgentOutput(feedback);
    return;
  }

  if (type === "ui.show_choices") {
    setBusy(false, false);
    const selected = await renderChoices(payload);
    addMessage("student", selected);
    setBusy(true);
    const feedback = await submitActionResult(callId, { selected });
    hasPendingAction = false;
    await handleAgentOutput(feedback);
    return;
  }

  throw new Error(`Unsupported classroom action: ${type}`);
}

function renderImage(payload) {
  elements.stageTitle.textContent = payload.caption;
  elements.stageContent.innerHTML = "";

  const card = document.createElement("div");
  card.className = "image-card";

  const frame = document.createElement("div");
  frame.className = "image-frame";

  const image = document.createElement("img");
  image.src = payload.image_url;
  image.alt = payload.caption;

  const caption = document.createElement("p");
  caption.className = "image-caption";
  caption.textContent = payload.caption;

  frame.append(image);
  card.append(frame, caption);
  elements.stageContent.append(card);

  return new Promise((resolve) => {
    image.addEventListener("load", () => resolve(true), { once: true });
    image.addEventListener("error", () => resolve(false), { once: true });
  });
}

function renderChoices(payload) {
  elements.stageTitle.textContent = "Choose your answer";
  elements.stageContent.innerHTML = "";

  const card = document.createElement("div");
  card.className = "choice-card";

  const question = document.createElement("h2");
  question.textContent = payload.question;

  const choices = document.createElement("div");
  choices.className = "choices-grid";

  card.append(question, choices);
  elements.stageContent.append(card);

  return new Promise((resolve) => {
    payload.choices.forEach((choice) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "choice-button";
      button.textContent = choice;
      button.addEventListener(
        "click",
        () => {
          choices.querySelectorAll("button").forEach((item) => {
            item.disabled = true;
          });
          button.classList.add("selected");
          resolve(choice);
        },
        { once: true },
      );
      choices.append(button);
    });
  });
}

async function resetLesson() {
  if (isBusy) return;
  clearError();
  setBusy(true);

  try {
    await apiRequest(`/v1/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    localStorage.removeItem(SESSION_STORAGE_KEY);
    sessionId = getOrCreateSessionId();
    window.location.reload();
  } catch (error) {
    showError(error.message);
    setBusy(false);
  }
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = elements.input.value.trim();
  if (!message) return;
  elements.input.value = "";
  sendStudentMessage(message);
});

elements.resetButton.addEventListener("click", resetLesson);

document.querySelectorAll("[data-message]").forEach((button) => {
  button.addEventListener("click", () => {
    sendStudentMessage(button.dataset.message);
  });
});

checkConnection();
