<script setup>
import { computed, onBeforeUnmount, ref } from "vue";

import { enrollFace, recognizeFaces } from "../services/api.js";

const video = ref(null);
const canvas = ref(null);
const running = ref(false);
const scanning = ref(false);
const face = ref(null);
const status = ref("Camera is off");
const error = ref("");
const showEnrollment = ref(false);
const displayName = ref("");
const consent = ref(false);
const enrolling = ref(false);
const enrollmentProgress = ref(0);
const unknownStreak = ref(0);

let stream;
let timer;

const faceBoxStyle = computed(() => {
  if (!face.value) return {};
  const bounds = face.value.bounds;
  return {
    left: `${(1 - bounds.x_max) * 100}%`,
    top: `${bounds.y_min * 100}%`,
    width: `${(bounds.x_max - bounds.x_min) * 100}%`,
    height: `${(bounds.y_max - bounds.y_min) * 100}%`,
  };
});

const recognitionLabel = computed(() => {
  if (!face.value) return "No face";
  return face.value.display_name || "Unknown face";
});

function captureFrame() {
  if (!video.value?.videoWidth) throw new Error("Camera is not ready yet.");
  const width = Math.min(video.value.videoWidth, 640);
  const scale = width / video.value.videoWidth;
  const height = Math.round(video.value.videoHeight * scale);
  canvas.value.width = width;
  canvas.value.height = height;
  canvas.value.getContext("2d").drawImage(video.value, 0, 0, width, height);
  return canvas.value.toDataURL("image/jpeg", 0.82).split(",", 2)[1];
}

async function scan() {
  if (!running.value || scanning.value || enrolling.value) return;
  scanning.value = true;
  try {
    const faces = await recognizeFaces(captureFrame());
    if (!faces.length) {
      face.value = null;
      unknownStreak.value = 0;
      status.value = "Looking for one face";
      return;
    }
    face.value = faces.sort((a, b) => b.detection_score - a.detection_score)[0];
    if (face.value.subject_id) {
      unknownStreak.value = 0;
      status.value = `Recognized as ${face.value.display_name}`;
    } else {
      unknownStreak.value += 1;
      status.value = "Face detected · identity unknown";
    }
  } catch (reason) {
    error.value = reason.message;
  } finally {
    scanning.value = false;
  }
}

async function startCamera() {
  error.value = "";
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false,
    });
    video.value.srcObject = stream;
    await video.value.play();
    running.value = true;
    status.value = "Camera ready";
    await scan();
    timer = window.setInterval(scan, 1600);
  } catch (reason) {
    error.value = reason.name === "NotAllowedError"
      ? "Camera permission was denied."
      : "The camera could not be started.";
  }
}

function stopCamera() {
  clearInterval(timer);
  stream?.getTracks().forEach((track) => track.stop());
  stream = null;
  running.value = false;
  face.value = null;
  unknownStreak.value = 0;
  status.value = "Camera is off";
}

function openEnrollment() {
  displayName.value = "";
  consent.value = false;
  enrollmentProgress.value = 0;
  showEnrollment.value = true;
}

function subjectId() {
  const key = "classroom-face-subject-id";
  let value = localStorage.getItem(key);
  if (!value) {
    value = `self-${crypto.randomUUID().slice(0, 12)}`;
    localStorage.setItem(key, value);
  }
  return value;
}

