# Piper voice files

Voice weights are local runtime data and are ignored by Git.

Use the existing `classroom-ai` Conda environment:

```bash
conda activate classroom-ai
pip install -r requirements-audio.txt
python -m piper.download_voices --download-dir voices \
  en_US-lessac-medium vi_VN-vais1000-medium
```

The command downloads the `.onnx` model and `.onnx.json` configuration for both
default voices:

- `en_US-lessac-medium.onnx`
- `en_US-lessac-medium.onnx.json`
- `vi_VN-vais1000-medium.onnx`
- `vi_VN-vais1000-medium.onnx.json`

Use `CLASSROOM_PIPER_VOICE` for English and
`CLASSROOM_PIPER_VIETNAMESE_VOICE` for Vietnamese. Both voices load lazily: the
Vietnamese model uses memory only after a Vietnamese explanation is requested.
Review each voice's `MODEL_CARD` before distribution; individual voice licenses
may differ from Piper's GPL-3.0-or-later code license.
