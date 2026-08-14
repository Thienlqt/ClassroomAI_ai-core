# Optional local components

These components are deliberately separate from the child-facing Gemma agent. Install
only what the device needs, using the existing `classroom-ai` Conda environment.

## Hermes teacher assistant

Hermes is an optional adult-only planning shell around the same llama.cpp endpoint. It
does not replace `ClassroomAgent`, its system prompt, classroom tools, or HTTP session
protocol. The launcher restricts Hermes to its memory toolset; it does not give the
model terminal, browser, web, or file tools.

Install Hermes with its official installer:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

This is Hermes's own managed CLI installation, not another Conda environment. The
ClassroomAI Python packages remain in the existing `classroom-ai` environment.

Hermes documents 64,000 tokens as its minimum local context because its agent prompt
and tool definitions are much larger than a normal chat prompt. Stop the normal 8K
llama.cpp server, then start the same Gemma model in a separate teacher session:

```bash
conda activate classroom-ai
CLASSROOM_LLAMA_CONTEXT_SIZE=65536 python scripts/start_model.py
```

In a second terminal:

```bash
conda activate classroom-ai
python scripts/start_hermes_teacher.py
```

The launcher copies the reviewed configuration and `SOUL.md` into
`.runtime/hermes-teacher` on first use. That directory is ignored by Git and keeps
teacher memory separate from the source tree. It does not modify the source templates
when Hermes updates its working configuration.

This mode is experimental with a 4B model. A 64K context consumes substantially more
RAM and prompt processing time; benchmark it on the real device before relying on it.
For the classroom demo, keep the smaller, faster student agent as the default.

## Piper TTS

Piper turns returned teacher speech into a WAV file locally. It runs on CPU and is a
good fit for the planned Intel device.

```bash
conda activate classroom-ai
pip install -r requirements-audio.txt
python -m piper.download_voices --download-dir voices en_US-lessac-medium
```

Restart the AI Core API after installation. The app sends:

```http
POST /v1/speech
Content-Type: application/json

{"text":"Great job! The eagle can fly."}
```

The response body is `audio/wav`. In a browser:

```js
const response = await fetch("http://127.0.0.1:8000/v1/speech", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: teacherSpeech }),
});
const audio = new Audio(URL.createObjectURL(await response.blob()));
await audio.play();
```

Piper is GPL-3.0-or-later, and each downloaded voice can have its own license. Review
both before distributing a device image or commercial application.

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

### Trusted enrollment

Enrollment is a local administrator operation, not a browser API:

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