function pause(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function confirmEnrollment() {
  if (!displayName.value.trim() || !consent.value) return;
  enrolling.value = true;
  error.value = "";
  const id = subjectId();
  const consentReference = `browser-self-enrollment:${new Date().toISOString()}`;
  try {
    for (let index = 0; index < 3; index += 1) {
      enrollmentProgress.value = index + 1;
      await enrollFace({
        image_base64: captureFrame(),
        subject_id: id,
        display_name: displayName.value.trim(),
        consent_confirmed: true,
        consent_reference: consentReference,
      });
      if (index < 2) await pause(450);
    }
    showEnrollment.value = false;
    unknownStreak.value = 0;
    status.value = "Enrollment saved locally";
  } catch (reason) {
    error.value = reason.message;
  } finally {
    enrolling.value = false;
  }
  if (!error.value) {
    await pause(300);
    await scan();
  }
}

onBeforeUnmount(stopCamera);
</script>

<template>
  <aside class="face-panel">
    <div class="camera-frame">
      <video ref="video" muted playsinline></video>
      <div v-if="face" class="face-box" :style="faceBoxStyle"></div>
      <div v-if="!running" class="camera-off">
        <span aria-hidden="true">◉</span>
        <button type="button" @click="startCamera">Start camera</button>
      </div>
      <span v-if="running" class="local-only">Local only</span>
    </div>
    <canvas ref="canvas" hidden></canvas>

    <div class="face-summary">
      <div>
        <small>Identity</small>
        <strong>{{ recognitionLabel }}</strong>
      </div>
      <button v-if="running" type="button" class="stop-camera" @click="stopCamera">Stop</button>
    </div>

    <div v-if="face" class="scores">
      <span>Face {{ Math.round(face.detection_score * 100) }}%</span>
      <span v-if="face.similarity != null">Match {{ Math.round(face.similarity * 100) }}%</span>
    </div>
    <p class="camera-status">{{ status }}</p>
    <p v-if="error" class="camera-error" role="alert">{{ error }}</p>

    <div v-if="running && unknownStreak >= 2" class="unknown-warning">
      <strong>This face is not enrolled.</strong>
      <span>No image will be saved automatically.</span>
      <button type="button" @click="openEnrollment">Review enrollment</button>
    </div>

    <Teleport to="body">
      <div v-if="showEnrollment" class="modal-backdrop" role="presentation">
        <section class="consent-modal" role="dialog" aria-modal="true" aria-labelledby="consentTitle">
          <p class="modal-eyebrow">Biometric consent</p>
          <h2 id="consentTitle">Save your face embeddings?</h2>
          <p>
            ClassroomAI will capture three camera frames and store mathematical face
            embeddings on this device. The frames themselves are not saved.
          </p>
          <label>
            Display name
            <input v-model="displayName" maxlength="100" autocomplete="name" placeholder="Your name" />
          </label>
          <label class="consent-check">
            <input v-model="consent" type="checkbox" />
            <span>I understand and consent to local face enrollment.</span>
          </label>
          <p class="consent-note">You can delete this enrollment later using the local administrator tool.</p>
          <div class="modal-actions">
            <button type="button" class="cancel" :disabled="enrolling" @click="showEnrollment = false">Not now</button>
            <button
              type="button"
              class="confirm"
              :disabled="!displayName.trim() || !consent || enrolling"
              @click="confirmEnrollment"
            >
              {{ enrolling ? `Saving ${enrollmentProgress}/3…` : "Save locally" }}
            </button>
          </div>
        </section>
      </div>
    </Teleport>
  </aside>
</template>

<style scoped>
.face-panel {
  position: absolute;
  right: 24px;
  bottom: 24px;
  z-index: 8;
  width: 270px;
  padding: 10px;
  border: 1px solid rgb(255 255 255 / 0.72);
  border-radius: 22px;
  color: #1b3d32;
  background: rgb(252 253 250 / 0.92);
  box-shadow: 0 24px 65px rgb(37 65 54 / 0.2);
  backdrop-filter: blur(18px);
}

.camera-frame {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border-radius: 15px;
  background: #dfe8e3;
}

video { width: 100%; height: 100%; display: block; object-fit: cover; transform: scaleX(-1); }
.camera-off { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 10px; color: #527066; }
.camera-off span { font-size: 28px; }
.camera-off button, .unknown-warning button { padding: 8px 11px; border: 0; border-radius: 10px; color: white; background: #2a7156; font-size: 12px; font-weight: 800; }
.local-only { position: absolute; top: 8px; left: 8px; padding: 5px 7px; border-radius: 999px; color: white; background: rgb(24 62 49 / 0.72); font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }
.face-box { position: absolute; border: 2px solid #7ee2ad; border-radius: 10px; box-shadow: 0 0 0 1px rgb(9 54 37 / 0.45), inset 0 0 16px rgb(88 222 148 / 0.12); pointer-events: none; }

.face-summary { display: flex; align-items: center; margin: 10px 3px 2px; }
.face-summary small, .face-summary strong { display: block; }
.face-summary small { color: #72827c; font-size: 9px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.face-summary strong { margin-top: 2px; font-size: 14px; }
.stop-camera { margin-left: auto; border: 0; color: #8b4640; background: transparent; font-size: 11px; font-weight: 800; }
.scores { display: flex; gap: 6px; margin: 8px 3px 0; }
.scores span { padding: 5px 7px; border-radius: 8px; color: #32654f; background: #e1f1e8; font-size: 10px; font-weight: 800; }
.camera-status { margin: 8px 3px 0; color: #687b74; font-size: 11px; }
.camera-error { margin: 8px 0 0; padding: 7px 8px; border-radius: 8px; color: #91423c; background: #f8e7e4; font-size: 11px; }

.unknown-warning { display: grid; gap: 5px; margin-top: 10px; padding: 10px; border: 1px solid #e5c68d; border-radius: 12px; background: #fff6df; }
.unknown-warning strong { font-size: 12px; }
.unknown-warning span { color: #756647; font-size: 10px; }
.unknown-warning button { justify-self: start; margin-top: 3px; }

.modal-backdrop { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; padding: 20px; background: rgb(20 38 32 / 0.56); backdrop-filter: blur(8px); }
.consent-modal { width: min(100%, 470px); padding: 28px; border-radius: 24px; color: #193a30; background: #fffefa; box-shadow: 0 30px 90px rgb(15 32 26 / 0.35); }
.modal-eyebrow { margin: 0 0 7px; color: #a36829; font-size: 10px; font-weight: 900; letter-spacing: 0.12em; text-transform: uppercase; }
.consent-modal h2 { margin: 0; font-size: 28px; letter-spacing: -0.035em; }
.consent-modal > p:not(.modal-eyebrow):not(.consent-note) { color: #5f716b; line-height: 1.55; }
.consent-modal label:not(.consent-check) { display: grid; gap: 7px; margin-top: 18px; font-size: 12px; font-weight: 800; }
.consent-modal input[type="text"], .consent-modal input:not([type]) { padding: 12px; border: 1px solid #cbd8d1; border-radius: 11px; font: inherit; }
.consent-check { display: flex; align-items: flex-start; gap: 9px; margin-top: 18px; color: #334e45; font-size: 13px; line-height: 1.4; }
.consent-check input { margin-top: 3px; }
.consent-note { color: #7b6b4e; font-size: 11px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 9px; margin-top: 22px; }
.modal-actions button { padding: 11px 15px; border-radius: 11px; font-weight: 850; }
.modal-actions .cancel { border: 1px solid #ced8d2; color: #4c625a; background: white; }
.modal-actions .confirm { border: 0; color: white; background: #286d53; }
.modal-actions button:disabled { opacity: 0.5; }

@media (max-width: 900px) {
  .face-panel { top: 82px; right: 18px; bottom: auto; width: 190px; }
  .face-summary, .scores, .camera-status { display: none; }
}
</style>
