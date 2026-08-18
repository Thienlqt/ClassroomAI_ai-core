# ClassroomAI full technical assessment

**Assessment date:** 16 August 2026  
**Assessed state:** local working tree on branch `agent/initial-ai-core`, based on commit
`2e37c97` plus uncommitted frontend, speech-input, face-enrollment, and evaluation work  
**Host:** Apple M4 MacBook Pro, 10 CPU cores, 16 GB unified memory, macOS 26.5.2  
**Model:** Gemma 4 E4B IT QAT Q4_0 GGUF, SHA-256
`676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee`  
**Runtime:** llama.cpp, 8,192-token context, one inference slot  
**Assessment confidence:** moderate for the current Mac prototype; low for the planned
Intel CPU device and real classroom use because those environments were not tested

## Executive verdict

**Overall evidence-weighted score: 59/100 — functional prototype, not classroom-ready.**

ClassroomAI is a credible supervised contest prototype. It has a clean local architecture,
bounded tools, a usable browser interface, local speech, and privacy-aware face storage.
On the current M4 Mac, normal answers are fast and the individual speech and vision
components operate successfully.

It should not yet be described as reliable enough for an unattended classroom pilot.
The largest measured defect is the core interactive action: in an isolated ten-run test,
Gemma produced a valid `ui.show_choices` action only **2/10 times**. Several failures
printed malformed tool syntax and the hidden correct answer into ordinary speech. A
second critical finding is that `/health` returned `200 OK` while llama.cpp was stopped;
all 24 attempted chat checks then failed with unhandled HTTP 500 responses.

Face recognition passed only a synthetic-image execution test. No false-acceptance,
false-rejection, demographic, lighting, distance, or classroom-camera study has been
performed. It must not be used for attendance, grading, discipline, or access control.

### Release decision

- **Supervised contest demonstration:** conditional go, after fixing quiz tool enforcement
  and verifying the full demo immediately before presentation.
- **Small supervised usability study:** no-go until child-safety review, consent procedure,
  model-readiness health, and data deletion are implemented.
- **Real classroom deployment:** no-go.
- **16 GB Intel target device:** performance verdict pending; no measurement exists yet.

## Why this framework fits

No single chatbot score covers a local multimodal classroom appliance. This assessment
therefore uses a project-specific TEVV profile derived from:

- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html), whose product-quality
  model covers an ICT product rather than only its model.
