# Optional local components

These components are deliberately separate from the child-facing Gemma agent. Install
only what the device needs, using the existing `classroom-ai` Conda environment.

## Hermes teacher assistant

Hermes is an optional adult-only planning shell around the same llama.cpp endpoint. It
does not replace `ClassroomAgent`, its system prompt, classroom tools, or HTTP session
protocol. Its reviewed `SOUL.md` includes the bilingual teaching policy: plan short
Vietnamese clarification only when evidence shows it is needed, then return the learner
to English practice. The launcher restricts Hermes to its memory toolset; it does not
give the model terminal, browser, web, or file tools.

Install Hermes with its official installer in minimal mode. This skips its setup
wizard, browser/computer-control dependencies, and bundled skills because the
ClassroomAI launcher exposes only the memory toolset:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/hermes-install.sh
bash /tmp/hermes-install.sh \
  --skip-setup \
  --skip-browser \
  --skip-computer-use \
  --no-skills \
  --non-interactive
```

This is Hermes's own managed CLI installation, not another Conda environment. The
ClassroomAI Python packages remain in the existing `classroom-ai` environment.

Hermes documents 64,000 tokens as its minimum local context because its agent prompt
and tool definitions are much larger than a normal chat prompt. Stop the normal 8K
llama.cpp server, then start the same Gemma model in a separate teacher session:

```bash
conda activate classroom-ai
CLASSROOM_LLAMA_CONTEXT_SIZE=65536 \
CLASSROOM_LLAMA_EXTRA_ARGS="--cache-type-k q8_0 --cache-type-v q8_0" \
python scripts/start_model.py
```

In a second terminal:

```bash
conda activate classroom-ai
python scripts/start_hermes_teacher.py
```

The launcher creates `.runtime/hermes-teacher` on first use. That directory is ignored
by Git and keeps teacher memory separate from the source tree. On every start it
refreshes the runtime `SOUL.md` from the reviewed source-controlled policy, while
leaving the runtime configuration and Hermes memory intact.

This mode is experimental with a 4B model. The compressed KV cache reduces memory
pressure, but a 64K context still consumes substantially more RAM and prompt
processing time. Benchmark it on the real device before relying on it. When teacher
planning is finished, stop that server and run `python scripts/start_model.py` again
to restore the smaller, faster 8K student-agent default.

## Piper TTS

Piper turns returned teacher speech into a WAV file locally. It runs on CPU and is a
good fit for the planned Intel device.

```bash
conda activate classroom-ai
pip install -r requirements-audio.txt
python -m piper.download_voices --download-dir voices \
  en_US-lessac-medium vi_VN-vais1000-medium
```

Restart the AI Core API after installation. The app sends:

```http
POST /v1/speech
Content-Type: application/json

{"text":"Great job! The eagle can fly.","language":"en-US"}
```

For a Vietnamese support segment, send `"language":"vi-VN"`. Both voice models load
only when first used and are cached by the API process. The response body is
`audio/wav`. In a browser:

```js
const response = await fetch("http://127.0.0.1:8000/v1/speech", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: teacherSpeech, language: "en-US" }),
});
const audio = new Audio(URL.createObjectURL(await response.blob()));
await audio.play();
```

Piper is GPL-3.0-or-later, and each downloaded voice can have its own license. Review
both before distributing a device image or commercial application.

## whisper.cpp speech input

whisper.cpp turns an English or Vietnamese microphone recording into text locally.
ClassroomAI uses the official multilingual `small` model with automatic language
detection. It is about 465 MiB on disk, does not require Gemma, and runs on CPU only
while processing a recording. `CLASSROOM_WHISPER_USE_GPU=0` is the safe default because
it prevents Whisper from competing with llama.cpp for Metal/unified GPU memory.

On macOS:

```bash
brew install whisper-cpp ffmpeg
mkdir -p models/speech
curl --location --fail --continue-at - \
  --output models/speech/ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
```

On the Intel Windows or Linux device, install FFmpeg and build or install
`whisper-cli` using the official
[whisper.cpp instructions](https://github.com/ggml-org/whisper.cpp). The Python API
still runs in the existing `classroom-ai` environment; whisper.cpp is a native command,
not another Conda environment.

Restart the API after installation. Send a browser recording or audio file as multipart
form data:

```bash
curl -X POST http://127.0.0.1:8000/v1/audio/transcriptions \
  -F file=@student.webm
