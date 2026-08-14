# Local model

The default runtime expects this file in this directory:

```text
gemma-4-E4B_q4_0-it.gguf
```

It is the official Google **Gemma 4 E4B instruction-tuned QAT Q4_0 GGUF**:

- Source: <https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf>
- Size: `5,154,941,280` bytes (about 4.8 GiB)
- SHA-256: `676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee`

The model itself is intentionally ignored by Git and must not be committed.

## Download on macOS or Linux

Run from the repository root:

```bash
curl --location --fail --continue-at - \
  --output models/gemma-4-E4B_q4_0-it.gguf \
  'https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf/resolve/main/gemma-4-E4B_q4_0-it.gguf?download=true'
```

Verify it on macOS:

```bash
shasum -a 256 models/gemma-4-E4B_q4_0-it.gguf
```

On Linux, use `sha256sum` instead.

## Download on Windows PowerShell

Run from the repository root:

```powershell
curl.exe --location --fail --continue-at - `
  --output models/gemma-4-E4B_q4_0-it.gguf `
  "https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf/resolve/main/gemma-4-E4B_q4_0-it.gguf?download=true"
```

Verify it:

```powershell
(Get-FileHash models/gemma-4-E4B_q4_0-it.gguf -Algorithm SHA256).Hash
```

The optional multimodal projector is not needed. ClassroomAI currently asks the app to
display catalogued images; it does not send images, video, or audio into the model.
