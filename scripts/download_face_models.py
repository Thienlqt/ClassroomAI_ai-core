#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import urllib.request
from pathlib import Path

try:
    from ._shared import PROJECT_ROOT
except ImportError:  # Direct execution: python scripts/download_face_models.py
    from _shared import PROJECT_ROOT


MODEL_DIR = PROJECT_ROOT / "models" / "vision"
MODELS = {
    "face_detection_yunet_2023mar.onnx": {
        "url": (
            "https://github.com/opencv/opencv_zoo/raw/4.10.0/models/"
            "face_detection_yunet/face_detection_yunet_2023mar.onnx"
        ),
        "sha256": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    },
    "face_recognition_sface_2021dec.onnx": {
        "url": (
            "https://github.com/opencv/opencv_zoo/raw/4.10.0/models/"
            "face_recognition_sface/face_recognition_sface_2021dec.onnx"
        ),
        "sha256": "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(
    url: str, destination: Path, expected_sha256: str, *, force: bool = False
) -> None:
    if destination.exists() and not force:
        if sha256(destination) == expected_sha256:
            print(f"Already present and verified: {destination}")
            return
        raise SystemExit(
            f"Checksum mismatch for existing model: {destination}\n"
            "Inspect it, then rerun with --force to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=destination.name, suffix=".part", delete=False
        ) as temporary:
            shutil.copyfileobj(response, temporary)
            temporary_path = Path(temporary.name)
    actual_sha256 = sha256(temporary_path)
    if actual_sha256 != expected_sha256:
        temporary_path.unlink()
        raise SystemExit(f"Checksum mismatch for {destination.name}: {actual_sha256}")
    temporary_path.replace(destination)
    print(f"Downloaded and verified: {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the official YuNet and SFace ONNX models."
    )
    parser.add_argument(
        "--force", action="store_true", help="Replace model files that already exist."
    )
    args = parser.parse_args()
    for filename, details in MODELS.items():
        download(
            details["url"],
            MODEL_DIR / filename,
            details["sha256"],
            force=args.force,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
