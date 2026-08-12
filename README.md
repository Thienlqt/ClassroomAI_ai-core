# Spatial AI Classroom — AI Core

This repository runs the local Gemma English-teacher agent. It exposes structured
classroom actions over HTTP, while the classroom app owns all visual rendering and
student interaction.

## Project structure

```text
classroom_ai/
├── agent.py              # Gemma conversation and tool-call orchestration
├── api.py                # FastAPI endpoints used by the classroom app
├── config.py             # Paths and environment settings
├── content.py            # Lesson and image-catalog loading
├── model.py              # Local Ollama adapter
├── policies.py           # Guards against fake/unrendered visual claims
├── prompts.py            # System-prompt template rendering
├── schemas.py            # Shared Pydantic/API data contracts
├── sessions.py           # Prototype in-memory conversation sessions
├── terminal.py           # Local terminal UI adapter
└── tools/
    ├── definitions.py    # Loads JSON definitions sent to Gemma
    └── registry.py       # Validates calls and maps them to UI actions

assets/images/            # Approved offline images and catalog
lessons/                  # Bounded lesson content
prompts/                  # Editable model prompts
tool_definitions/         # Ollama function/tool JSON schemas
tests/                    # Agent, tool, content, and API tests
```

`english_agent.py` remains a small compatibility entry point for the terminal demo.
`api.py` is the small Uvicorn entry point for the app integration.

## Recommended model and runtime

The tested development configuration is:

- Model: **Gemma 4 E4B instruction-tuned**, exposed by Ollama as `gemma4:e4b`
- Runtime: **Ollama**
- Python: **3.11**
- Current development machine: Apple Silicon Mac; target Intel/OpenVINO deployment
  remains future work and must be benchmarked on real Intel hardware.

Ollama currently lists `gemma4:e4b` as a 9.6 GB model with a 128K context window.
See the [official Ollama model page](https://ollama.com/library/gemma4/tags) and the
[official Google Gemma 4 checkpoint](https://huggingface.co/google/gemma-4-E4B).

Ollama is recommended for this prototype because that exact configuration has passed
the tool-call and feedback tests in this repository.

### Python setup

Use the existing environment:

```bash
conda activate classroom-ai
pip install -r requirements.txt
```

For a different machine where the environment does not exist yet:

```bash
conda create -n classroom-ai python=3.11 pip -y
conda activate classroom-ai
pip install -r requirements.txt
```

### Option A — Ollama (recommended and tested)

Install Ollama using its [official download guide](https://ollama.com/download), then:

```bash
ollama pull gemma4:e4b
ollama list
```

Configure AI Core:

```bash
export CLASSROOM_MODEL_PROVIDER=ollama
export CLASSROOM_MODEL=gemma4:e4b
export OLLAMA_HOST=http://127.0.0.1:11434
```

Ollama starts automatically on many desktop installations. If it is not running:

```bash
ollama serve
```

### Option B — llama.cpp (supported adapter, experimental with Gemma 4)

The code can use any server exposing OpenAI-compatible chat completions and tool calls.
`llama-server` provides that API. Install or build it using the
[official llama.cpp guide](https://github.com/ggml-org/llama.cpp), and read its
[server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

llama.cpp requires a compatible **GGUF** instruction-tuned model file. Google's official
checkpoint is not distributed as GGUF, so either convert it with the current llama.cpp
conversion tools or choose a third-party GGUF conversion after checking its model card,
license, checksum, architecture support, and chat template. Do not commit model files;
`*.gguf` and `models/` are ignored by Git.

Start the server with tool calling enabled:

```bash
llama-server \
  --model /absolute/path/to/gemma-4-E4B-it.gguf \
  --alias gemma4-e4b \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 32768 \
  --jinja
```

`--jinja` is important because llama.cpp documents it as the switch for OpenAI-style
function calling. Some GGUFs may require `--chat-template-file` with a tool-compatible
template. Gemma 4 tool calling and some architecture features have had active llama.cpp
compatibility work, so treat this path as experimental and run the complete test/live
evaluation before using it in a demo. Relevant upstream references:

- [llama.cpp function-calling documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md)
- [Gemma 4 E2B/E4B PLE compatibility report](https://github.com/ggml-org/llama.cpp/issues/22243)

Configure AI Core in another terminal:

```bash
export CLASSROOM_MODEL_PROVIDER=llama_cpp
export CLASSROOM_MODEL=gemma4-e4b
export CLASSROOM_OPENAI_BASE_URL=http://127.0.0.1:8080/v1
export CLASSROOM_OPENAI_API_KEY=local-no-key
```

Then run the same terminal or HTTP API commands below. No agent, tool, prompt, lesson,
or frontend code changes are required.

### How runtime switching works

`classroom_ai/model.py` contains two adapters:

- `OllamaGateway` translates the shared conversation into Ollama's message format.
- `OpenAICompatibleGateway` translates it into the OpenAI-compatible format used by
  llama.cpp, including tool-call IDs and JSON-string function arguments.

`CLASSROOM_MODEL_PROVIDER` selects the adapter at startup. Everything above that adapter
uses one provider-neutral message history. Therefore changing runtime should not be a
major code change. The likely work is operational and evaluative: obtaining the correct
model format, selecting the right chat template, starting the server, and rechecking
tool-call accuracy and output quality.

Copy `.env.example` if you want a reference, but export/load the variables in your own
process manager; this prototype does not automatically load `.env` files.

## Run the terminal demo

```bash
conda activate classroom-ai
python english_agent.py
```

## Run the API for the classroom app

Make sure Ollama and `gemma4:e4b` are available, then run:

```bash
conda activate classroom-ai
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Useful development pages:

- API status: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

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