```

The response is:

```json
{"text":"Can an eagle fly?"}
```

The reference browser app's **Speak** button first calibrates to the current room noise,
waits for sustained speech, and automatically stops after about 1.2 seconds of silence.
This boundary detection uses Web Audio signal energy and does not load another model.
The student can still press **Finish**, and recording is capped at 30 seconds. The audio
is then transcribed and submitted to the normal student message endpoint. The API
accepts at most 15 MiB and processes at most the first 60 seconds. FFmpeg normalizes
browser formats to the 16-bit, 16 kHz mono WAV input expected by whisper.cpp.

Energy-based detection rejects brief bumps and adapts to steady background noise, but
it cannot tell the student's voice from another person speaking nearby. If classroom
testing shows that limitation is material, replace only this browser gate with a small
specialized VAD; Gemma still should not be used to detect audio boundaries.

The defaults are configurable with `CLASSROOM_WHISPER_MODEL`,
`CLASSROOM_WHISPER_LANGUAGE`, `CLASSROOM_WHISPER_COMMAND`,
`CLASSROOM_WHISPER_USE_GPU`, `CLASSROOM_FFMPEG_COMMAND`, and
`CLASSROOM_WHISPER_THREADS`.

## CPU-only face recognition

The vision scope is now limited to face recognition. There is no raised-hand detector
and no general vision-language model. The local pipeline is:

```text
camera image -> YuNet face box -> SFace embedding -> cosine database match
```

Install OpenCV in the existing environment and download the two official ONNX models:

```bash
conda activate classroom-ai
pip install -r requirements-face.txt
python scripts/download_face_models.py
```

YuNet and SFace both run on CPU. The default cosine threshold is `0.45`, which is more
conservative than OpenCV's example threshold of `0.363`; it is still only a starting
point. Calibrate the threshold with consented photos from the actual camera, distance,
angles, and classroom lighting. A face below the threshold is returned as unknown.

### Trusted command-line enrollment

An administrator can enroll from a known local image:

```bash
python scripts/manage_faces.py enroll \
  --image /path/to/one-clear-face.jpg \
  --subject-id student-17 \
  --display-name "Student 17" \
  --consent-reference guardian-form-2026-017
```

The image must contain exactly one detected face. The source photo is read to create
the embedding but is not copied into the database. List or delete records with:

```bash
python scripts/manage_faces.py list
python scripts/manage_faces.py delete \
  --subject-id student-17 \
  --confirm student-17
```

### Consent-first browser enrollment

The reference browser app never enrolls a face automatically. After repeated unknown
results it displays a warning, explains exactly what will be stored, and requires the
person to enter a display name and check a consent box. It then submits three separate
frames to:

```http
POST /v1/faces/enroll
Content-Type: application/json

{
  "image_base64": "<base64 JPEG>",
  "subject_id": "self-generated-browser-id",
  "display_name": "Student One",
  "consent_confirmed": true,
  "consent_reference": "browser-self-enrollment:2026-08-16T10:00:00.000Z"
}
```

The endpoint rejects `false` or missing consent. Every submitted frame must contain
exactly one detected face. Only the SFace embeddings, identity fields, model hash, and
consent reference enter SQLite; the JPEG frames are not stored. This browser workflow
is suitable for a supervised local prototype, but production use should add guardian
policy, authentication/authorization, audit logs, retention expiry, and a visible
self-service deletion control.

### App recognition request

The app sends a compressed snapshot. AI Core—not the browser—creates the embedding:

```http
POST /v1/faces/recognize
Content-Type: application/json

{"image_base64":"<base64 JPEG or a base64 data URL>"}
```

Each returned face has a normalized box, detection confidence, and either a match or
an unknown result:

```json
[
  {
    "bounds": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.3, "y_max": 0.6},
    "detection_score": 0.98,
    "subject_id": "student-17",
    "display_name": "Student 17",
    "similarity": 0.72
  },
  {
    "bounds": {"x_min": 0.5, "y_min": 0.2, "x_max": 0.7, "y_max": 0.6},
    "detection_score": 0.95,
    "subject_id": null,
    "display_name": null,
    "similarity": null
  }
]
```

Keep the API bound to `127.0.0.1` and restrict `CLASSROOM_CORS_ORIGINS` to the real
classroom app origin. Do not publish the recognition endpoint directly to a network.

The database stores normalized SFace vectors, student IDs, display names, the exact
SFace model hash, and consent references. It never stores photos. Treat it as biometric
data: encrypt the device, restrict access, define retention/deletion rules, and never
use recognition alone for attendance, grading, discipline, or access control.