- [ISO/IEC 25059:2023](https://www.iso.org/standard/80655.html), the AI-specific SQuaRE
  extension for qualities including correctness, robustness, transparency, and control.
- [NIST AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) and the
  [Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) for
  validity, safety, security, privacy, transparency, fairness, and risk treatment.
- [HELM](https://crfm.stanford.edu/2022/11/17/helm.html) for broad scenario coverage,
  multiple metrics, repeatability, and explicit documentation of missing evaluations.
- [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/) for
  prompt injection, information disclosure, supply-chain, and operational security.

The final score is weighted for this product's intended context. Release gates override
the numeric score: a high average cannot compensate for an unresolved critical child,
biometric, or core-function risk.

## Scope and architecture assessed

```text
Vue classroom UI
  -> FastAPI session and tool boundary
      -> Gemma 4 E4B through llama.cpp
  -> Piper local speech output
  -> whisper.cpp local speech input
  -> YuNet detection -> SFace embedding -> cosine SQLite store

Hermes teacher planner: installed but isolated and not in the student runtime
```

In scope: code, configuration, tests, current local model files, live API behavior,
frontend production build, speech, synthetic face detection, privacy design, dependency
advisories, documentation, and operational failure behavior.

Not fully assessed: teaching effectiveness with students, real classroom audio, real-person
face accuracy, bias/fairness, browser FPS, screen-reader use, long sessions, concurrency,
power consumption, the planned Intel device, or the experimental Hermes 64K workflow.

## Scorecard

Scores use a 0–100 maturity scale for each area. Weighted points sum to 59/100.

| Quality area | Weight | Score | Weighted | Evidence-based finding |
| --- | ---: | ---: | ---: | --- |
| Teaching and functional correctness | 25% | 60 | 15.0 | Normal teaching, image action, bilingual help, injection refusal, and a medical boundary worked, but quiz tool reliability was 20% and no learning-outcome study exists. |
| Reliability and robustness | 15% | 48 | 7.2 | 39/39 deterministic tests pass, but dependency outage is invisible to health, becomes HTTP 500, sessions are unbounded, and no soak/concurrency test exists. |
| Performance efficiency | 15% | 72 | 10.8 | M4 response latency and local components are responsive; frontend/VRM payloads are large and Intel CPU performance is unknown. |
| Security, privacy, and child safety | 20% | 45 | 9.0 | Local binding, schema validation, consent UI, and no raw-photo storage are good; there is no API authentication, rate limit, encrypted biometric store, verified consent authority, or comprehensive child-safety policy. |
| Interaction, accessibility, usability | 10% | 68 | 6.8 | Clear browser UI, subtitles, keyboard-friendly controls, local camera preview, and fallbacks exist; no browser E2E, contrast, screen-reader, or classroom usability study was run. |
| Maintainability and portability | 10% | 72 | 7.2 | Model/runtime adapters and components are modular, dependencies are pinned, and guides are strong; CI, coverage, linting, frontend tests, and Intel validation are absent. |
| Transparency and governance | 5% | 55 | 2.8 | Model checksums, third-party notices, local-data explanations, and limitations are documented; there is no project license, model/system card, formal risk owner, incident plan, or retention schedule. |
| **Total** | **100%** |  | **58.8 ≈ 59** | **Prototype maturity** |

## Measured evidence

### Deterministic software verification

| Check | Result |
| --- | --- |
| Python tests | **39/39 passed** in 0.54 seconds |
| Frontend production build | Passed with Vite 8.2.1 |
| Frontend JS bundle | 821.92 kB minified, 216.25 kB gzip; Vite emitted a >500 kB chunk warning |
| Compiled frontend folder | About 3.5 MiB |
| VRM teacher asset | 26,781,812 bytes, loaded successfully over HTTP |
| npm production advisory audit | No known vulnerabilities found on 16 August 2026 |
| Python requirements advisory audit | No known vulnerabilities found on 16 August 2026 |
| Test coverage percentage | Not measured; `pytest-cov` is not part of the environment |
| CI pipeline | None found |

“No known vulnerabilities” describes the advisory databases at the time of the query; it
does not prove that the code or dependencies are vulnerability-free.

### Live chatbot evaluation

The raw evidence is in
`evaluation/results/chatbot-2026-08-16-m4.json` and
`evaluation/results/quiz-reliability-2026-08-16-m4.json`.

| Metric | Result |
| --- | ---: |
| Broad scenario checks | **22/24 passed (91.7%)** |
| Broad first-response latency p50 | **1.635 s** |
| Broad first-response latency p95 | **2.626 s** |
| Broad maximum | **3.532 s** |
| Isolated quiz action reliability | **2/10 passed (20%)** |
| Prompt-injection disclosure probe | 3/3 refused without detected prompt text leakage |
| Medical-dose boundary probe | 3/3 refused and directed the child to an adult/doctor boundary |
| Approved eagle image action | 3/3 valid in the broad run |

The prompt-injection and medical results are encouraging but far too small to establish
general safety. They are repeated samples of one scenario, not a comprehensive attack or
child-safety set.

The quiz failures took three forms:

1. Multiple-choice content returned as plain speech instead of a semantic UI action.
2. `show_choices{...}` printed as malformed text rather than emitted as a tool call.
3. `correct_answer` appeared inside that text, leaking the answer the browser protocol is
   specifically designed to hide.

Because the API accepts any non-empty model text as valid speech, it does not currently
detect or repair these failures.

### Inference performance on this Mac

llama.cpp logs showed approximately **31–34 generated tokens/second** in the observed
runs. The first cold request evaluated a 929-token prompt in about 2.58 seconds and
generated 35 tokens in about 1.09 seconds. Later requests benefited from prompt-prefix
caching and were typically much faster.

Observed process RSS was approximately 755 MiB for `llama-server` and 205 MiB for the
Python API. This is **not total model memory** on Apple Silicon: it excludes important
memory-mapped and Metal/unified-memory accounting, so it must not be used as the device
RAM requirement. The GGUF alone is about 4.8 GiB; the local `models/` directory is about
5.3 GiB and the Piper voice adds about 60 MiB.

### Local component benchmark

Raw evidence: `evaluation/results/components-2026-08-16-m4.json`.

| Component | Current-Mac result | Interpretation |
| --- | ---: | --- |
| `/health`, 30 sequential calls | 0–3 ms | Fast endpoint, but not dependency-aware |
| Piper, 3 runs | mean 255 ms; 36–693 ms | Good for short local teacher speech |
| Piper-to-whisper clean synthetic utterance | 940 ms; exact transcript | Execution works; not a classroom-noise accuracy test |
| YuNet/SFace synthetic teacher image | 698 ms; one face at 0.923 detection confidence | Execution works; identity quality is unmeasured |
| Frontend HTML | 3 ms, 574 bytes | Local server overhead is negligible |
| VRM transfer | 33 ms, 26.8 MB | Local transfer is fast; browser parse/render/FPS is unmeasured |

The face scan interval is 1.6 seconds. A 698 ms inference fits on this Mac, but the planned
Intel CPU could be slower and must be measured under simultaneous Gemma, speech, camera,
and browser load.

### Dependency-outage experiment

With the API running and llama.cpp stopped:

- `GET /health` returned `200` with `{"status":"ok"}`.
- All 24 chat attempts returned HTTP 500.
- The unhandled server cause was `openai.APIConnectionError`.

This means an operator or frontend cannot distinguish “API process exists” from “teacher
is ready.” It also exposes an internal server error instead of a controlled `503 Service
Unavailable` response.

## Detailed quality findings

### Functional and pedagogical quality

Strengths:

- Lesson text and prompt are separate from Python code.
- Approved images and tool schemas are bounded and server-validated.
- The correct quiz answer is intentionally omitted from a valid browser action.
- Tool results return to Gemma, allowing feedback based on the student's choice.
- Responses were usually concise, beginner-friendly, and on the animals lesson.
- Simple Vietnamese support worked in all broad samples, although one sample invented a
  future picture without issuing an image action.

Gaps:

- The defining interactive quiz behavior is not reliable enough.
- The agent validates tool calls, but not whether speech violates an explicit user intent
  that required a tool.
- Initial speech is not passed through the unavailable-visual policy; only post-tool
  feedback is checked.
- There is no student proficiency model, mastery score, spaced repetition, learning
  progression, or outcome measurement. Current adaptation is conversation context only.
- Only one small English lesson and two UI tools are implemented.
- No teacher-authored gold dataset or human pedagogy rubric exists.

### Reliability and operations

Strengths:

- Schema validation rejects malformed actions and bad action results.
- Per-session locks prevent two turns from corrupting the same conversation.
- Speech and face adapters serialize native inference where required.
- Model, API, and optional component launch instructions are documented.

Gaps:

- `/health` has no llama.cpp, Piper, whisper, vision, model-file, or database readiness.
- Model connection exceptions are not mapped into stable API errors.
- `SessionStore` is process-local, unbounded, has no TTL, and loses all sessions on restart.
- Message history is never summarized or truncated before the 8,192-token limit.
- There is no request ID, structured log, metric, tracing, watchdog, restart policy, or
  error-rate alert.
- One llama.cpp slot serializes generation; classroom concurrency behavior is unmeasured.
- No startup, shutdown, one-hour soak, forced-crash recovery, or disk-full test exists.

### Security, privacy, and safety

Strengths:

- Services default to `127.0.0.1`.
- Pydantic limits text and encoded-image sizes; tool schemas forbid extra arguments.
- Local image IDs are catalogued rather than arbitrary filesystem paths.
- Browser camera and microphone require explicit browser permission.
- Face photos are decoded in memory and not written to the biometric database.
- SQLite stores normalized embeddings and model identifiers, with CLI deletion available.
- Enrollment UI explains the storage and requires a checkbox.

Gaps:

- API endpoints have no authentication or authorization. Any local process or allowed web
  origin can recognize faces, submit a self-asserted `consent_confirmed: true`, or create
  embeddings.
- The database is not application-encrypted, has no retention expiry, and has no access or
  deletion audit trail.
- Consent is a client assertion, not verified adult/guardian authorization.
- The browser has no self-service view/delete function despite telling the user deletion is
  possible through an administrator tool.
- There is no rate limit, request quota, CSRF design review, security header policy, or
  explicit production disable-switch for biometric enrollment.
- llama.cpp reported permissive CORS and no API key. Loopback binding reduces exposure but
  does not replace process-to-process authentication.
- System instructions contain teaching/tool rules but not a complete child-safety policy.
- Prompt injection, unsafe content, self-harm, abuse disclosure, sexual content, hate,
  personal data elicitation, and inappropriate relationship boundaries lack a systematic
  evaluation set.
- No privacy impact assessment, guardian consent artifact, fairness study, or applicable-law
  review has been completed.

### Usability and accessibility

Strengths:

- One local URL serves the complete app; normal users do not need Node.js.
- The UI provides typed input, voice input, subtitles, teacher speech, images, quizzes,
  camera preview, clear scores, and a static-avatar fallback.
- Basic semantic controls, labels, focus styling, `aria-live`, and reduced-motion support
  are present.
- The browser separates face detection confidence from identity similarity.

Gaps:

- No real browser E2E test was run for this assessment.
- No frame-rate, WebGL fallback, camera-denial, microphone-denial, autoplay, responsive
  overlap, or low-end integrated-GPU measurement exists.
- No WCAG contrast, keyboard-only, screen-reader, font scaling, caption timing, or classroom
  projection-distance review exists.
- Automatic TTS may be blocked by browser autoplay policy; failure is only logged.
- The interface does not expose data deletion or a clear “disable biometrics” administrator
  control.

### Maintainability, portability, and supply chain

Strengths:

- Provider-neutral model messages isolate Ollama and llama.cpp differences.
- Prompt, lesson, tools, audio, vision, storage, API, and Vue components have clear boundaries.
- Python and frontend versions are pinned; model files have checksums and are kept out of Git.
- The production frontend is committed so an app user does not need the Node toolchain.
- Both npm and Python advisory checks found no known vulnerable pinned packages today.

Gaps:

- There is no CI workflow, code formatter/linter gate, test coverage threshold, SBOM, signed
  artifact, or automated recurring dependency audit.
- The repository has third-party notices but no top-level license for ClassroomAI's own code.
- The compiled frontend duplicates generated assets already present in source.
- The 822 kB JavaScript chunk should be code-split or explicitly accepted for the offline
  appliance.
- Intel CPU, Windows, Linux, OpenVINO/NPU, and clean-clone installation are documented but
  not exercised by automated tests.
- Hermes is installed and has isolated configuration, but its 64K context mode was not run
  in this assessment and it is not integrated into the student system.

## Risk register and required actions

| Priority | Risk | Evidence | Required treatment |
| --- | --- | --- | --- |
| P0 | Quiz/tool contract unreliable and can leak the hidden answer | 2/10 valid actions; malformed tool text included `correct_answer` | Force or deterministically enforce `show_choices` for explicit quiz intent; reject pseudo-tool speech; set controlled sampling; require ≥95/100 clean trials before demo sign-off. |
| P0 | Biometric capability is not deployment-validated | Only one synthetic face smoke test; no FAR/FRR or fairness data; no endpoint auth | Disable enrollment by default outside supervised demo; add authorization, encryption, retention/deletion, consent governance, and consented validation dataset before any pilot. |
| P0 | Child-safety controls are not comprehensive | One repeated medical boundary only; prompt lacks general child-safety policy | Define age-appropriate safety policy, deterministic escalation paths, prohibited advice, abuse/self-harm handling, red-team set, and human review. |
| P1 | Health endpoint produces false readiness and chat emits 500 on model outage | Reproduced with 24/24 failures | Add live/deep readiness, catch gateway errors as 503, frontend retry guidance, watchdog/restart, and tests. |
| P1 | Target Intel performance unknown | All measurements are on Apple M4 | Run the same JSON scenarios and component benchmark on the exact 16 GB Intel device under simultaneous load. |
| P1 | Conversation state can exhaust RAM/context | Unbounded in-memory sessions and history | Add TTL/LRU limits, maximum turns/tokens, summarization, explicit capacity behavior, and persistence policy. |
| P1 | Real speech quality unknown | Exact result used clean Piper-generated audio | Build a consented classroom corpus with noise, distance, children, accents, and Vietnamese-influenced English; report WER and failure rate. |
| P1 | Frontend behavior not automatically validated | No browser E2E/accessibility suite | Add Playwright component journeys, camera/mic mocks, axe checks, and target-device FPS/memory capture. |
| P2 | Operational and supply-chain assurance is manual | No CI, coverage, SBOM, recurring audit | Add CI for tests/build/evals, coverage threshold, audit jobs, SBOM, and release checksum manifest. |
| P2 | Governance and licensing incomplete | No root project license/system card/retention policy | Choose a project license, create a system card, name risk/data owners, document incident response and retention. |

## Acceptance criteria for the next assessment

These targets turn “better” into measurable readiness:

| Gate | Minimum target |
| --- | --- |
| Explicit quiz intent -> valid `ui.show_choices` | ≥95/100 trials; 0 hidden-answer leaks |
| Approved image intent -> valid image action | ≥99/100 trials |
| Prompt/tool-policy leakage | 0/50 diverse attacks |
| Child high-risk response set | 100% deterministic escalation on critical cases; human-reviewed rubric |
| Model dependency outage | `/ready` fails; chat returns controlled 503; no traceback to client |
| Long-session robustness | 100-turn test completes within configured token/memory bounds |
| One-hour supervised soak | <1% failed turns; no unbounded RSS growth |
| Current-Mac first response | p95 ≤3 seconds for the fixed scenario set |
| Intel-device first response | establish baseline, then target p95 ≤5 seconds for short turns |
| Piper synthesis | p95 ≤1 second for one short classroom sentence |
| Real classroom STT | WER ≤15% on the agreed English corpus, with subgroup results |
| Face verification, if retained | FAR/FRR thresholds defined before testing; subgroup and operating-condition results; no use before approval |
| Accessibility | Keyboard journey passes; no critical automated WCAG findings; human screen-reader check |
| Supply chain | CI tests/build/audits pass; release has SBOM and checksums |

## Recommended remediation sequence

1. Make explicit UI intents deterministic. Add `tool_choice` support or an application-level
   intent guard, controlled temperature/seed, pseudo-tool-text detection, and a retry that
   cannot return hidden arguments as speech.
2. Add dependency-aware readiness and stable 503 handling before further benchmarking.
3. Add bounded sessions and context management.
4. Add a dedicated child-safety policy and red-team dataset reviewed by an educator or
   child-safety specialist.
5. Keep biometric enrollment disabled by default until authentication, verified consent,
   deletion, retention, encryption, and real accuracy/fairness evaluation exist.
6. Run the supplied evaluation tools on the actual Intel device with Gemma, Piper, Whisper,
   face scanning, and the browser active together.
7. Add browser E2E/accessibility/performance tests and a one-hour soak.
8. Add CI, coverage, scheduled dependency audits, an SBOM, a root license, and a system card.

## Reproduce this assessment

With llama.cpp and the API running:

```bash
conda activate classroom-ai
python -m pytest -q

python evaluation/run_chatbot_eval.py \
  --base-url http://127.0.0.1:8000 \
  --runs 3 \
  --output evaluation/results/chatbot-latest.json

python evaluation/run_chatbot_eval.py \
  --base-url http://127.0.0.1:8000 \
  --scenario-id interactive_quiz \
  --runs 10 \
  --output evaluation/results/quiz-reliability-latest.json

python evaluation/run_component_benchmark.py \
  --base-url http://127.0.0.1:8000 \
  --output evaluation/results/components-latest.json

cd frontend
pnpm build
pnpm audit --prod --audit-level low
```

Raw outputs should always be retained with the model checksum, llama.cpp build, device,
context size, and sampling settings. A later score is comparable only when those conditions
are controlled.
