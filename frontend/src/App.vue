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
import { calculateRms, matchSpokenChoice, VoiceActivityGate } from "./services/voiceActivity.js";

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
const recordingPhase = ref("idle");
const voiceLevel = ref(0);
const microphoneEnabled = ref(false);
const microphoneMuted = ref(false);

let sessionId = getSessionId();
let mediaRecorder;
let microphoneStream;
let recordingChunks = [];
let recordingTimer;
let restartListeningTimer;
let microphoneRequest;
let startingListeningCycle = false;
let appUnmounted = false;
let voiceActivityTimer;
let voiceAudioContext;
let voiceSource;
let voiceAnalyser;
let voiceActivityGate;
let recordingStopReason = "manual";
let recordingHadSpeech = false;
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
  speaking.value = true;
  pauseAutomaticListening("paused");
  try {
    stopCurrentAudio();
    for (const segment of segments) {
      const blob = await synthesizeSpeech(segment.text, segment.language);
      if (requestId !== speechRequestId) return;
      currentAudioUrl = URL.createObjectURL(blob);
      currentAudio = new Audio(currentAudioUrl);
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
      scheduleAutomaticListening();
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
  pauseAutomaticListening("paused");
  busy.value = true;
  try {
    await handleOutput(await postMessage(sessionId, message));
  } catch (reason) {
    error.value = reason.message;
  } finally {
    busy.value = false;
    scheduleAutomaticListening();
  }
}

async function completeAction(result) {
  if (!pendingAction.value || busy.value) return;
  const action = pendingAction.value;
  if (result.selected) messages.value.push({ role: "student", text: result.selected });
  pauseAutomaticListening("paused");
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
    scheduleAutomaticListening();
  }
}

function preferredAudioType() {
  const types = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"];
  return types.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function stopVoiceActivityMonitor() {
  clearInterval(voiceActivityTimer);
  voiceActivityTimer = null;
  voiceSource?.disconnect();
  voiceAnalyser?.disconnect();
  voiceSource = null;
  voiceAnalyser = null;
  voiceActivityGate = null;
  voiceLevel.value = 0;
  if (voiceAudioContext) void voiceAudioContext.close().catch(() => {});
  voiceAudioContext = null;
}

function finishRecording(reason = "paused") {
  if (mediaRecorder?.state !== "recording") return;
  recordingStopReason = reason;
  recordingHadSpeech ||= Boolean(voiceActivityGate?.speechDetected);
  mediaRecorder.stop();
}

async function startVoiceActivityMonitor(stream) {
  const AudioContext = globalThis.AudioContext || globalThis.webkitAudioContext;
  if (!AudioContext) return false;

  try {
    voiceAudioContext = new AudioContext();
    await voiceAudioContext.resume();
    voiceSource = voiceAudioContext.createMediaStreamSource(stream);
    voiceAnalyser = voiceAudioContext.createAnalyser();
    voiceAnalyser.fftSize = 1024;
    voiceAnalyser.smoothingTimeConstant = 0;
    voiceSource.connect(voiceAnalyser);

    const samples = new Float32Array(voiceAnalyser.fftSize);
    voiceActivityGate = new VoiceActivityGate();
    recordingPhase.value = "calibrating";
    voiceActivityTimer = window.setInterval(() => {
      if (!voiceAnalyser || mediaRecorder?.state !== "recording") return;
      voiceAnalyser.getFloatTimeDomainData(samples);
      const result = voiceActivityGate.update(calculateRms(samples), performance.now());
      voiceLevel.value = Math.min(
        1,
        result.level / Math.max(result.startThreshold * 1.8, 0.001),
      );
      if (result.phase !== "stopped") recordingPhase.value = result.phase;
      if (result.speechDetected) recordingHadSpeech = true;
      if (result.stopReason) finishRecording(result.stopReason);
    }, 50);
    return true;
  } catch (reason) {
    console.warn("Automatic voice detection unavailable", reason);
    stopVoiceActivityMonitor();
    return false;
  }
}

function canListenAutomatically() {
  return Boolean(
    !appUnmounted
    && microphoneStream?.active
    && microphoneEnabled.value
    && !microphoneMuted.value
    && !busy.value
    && !speaking.value,
  );
}

function pauseAutomaticListening(reason = "paused") {
  clearTimeout(restartListeningTimer);
  restartListeningTimer = null;
  if (mediaRecorder?.state === "recording") {
    finishRecording(reason);
  } else if (microphoneEnabled.value && !microphoneMuted.value) {
    recordingPhase.value = "paused";
  }
}

function scheduleAutomaticListening(delay = 150) {
  clearTimeout(restartListeningTimer);
  restartListeningTimer = null;
  if (!canListenAutomatically()) return;
  restartListeningTimer = window.setTimeout(() => {
    restartListeningTimer = null;
    void startListeningCycle();
  }, delay);
}

async function startListeningCycle() {
  if (!canListenAutomatically() || mediaRecorder || startingListeningCycle) return;
  startingListeningCycle = true;
  const stream = microphoneStream;

  try {
    const mimeType = preferredAudioType();
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    mediaRecorder = recorder;
    recordingChunks = [];
    recordingStopReason = "no-speech";
    recordingHadSpeech = false;
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) recordingChunks.push(event.data);
    });
    recorder.addEventListener(
      "stop",
      async () => {
        clearTimeout(recordingTimer);
        recordingTimer = null;
        const stopReason = recordingStopReason;
        const heardSpeech = recordingHadSpeech;
        stopVoiceActivityMonitor();
        const blob = new Blob(recordingChunks, { type: recorder.mimeType || "audio/webm" });
        mediaRecorder = null;
        recordingChunks = [];
        recording.value = false;
        voiceLevel.value = 0;

        if (stopReason === "cancelled") {
          recordingPhase.value = microphoneMuted.value ? "muted" : "idle";
          scheduleAutomaticListening();
          return;
        }
        if (stopReason === "paused") {
          recordingPhase.value = "paused";
          return;
        }
        if (stopReason === "unsupported") {
          recordingPhase.value = "unavailable";
          error.value = "Automatic listening is not supported by this browser.";
          return;
        }
        if (stopReason === "no-speech" || (stopReason === "maximum-duration" && !heardSpeech)) {
          recordingPhase.value = "listening";
          scheduleAutomaticListening();
          return;
        }
        if (!blob.size) {
          recordingPhase.value = "listening";
          error.value = "The microphone did not produce any audio. Listening will retry automatically.";
          scheduleAutomaticListening(500);
          return;
        }

        recordingPhase.value = "processing";
        busy.value = true;
        try {
          const transcript = await transcribeAudio(blob);
          const message = transcript.text.trim();
          if (!message) throw new Error("I couldn’t understand that. Please say it again.");
          busy.value = false;
          if (pendingAction.value?.type === "ui.show_choices") {
            const selected = matchSpokenChoice(message, pendingAction.value.payload.choices);
            if (!selected) {
              throw new Error(`I heard “${message}”. Please say one of the choices.`);
            }
            await completeAction({ selected });
          } else {
            await sendStudentMessage(message);
          }
        } catch (reason) {
          error.value = reason.message;
          busy.value = false;
        } finally {
          scheduleAutomaticListening();
        }
      },
      { once: true },
    );
    recorder.start();
    recording.value = true;
    const automaticDetectionStarted = await startVoiceActivityMonitor(stream);
    if (mediaRecorder !== recorder || recorder.state !== "recording") {
      stopVoiceActivityMonitor();
      return;
    }
    if (!automaticDetectionStarted) {
      finishRecording("unsupported");
      return;
    }
    recordingTimer = window.setTimeout(() => finishRecording("maximum-duration"), 30_000);
  } catch (reason) {
    stopVoiceActivityMonitor();
    mediaRecorder = null;
    recording.value = false;
    recordingPhase.value = "unavailable";
    error.value = "The microphone listener could not be started.";
    console.warn("Always-on microphone failed", reason);
  } finally {
    startingListeningCycle = false;
  }
}

