# ClassroomAI technical evaluation

This folder contains repeatable checks for the probabilistic parts of ClassroomAI.
The normal unit tests remain in `tests/`.

## Evaluation profile

The project uses a small, context-specific TEVV profile instead of one generic chatbot
score:

- ISO/IEC 25010:2023 for software product quality
- ISO/IEC 25059:2023 for AI-specific correctness, robustness, transparency, and control
- NIST AI RMF 1.0 and its Generative AI Profile for risk management
- HELM's scenario coverage and multi-metric principles
- OWASP Top 10 for LLM Applications 2025 for security probes

The profile evaluates the complete classroom appliance across seven weighted areas:

| Area | Weight |
| --- | ---: |
| Teaching and functional correctness | 25% |
| Reliability and robustness | 15% |
| Performance efficiency | 15% |
| Security, privacy, and child safety | 20% |
| Interaction, accessibility, and usability | 10% |
| Maintainability and portability | 10% |
| Transparency and governance | 5% |

An overall score is useful for tracking, but release gates override it. A system cannot
be called classroom-ready while a critical child-safety, biometric, authentication, or
target-device validation gate remains open.

## Run the live chatbot scenarios

Start llama.cpp and the ClassroomAI API, then run:

```bash
conda activate classroom-ai
python evaluation/run_chatbot_eval.py \
  --base-url http://127.0.0.1:8000 \
  --runs 3 \
  --output evaluation/results/chatbot-latest.json
```

The runner creates an isolated API session for each scenario, follows classroom actions,
deletes the session afterward, records latency, and applies deterministic assertions. A
passing assertion means the response followed the tested contract; it is not proof of
pedagogical quality. Review the saved raw responses as well.

Use `--strict` in CI to return a non-zero status when any scenario fails.
Use `--scenario-id interactive_quiz --runs 10` to isolate a flaky behavior.

Run local component latency smoke tests with:

```bash
python evaluation/run_component_benchmark.py \
  --base-url http://127.0.0.1:8000 \
  --output evaluation/results/components-latest.json
```

This covers API health, Piper, Piper-to-whisper transcription, a synthetic YuNet/SFace
smoke test, the frontend page, and the VRM asset. It does not claim real-person face
identification accuracy.

## Run deterministic verification

```bash
python -m pytest -q
cd frontend && pnpm build
```

The dated assessment in `docs/` records the exact environment, evidence, limitations,
scores, and release gates. Do not compare performance results across devices without
recording the CPU, RAM, runtime build, context size, and model checksum.
