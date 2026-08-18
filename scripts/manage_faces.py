#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classroom_ai.vision import FaceEmbeddingStore, OpenCVFaceRecognition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage the local consented face-recognition database."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    enroll = commands.add_parser("enroll", help="Enroll exactly one face from an image.")
    enroll.add_argument("--image", type=Path, required=True)
    enroll.add_argument("--subject-id", required=True)
    enroll.add_argument("--display-name", required=True)
    enroll.add_argument("--consent-reference", required=True)

    commands.add_parser("list", help="List enrolled subjects without embeddings.")

    delete = commands.add_parser("delete", help="Delete a subject and all embeddings.")
    delete.add_argument("--subject-id", required=True)
    delete.add_argument(
        "--confirm",
        required=True,
        help="Repeat the subject ID to confirm permanent deletion.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = FaceEmbeddingStore()
    if args.command == "list":
        print(json.dumps(store.list_subjects(), indent=2))
        return 0
    if args.command == "delete":
        if args.confirm != args.subject_id:
            raise SystemExit("--confirm must exactly match --subject-id")
        deleted = store.delete_subject(args.subject_id)
        print("Deleted." if deleted else "Subject was not found.")
        return 0

    if not args.image.is_file():
        raise SystemExit(f"Enrollment image not found: {args.image}")
    recognition = OpenCVFaceRecognition(store=store)
    embedding_id = recognition.enroll(
        args.image.read_bytes(),
        subject_id=args.subject_id,
        display_name=args.display_name,
        consent_reference=args.consent_reference,
    )
    print(f"Enrolled embedding {embedding_id} for {args.subject_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
