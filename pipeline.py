#!/usr/bin/env python3
"""
pipeline.py – CLI entry point for the email-processing pipeline.

Usage
-----
    python pipeline.py path/to/email.eml
    python pipeline.py path/to/email.eml --output result.json
    python pipeline.py path/to/email.eml --pretty
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src.*` imports work.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.controller import EmailController
from src.models.schemas import UserProfile

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process a .eml file through the AI email-classifier pipeline.",
    )
    parser.add_argument(
        "eml_file",
        type=str,
        help="Path to the .eml file to process.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Write the JSON result to this file (default: stdout).",
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--probe-links",
        action="store_true",
        help="Enable HTTP HEAD probes for link trust checking.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the Gemini model name (e.g. gemini-2.0-flash).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Use a mock UserProfile for link analysis matching.",
    )
    args = parser.parse_args()

    # ── Logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    eml_path = Path(args.eml_file)
    if not eml_path.exists():
        print(f"Error: file not found – {eml_path}", file=sys.stderr)
        sys.exit(1)

    # ── User Profile mock
    user_profile = None
    if args.profile:
        user_profile = UserProfile(
            skills=["Python", "React", "SQL", "Git"],
            experience_level="Intern / Junior",
            education="BS Computer Science",
            location="Islamabad, Pakistan",
            interests=["AI", "Web Development"]
        )

    # ── Run pipeline
    controller = EmailController(
        enable_link_probe=args.probe_links,
        model=args.model,
    )
    result = controller.process(eml_path, user_profile=user_profile)

    # ── Output
    indent = 2 if args.pretty else None
    json_str = result.model_dump_json(indent=indent)

    if args.output:
        out = Path(args.output)
        out.write_text(json_str, encoding="utf-8")
        print(f"✓ Result written to {out}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
