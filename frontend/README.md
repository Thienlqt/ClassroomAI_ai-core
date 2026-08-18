# ClassroomAI browser app

This Vue app is the visual shell around the local Python AI Core. It uses Three.js and
`@pixiv/three-vrm` for the animated teacher. It does not contain another language model
or another agent runtime.

## What belongs where

```text
Browser (this folder)
  camera + microphone capture
  VRM teacher, board, chat, buttons, subtitles
  sends inputs and renders semantic actions

Python AI Core
  Gemma conversation and lesson policy
  tool/action validation and session state
  whisper.cpp transcription and Piper speech
  YuNet detection, SFace embeddings, cosine matching, SQLite
```

The main components are:

- `src/components/AvatarStage.vue` — VRM loading, blink, idle movement, and eye tracking
- `src/components/LessonBoard.vue` — `ui.show_image` and `ui.show_choices`
- `src/components/ChatPanel.vue` — text, microphone, transcript, and lesson reset
- `src/components/FacePanel.vue` — opt-in camera, scores, warning, and consent enrollment
- `src/services/api.js` — the complete HTTP boundary with AI Core, including language-routed speech
- `src/services/voiceActivity.js` — lightweight room calibration and speech/silence timing

## Run it

For normal use, do not install Node.js. The committed `bundle/` is served by FastAPI:

```bash
conda activate classroom-ai
python scripts/start_api.py --reload
```

Open <http://127.0.0.1:8000/>. Start the llama.cpp model server first if you want Gemma
responses. Piper, whisper.cpp, and the face models are optional; their controls show a
clear error if a local component is not installed.

The **Speak** button needs one click to request microphone access. It then measures the
room for about 0.65 seconds, waits for sustained speech, and stops after about 1.2
seconds of silence. This voice-activity gate is browser code, not another AI model, so
it consumes negligible resources when idle. **Finish** remains available for noisy
rooms or browsers without Web Audio support.

For speech output, render `output.speech` as the clean subtitle and play
`output.segments` in order. Each segment has a `language` of `en-US` or `vi-VN`; send
that value with its text to `POST /v1/speech` so AI Core selects the correct Piper voice.

## Develop it

Node.js 22 and pnpm 10 were used for the current build. With the Python API on port
8000:

```bash
cd frontend
pnpm install
pnpm dev
```

Open <http://127.0.0.1:5173/>. Vite proxies `/v1`, `/health`, and `/assets` to the local
API, so the source uses the same relative URLs in development and production.

After a frontend change, rebuild the production files that FastAPI serves:

```bash
cd frontend
pnpm build
```

Commit `package.json`, `pnpm-lock.yaml`, `src/`, and `bundle/` together. Do not commit
`node_modules/` or `models/avatar/teacher.vrm`.

## Replacing AIRI's AI side

Only the renderer ideas were adapted from Project AIRI. `AvatarStage.vue` owns the
visual avatar lifecycle while ClassroomAI owns all intelligence through HTTP. This
keeps the boundary small: another app can reuse `src/services/api.js`, or replace the
entire Vue UI, without changing Gemma, prompts, tools, or Python session logic.

The avatar file is requested from `/assets/avatar/teacher.vrm`. Follow
[`../models/avatar/README.md`](../models/avatar/README.md) to install the tested sample,
or place a compatible, properly licensed VRM at that path.
