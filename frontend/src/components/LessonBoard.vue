<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  action: { type: Object, default: null },
  interactive: Boolean,
});
const emit = defineEmits(["result"]);
const reportedCallId = ref(null);
const selected = ref(null);

watch(
  () => props.action?.call_id,
  () => {
    reportedCallId.value = null;
    selected.value = null;
  },
);

function reportImage(success) {
  if (!props.action || reportedCallId.value === props.action.call_id) return;
  reportedCallId.value = props.action.call_id;
  emit("result", { success });
}

function choose(choice) {
  if (!props.interactive || selected.value) return;
  selected.value = choice;
  emit("result", { selected: choice });
}
</script>

<template>
  <section class="lesson-board" aria-live="polite">
    <div v-if="!action" class="board-welcome">
      <p class="eyebrow">Today’s lesson</p>
      <h1>Animals and their amazing abilities</h1>
      <p>Ask Gemma a question, request a picture, or start a quick quiz.</p>
    </div>

    <div v-else-if="action.type === 'ui.show_image'" class="image-lesson">
      <img
        :src="action.payload.image_url"
        :alt="action.payload.caption"
        @load="reportImage(true)"
        @error="reportImage(false)"
      />
      <strong>{{ action.payload.caption }}</strong>
    </div>

    <div v-else-if="action.type === 'ui.show_choices'" class="choice-lesson">
      <p class="eyebrow">Quick question</p>
      <h2>{{ action.payload.question }}</h2>
      <div class="choice-grid">
        <button
          v-for="choice in action.payload.choices"
          :key="choice"
          type="button"
          :class="{ selected: selected === choice }"
          :disabled="!interactive || Boolean(selected)"
          @click="choose(choice)"
        >
          {{ choice }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.lesson-board {
  position: absolute;
  top: 92px;
  left: clamp(18px, 3vw, 46px);
  z-index: 4;
  width: min(34vw, 470px);
  min-width: 310px;
  padding: clamp(20px, 2.4vw, 30px);
  border: 1px solid rgb(255 255 255 / 0.68);
  border-radius: 26px;
  background: rgb(255 255 255 / 0.82);
  box-shadow: 0 24px 60px rgb(42 70 58 / 0.16);
  backdrop-filter: blur(16px);
}

.eyebrow {
  margin: 0 0 8px;
  color: #2b7559;
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0;
  color: #17372f;
  line-height: 1.08;
  letter-spacing: -0.035em;
}

h1 { font-size: clamp(28px, 3.2vw, 44px); }
h2 { font-size: clamp(24px, 2.7vw, 36px); }

.board-welcome > p:last-child {
  margin: 16px 0 0;
  color: #60736d;
  line-height: 1.55;
}

.image-lesson {
  display: grid;
  gap: 14px;
  justify-items: center;
}

.image-lesson img {
  width: min(100%, 320px);
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 20px;
  box-shadow: 0 15px 36px rgb(28 62 50 / 0.18);
}

.image-lesson strong {
  font-size: 26px;
  color: #17372f;
}

.choice-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 22px;
}

.choice-grid button {
  min-height: 62px;
  padding: 12px;
  border: 1px solid #cbd9d1;
  border-radius: 15px;
  color: #214d3e;
  background: white;
  font-weight: 800;
}

.choice-grid button:hover:not(:disabled),
.choice-grid button.selected {
  border-color: #297657;
  color: white;
  background: #297657;
}

.choice-grid button:disabled { opacity: 0.65; }
.choice-grid button.selected:disabled { opacity: 1; }

@media (max-width: 900px) {
  .lesson-board {
    top: 82px;
    width: calc(100% - 36px);
    min-width: 0;
  }
}
</style>
