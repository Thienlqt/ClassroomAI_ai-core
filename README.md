# Spatial AI Classroom — AI Core

This repository runs the local Gemma English-teacher agent. It exposes structured
classroom actions over HTTP, while the classroom app owns all visual rendering and
student interaction.

## Project structure

```text
classroom_ai/             # Agent, runtime adapters, API, sessions, and policies
assets/images/            # Approved offline images and catalog
frontend/                 # Reference browser classroom app
lessons/                  # Bounded lesson content
models/                   # Local GGUF files; model weights are ignored by Git
prompts/                  # Editable model prompts
scripts/                  # Cross-platform model and API launchers
tool_definitions/         # Provider-neutral function/tool JSON schemas
tests/                    # Agent, tool, adapter, launcher, and API tests
```

`english_agent.py` is the terminal demo. `api.py` is the small Uvicorn entry point for
app integration. Model-specific request translation is isolated in
`classroom_ai/model.py`.

## Recommended model and runtime

The tested default configuration is:

- Model: **Google Gemma 4 E4B instruction-tuned QAT Q4_0 GGUF**
- Model repository: [`google/gemma-4-E4B-it-qat-q4_0-gguf`](https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf)
- File: `models/gemma-4-E4B_q4_0-it.gguf`
- Runtime: **llama.cpp** using its OpenAI-compatible `llama-server`
- Python: **3.11**
- Tested host: Apple Silicon macOS with llama.cpp build `b10360`
- Planned host: 16 GB Intel AI PC, initially using CPU inference

The model is about 4.8 GiB on disk. The launch script uses an 8,192-token context and
one server slot to leave working memory for the operating system and ClassroomAI. It
disables multimodal loading because the current app displays catalogued images instead
of sending visual input to Gemma.

The exact download URL, size, checksum, and platform-specific verification commands are
in [`models/README.md`](models/README.md). Model weights are ignored by Git and must not
be pushed to GitHub.

## Setup on this Mac

Use the existing Conda environment; do not create another one:

```bash
conda activate classroom-ai
pip install -r requirements.txt
```

Install llama.cpp with Homebrew:

```bash
brew install llama.cpp
```

Download and verify the official model by following [`models/README.md`](models/README.md).

Open two terminals in the repository. Start the model first:

```bash
conda activate classroom-ai
python scripts/start_model.py
```

Then start ClassroomAI:

```bash
conda activate classroom-ai
python scripts/start_api.py --reload
```

The launchers set the llama.cpp provider, model alias, ports, context size, Jinja tool
calling, and other safe local defaults. Run either launcher with `--dry-run` to inspect
its command without starting a process.

## Setup on the 16 GB Intel device

Use the same model and the same Python launchers. Install a current llama.cpp release:

- Windows: `winget install llama.cpp`
- Linux: use the [official installation/build guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/install.md)

Set up Python 3.11, download the model as described in `models/README.md`, then run:

```text
python scripts/start_model.py
python scripts/start_api.py
```

Plain CPU execution is the reliable starting point. Let llama.cpp choose the thread
count automatically first. If benchmarking shows that a fixed physical-core count is
better, set `CLASSROOM_LLAMA_THREADS` before starting the model. For example, on an
8-core Linux machine:

```bash
CLASSROOM_LLAMA_THREADS=8 python scripts/start_model.py
```

On Windows PowerShell:

```powershell
$env:CLASSROOM_LLAMA_THREADS = "8"
python scripts/start_model.py
```

Intel NPU execution requires a special llama.cpp OpenVINO build and remains experimental,
so it is not enabled by these launchers. First establish a CPU quality/performance
baseline on the real device, then evaluate the
[OpenVINO backend](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/OPENVINO.md)
without changing the ClassroomAI application code.

## Runtime settings

The defaults work without exporting environment variables. Copy `.env.example` as a
reference when a process manager or deployment system will load the values.

| Setting | Default | Purpose |
| --- | --- | --- |
| `CLASSROOM_MODEL_PROVIDER` | `llama_cpp` | Selects the model adapter |
| `CLASSROOM_MODEL` | `gemma4-e4b` | Model name sent to the server |
| `CLASSROOM_MODEL_FILE` | `models/gemma-4-E4B_q4_0-it.gguf` | Local model used by the launcher |
| `CLASSROOM_OPENAI_BASE_URL` | `http://127.0.0.1:8080/v1` | llama.cpp API endpoint |
| `CLASSROOM_LLAMA_CONTEXT_SIZE` | `8192` | Model context allocated per slot |
| `CLASSROOM_LLAMA_PARALLEL` | `1` | Concurrent llama.cpp server slots |
| `CLASSROOM_LLAMA_THREADS` | automatic | Optional Intel CPU tuning |

