<script setup>
import { nextTick, ref, watch } from "vue";

const props = defineProps({
  messages: { type: Array, required: true },
  busy: Boolean,
  recording: Boolean,
  disabled: Boolean,
  error: { type: String, default: "" },
});
const emit = defineEmits(["send", "toggle-recording", "reset"]);
const draft = ref("");
const conversation = ref(null);

watch(
  () => props.messages.length,
  async () => {
    await nextTick();
    if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight;
  },
);

function submit() {
  const message = draft.value.trim();
  if (!message || props.busy || props.disabled) return;
  draft.value = "";
  emit("send", message);
}
</script>

<template>
  <aside class="chat-panel">
    <div class="chat-heading">
      <div class="teacher-mark">G</div>
      <div>
        <small>Your English teacher</small>
        <strong>Gemma</strong>
      </div>
      <button type="button" :disabled="busy || recording" @click="$emit('reset')">
        New lesson
      </button>
    </div>

    <div ref="conversation" class="conversation" aria-live="polite">
      <article
        v-for="(message, index) in messages"
        :key="`${message.role}-${index}`"
        :class="['message', `${message.role}-message`]"
      >
        <span>{{ message.role === "teacher" ? "Teacher" : "You" }}</span>
        <p>{{ message.text }}</p>
      </article>
      <div v-if="busy" class="thinking"><i></i><i></i><i></i></div>
    </div>

    <p v-if="error" class="chat-error" role="alert">{{ error }}</p>

    <form class="chat-form" @submit.prevent="submit">
      <input
        v-model="draft"
        type="text"
        maxlength="2000"
        autocomplete="off"
        placeholder="Ask Gemma about an animal…"
        :disabled="busy || recording || disabled"
        aria-label="Message Gemma"
      />
      <button
        class="speak-button"
        :class="{ recording }"
        type="button"
        :disabled="busy || disabled"
        :aria-pressed="recording"
        @click="$emit('toggle-recording')"
      >
        {{ recording ? "Stop" : "Speak" }}
      </button>
      <button class="send-button" type="submit" :disabled="busy || recording || disabled">
        Send
      </button>
    </form>
  </aside>
</template>

<style scoped>
.chat-panel {
  position: absolute;
  left: clamp(18px, 3vw, 46px);
  bottom: 24px;
  z-index: 6;
  width: min(40vw, 520px);
  min-width: 340px;
  border: 1px solid rgb(255 255 255 / 0.7);
  border-radius: 24px;
  background: rgb(252 253 250 / 0.9);
  box-shadow: 0 24px 65px rgb(37 65 54 / 0.2);
  backdrop-filter: blur(18px);
  overflow: hidden;
}

.chat-heading {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 14px 16px;
  border-bottom: 1px solid #dfe7e1;
}

.teacher-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  color: white;
  background: #286d53;
  font-weight: 900;
}

.chat-heading small,
.chat-heading strong { display: block; }
.chat-heading small { color: #6c7a76; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; }
.chat-heading strong { color: #17372f; font-size: 17px; }
.chat-heading button { margin-left: auto; border: 0; color: #356653; background: transparent; font-size: 12px; font-weight: 800; }

.conversation {
  max-height: 210px;
  min-height: 92px;
  padding: 14px 16px 5px;
  overflow-y: auto;
}

.message {
  width: fit-content;
  max-width: 88%;
  margin: 0 0 10px;
  padding: 10px 12px;
  border-radius: 15px;
}

.message span { display: block; margin-bottom: 3px; font-size: 9px; font-weight: 900; letter-spacing: 0.1em; text-transform: uppercase; }
.message p { margin: 0; line-height: 1.4; white-space: pre-wrap; }
.teacher-message { border-top-left-radius: 4px; color: #24473b; background: #e0f0e7; }
.teacher-message span { color: #37705a; }
.student-message { margin-left: auto; border-top-right-radius: 4px; color: white; background: #287255; }
.student-message span { color: rgb(255 255 255 / 0.68); }

.thinking { display: flex; gap: 4px; padding: 8px 4px 14px; }
.thinking i { width: 6px; height: 6px; border-radius: 50%; background: #5b8c77; animation: pulse 1s infinite alternate; }
.thinking i:nth-child(2) { animation-delay: 160ms; }
.thinking i:nth-child(3) { animation-delay: 320ms; }

.chat-error { margin: 0 16px 8px; padding: 8px 10px; border-radius: 9px; color: #923c38; background: #f8e6e3; font-size: 12px; }

.chat-form { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #dfe7e1; }
.chat-form input { flex: 1; min-width: 0; padding: 12px 13px; border: 1px solid #ccd8d1; border-radius: 12px; background: white; }
.chat-form button { padding: 0 14px; border-radius: 12px; font-weight: 850; }
.speak-button { border: 1px solid #33785d; color: #28694f; background: #e0f1e8; }
.speak-button.recording { border-color: #ae443d; color: white; background: #ae443d; }
.send-button { border: 0; color: white; background: #286d53; }
button:disabled, input:disabled { cursor: not-allowed; opacity: 0.55; }

@keyframes pulse { to { transform: translateY(-4px); opacity: 0.45; } }

@media (max-width: 900px) {
  .chat-panel { left: 18px; right: 18px; bottom: 18px; width: auto; min-width: 0; }
  .conversation { max-height: 150px; }
}
</style>
