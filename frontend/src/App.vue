<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

import classroomBackground from "./assets/classroom-background.png";
import AvatarStage from "./components/AvatarStage.vue";
import ChatPanel from "./components/ChatPanel.vue";
import FacePanel from "./components/FacePanel.vue";
import LessonBoard from "./components/LessonBoard.vue";
import {
  getHealth,
  resetSession,
  sendActionResult,
  sendMessage as postMessage,
  synthesizeSpeech,
  transcribeAudio,
} from "./services/api.js";

const SESSION_KEY = "spatial-classroom-session-id";
const messages = ref([
  { role: "teacher", text: "Hello! What would you like to learn about animals today?" },
]);
const busy = ref(false);
const recording = ref(false);
const error = ref("");
const connected = ref(false);
const provider = ref("local AI");
const stageAction = ref(null);
const pendingAction = ref(null);
const speaking = ref(false);

let sessionId = getSessionId();
let mediaRecorder;
let recordingChunks = [];
let recordingTimer;
let currentAudio;
let currentAudioUrl;
let finishCurrentAudio;
let speechRequestId = 0;

function getSessionId() {
  let value = localStorage.getItem(SESSION_KEY);
  if (!value) {
    value = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, value);
  }
  return value;
}

function stopCurrentAudio() {
  currentAudio?.pause();
  finishCurrentAudio?.();
  finishCurrentAudio = null;
  currentAudio = null;
  if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
  currentAudioUrl = null;
}

async function playTeacherSpeech(output) {
  const requestId = ++speechRequestId;
  const segments = output.segments?.length
    ? output.segments
    : [{ language: "en-US", text: output.speech }];
  try {
    stopCurrentAudio();
    for (const segment of segments) {
      const blob = await synthesizeSpeech(segment.text, segment.language);
      if (requestId !== speechRequestId) return;
      currentAudioUrl = URL.createObjectURL(blob);
      currentAudio = new Audio(currentAudioUrl);
      speaking.value = true;
      await new Promise((resolve) => {
        finishCurrentAudio = resolve;
        currentAudio.addEventListener("ended", resolve, { once: true });
        currentAudio.addEventListener("error", resolve, { once: true });
        currentAudio.play().catch(resolve);
      });
      finishCurrentAudio = null;
      currentAudio = null;
      URL.revokeObjectURL(currentAudioUrl);
      currentAudioUrl = null;
    }
  } catch (reason) {
    console.warn("Teacher audio playback unavailable", reason);
  } finally {
    if (requestId === speechRequestId) {
      speaking.value = false;
      stopCurrentAudio();
    }
  }
}

async function handleOutput(output) {
  if (output.type === "speech") {
    messages.value.push({ role: "teacher", text: output.speech });
    void playTeacherSpeech(output);
    return;
  }
  if (output.type !== "action" || !output.action) {
    throw new Error("AI Core returned an unsupported response.");
  }
  stageAction.value = output.action;
  pendingAction.value = output.action;
}

async function sendStudentMessage(message) {
  if (busy.value || pendingAction.value) return;
  error.value = "";
  messages.value.push({ role: "student", text: message });
  busy.value = true;
  try {
    await handleOutput(await postMessage(sessionId, message));
  } catch (reason) {
    error.value = reason.message;
  } finally {
    busy.value = false;
  }
}

async function completeAction(result) {
  if (!pendingAction.value || busy.value) return;
  const action = pendingAction.value;
  if (result.selected) messages.value.push({ role: "student", text: result.selected });
  busy.value = true;
  try {
    const output = await sendActionResult(sessionId, action.call_id, result);
    pendingAction.value = null;
    if (action.type === "ui.show_choices") stageAction.value = null;
    await handleOutput(output);
  } catch (reason) {
    error.value = reason.message;
  } finally {
    busy.value = false;
  }
}

function preferredAudioType() {
  const types = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"];
  return types.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

async function toggleRecording() {
  if (mediaRecorder?.state === "recording") {
    mediaRecorder.stop();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || !globalThis.MediaRecorder) {
    error.value = "Voice recording is not supported by this browser.";
    return;
  }

  try {
    error.value = "";
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = preferredAudioType();
    mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    recordingChunks = [];
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) recordingChunks.push(event.data);
    });
    mediaRecorder.addEventListener(
      "stop",
      async () => {
        clearTimeout(recordingTimer);
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(recordingChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        mediaRecorder = null;
        recordingChunks = [];
        recording.value = false;
        busy.value = true;
        try {
          const transcript = await transcribeAudio(blob);
          busy.value = false;
          await sendStudentMessage(transcript.text.trim());
        } catch (reason) {
          error.value = reason.message;
          busy.value = false;
        }
      },
      { once: true },
    );
    mediaRecorder.start();
    recording.value = true;
    recordingTimer = window.setTimeout(() => mediaRecorder?.stop(), 30_000);
  } catch (reason) {
    error.value = reason.name === "NotAllowedError"
      ? "Microphone permission was denied."
      : "The microphone could not be started.";
  }
}

async function newLesson() {
  if (busy.value || recording.value) return;
  try {
    await resetSession(sessionId);
  } catch {
    // A missing server-side session is already equivalent to a reset.
  }
  localStorage.removeItem(SESSION_KEY);
  sessionId = getSessionId();
  messages.value = [
    { role: "teacher", text: "Hello! What would you like to learn about animals today?" },
  ];
  stageAction.value = null;
  pendingAction.value = null;
  error.value = "";
  speechRequestId += 1;
  stopCurrentAudio();
  speaking.value = false;
}

onMounted(async () => {
  try {
    const health = await getHealth();
    connected.value = true;
    provider.value = health.provider;
  } catch {
    connected.value = false;
    error.value = "Cannot reach ClassroomAI. Start the local API first.";
  }
});

onBeforeUnmount(() => {
  clearTimeout(recordingTimer);
  mediaRecorder?.stream?.getTracks().forEach((track) => track.stop());
  speechRequestId += 1;
  stopCurrentAudio();
});
</script>

<template>
  <main class="classroom" :style="{ backgroundImage: `url(${classroomBackground})` }">
    <div class="soft-overlay"></div>
    <header class="topbar">
      <div class="brand">
        <span>AI</span>
        <div>
          <strong>ClassroomAI</strong>
          <small>English · Animals and abilities</small>
        </div>
      </div>
      <div :class="['connection', { online: connected }]">
        <i></i>
        {{ connected ? `Ready · ${provider}` : "Offline" }}
      </div>
    </header>

    <AvatarStage :speaking="speaking" />
    <LessonBoard
      :action="stageAction"
      :interactive="Boolean(pendingAction) && !busy"
      @result="completeAction"
    />
    <ChatPanel
      :messages="messages"
      :busy="busy"
      :recording="recording"
      :disabled="Boolean(pendingAction)"
      :error="error"
      @send="sendStudentMessage"
      @toggle-recording="toggleRecording"
      @reset="newLesson"
    />
    <FacePanel />
  </main>
</template>
