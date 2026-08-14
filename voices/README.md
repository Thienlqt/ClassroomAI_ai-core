# Piper voice files

Voice weights are local runtime data and are ignored by Git.

Use the existing `classroom-ai` Conda environment:

```bash
conda activate classroom-ai
pip install -r requirements-audio.txt
python -m piper.download_voices --download-dir voices en_US-lessac-medium
```

The command downloads both files required by the default configuration:

- `en_US-lessac-medium.onnx`
- `en_US-lessac-medium.onnx.json`

Set `CLASSROOM_PIPER_VOICE` to a different `.onnx` path to use another Piper
voice. Review the voice's own `MODEL_CARD` before distributing it; individual
voice licenses may differ from Piper's GPL-3.0-or-later code license.