### Optional Ollama adapter

The adapter remains available for comparison, but Ollama is no longer installed or
required by default. Install its optional Python dependency and select it at startup:

```bash
pip install -r requirements-ollama.txt
export CLASSROOM_MODEL_PROVIDER=ollama
export CLASSROOM_MODEL=gemma4:e4b
export OLLAMA_HOST=http://127.0.0.1:11434
python scripts/start_api.py
```

`OllamaGateway` and `OpenAICompatibleGateway` translate the same provider-neutral
conversation history. Switching providers does not require changes to the agent, tools,
prompt, lessons, API, or frontend.

## Run the terminal demo

Start `scripts/start_model.py` first, then in another terminal:

```bash
conda activate classroom-ai
python english_agent.py
```

## Run the API for the classroom app

Start the model and API launchers as shown above. You can also run Uvicorn directly
because llama.cpp is now the configuration default:

```bash
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Useful development pages:

- Reference classroom app: `http://127.0.0.1:8000/`
- API status: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

The reference classroom app is served by the same FastAPI process and needs no Node.js
or separate frontend command. It provides:

- student message input and teacher subtitles
- projector-friendly `ui.show_choices` buttons
- actual rendering of `ui.show_image` assets
- automatic action-result callbacks using `call_id`
- one browser-local session ID and a **New lesson** reset
- responsive, keyboard-accessible loading and error states

The app team can run it directly as an integration reference or copy the request/action
logic from `frontend/app.js` into their own UI framework. AI Core remains responsible
for conversation state and answer checking; the browser owns only display and input.

The prototype allows browser requests from any origin. Set a restricted comma-separated
list before deployment, for example:

```bash
export CLASSROOM_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## App integration protocol

The app uses a `session_id` of its choice, such as a classroom, teacher, or lesson ID.
Keep using the same ID to preserve that conversation's context.

### 1. Send a student message

```http
POST /v1/sessions/class-7a/messages
Content-Type: application/json

{
  "message": "Give me an interactive animal question."
}
```

Gemma can return normal teacher speech:

```json
{
  "type": "speech",
  "speech": "Hello! Let's learn about animals.",
  "action": null
}
```

Or it can return a choice action:

```json
{
  "type": "action",
  "speech": null,
  "action": {
    "call_id": "generated-id",
    "type": "ui.show_choices",
    "payload": {
      "question": "Which animal can fly?",
      "choices": ["Eagle", "Fish", "Dog"]
    }
  }
}
```

The correct answer is intentionally not sent to the app. AI Core keeps it and checks
the student's selection.

### 2. Render the action and return the result

After the student chooses an answer, return the exact displayed choice using the
`call_id` from the action:

```http
POST /v1/sessions/class-7a/actions/generated-id/result
Content-Type: application/json

{
  "result": {
    "selected": "Eagle"
  }
}
```

AI Core checks the answer, gives the result to Gemma, and returns teacher speech:

```json
{
  "type": "speech",
  "speech": "Great! The eagle can fly.",
  "action": null
}
```

For an image action, the app receives:

```json
{
  "call_id": "generated-id",
  "type": "ui.show_image",
  "payload": {
    "image_id": "lion",
    "caption": "Lion",
    "image_url": "/assets/images/lion.png"
  }
}
```

The app displays `http://127.0.0.1:8000/assets/images/lion.png`, then confirms:

```json
{
  "result": {
    "success": true
  }
}
```

Only one action can be pending in a session. The app must finish it before sending
another student message. Reset a conversation with:

```http
DELETE /v1/sessions/class-7a
```

## Minimal frontend example

```js
const API = "http://127.0.0.1:8000";
const sessionId = "class-7a";

async function sendStudentMessage(message) {
  const response = await fetch(`${API}/v1/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return handleAgentOutput(await response.json());
}

async function handleAgentOutput(output) {
  if (output.type === "speech") {
    showTeacherSubtitle(output.speech);
    return;
  }

  const { call_id, type, payload } = output.action;
  let result;

  if (type === "ui.show_image") {
    showImage(`${API}${payload.image_url}`, payload.caption);
    result = { success: true };
  } else if (type === "ui.show_choices") {
    const selected = await showChoices(payload.question, payload.choices);
    result = { selected };
  }

  const response = await fetch(
    `${API}/v1/sessions/${sessionId}/actions/${call_id}/result`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ result }),
    },
  );
  return handleAgentOutput(await response.json());
}
```

`showTeacherSubtitle`, `showImage`, and `showChoices` are functions owned by the app
team. AI Core never controls HTML elements, projector coordinates, or animations.

## Tests

```bash
python -m pytest -q
```