async function initializeAutomaticListening() {
  if (microphoneRequest) return microphoneRequest;
  if (!navigator.mediaDevices?.getUserMedia || !globalThis.MediaRecorder) {
    recordingPhase.value = "unavailable";
    error.value = "Automatic voice listening is not supported by this browser.";
    return;
  }
  if (microphoneStream?.active) {
    microphoneEnabled.value = true;
    microphoneMuted.value = false;
    scheduleAutomaticListening(0);
    return;
  }

  recordingPhase.value = "requesting";
  microphoneRequest = navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: { ideal: true },
      noiseSuppression: { ideal: true },
      autoGainControl: { ideal: true },
      channelCount: { ideal: 1 },
    },
  });
  try {
    microphoneStream = await microphoneRequest;
    if (appUnmounted) {
      microphoneStream.getTracks().forEach((track) => track.stop());
      microphoneStream = null;
      return;
    }
    microphoneEnabled.value = true;
    microphoneMuted.value = false;
    scheduleAutomaticListening(0);
  } catch (reason) {
    microphoneEnabled.value = false;
    recordingPhase.value = "unavailable";
    error.value = reason.name === "NotAllowedError"
      ? "Microphone access is blocked. Allow it in the browser, then select Retry mic."
      : "The microphone could not be started.";
  } finally {
    microphoneRequest = null;
  }
}

function releaseMicrophone() {
  pauseAutomaticListening("cancelled");
  microphoneStream?.getTracks().forEach((track) => track.stop());
  microphoneStream = null;
  microphoneEnabled.value = false;
}

function toggleMicrophone() {
  if (microphoneStream?.active) {
    microphoneMuted.value = true;
    releaseMicrophone();
    recordingPhase.value = "muted";
    return;
  }
  microphoneMuted.value = false;
  void initializeAutomaticListening();
}

async function newLesson() {
  if (busy.value) return;
  pauseAutomaticListening("paused");
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
  scheduleAutomaticListening();
}

onMounted(async () => {
  void initializeAutomaticListening();
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
  appUnmounted = true;
  clearTimeout(recordingTimer);
  clearTimeout(restartListeningTimer);
  if (mediaRecorder?.state === "recording") finishRecording("cancelled");
  stopVoiceActivityMonitor();
  releaseMicrophone();
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
      :recording-phase="recordingPhase"
      :voice-level="voiceLevel"
      :microphone-enabled="microphoneEnabled"
      :microphone-muted="microphoneMuted"
      :disabled="Boolean(pendingAction)"
      :error="error"
      @send="sendStudentMessage"
      @toggle-microphone="toggleMicrophone"
      @reset="newLesson"
    />
    <FacePanel />
  </main>
</template>
