#!/usr/bin/env python
"""nell.py — a never-ending learner demo on LETO + lovelaice.

Given a TOPIC, runs a lovelaice ReAct agent in a loop to build a small
"wiki" of LETO markdown notes. The agent is stateless across cycles — its
only memory is the LETO vault. This demonstrates that LETO does the work,
not the agent's cleverness or its own memory.

Run (in an env with `leto`, `lovelaice`, `lingo-ai`, `ddgs` installed):

    export OPENROUTER_API_KEY=sk-...
    python nell.py "History of the Enigma machine" --model openai/gpt-4o --cycles 4

The chat model is any OpenRouter slug (--model or NELL_MODEL). Embeddings
are computed locally (no embeddings provider needed). Web search uses
DuckDuckGo (keyless).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from lingo import LLM

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def make_llm(model: str, on_token=None) -> LLM:
    """A lingo.LLM pointed at OpenRouter. A fresh instance is built per use
    so no client is reused across event loops."""
    return LLM(
        model=model,
        api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY"),
        base_url=OPENROUTER_BASE_URL,
        on_token=on_token,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Never-ending learner demo on LETO + lovelaice.")
    p.add_argument("topic", help="the topic to learn about")
    p.add_argument("--cycles", type=int, default=8, help="number of learning cycles (default 8)")
    p.add_argument("--vault", default=None, help="vault dir (default: ./.nell-<timestamp>)")
    p.add_argument("--model", default=None, help="OpenRouter chat model slug (or set NELL_MODEL)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    model = args.model or os.getenv("NELL_MODEL")
    if not model:
        sys.exit("error: set --model <openrouter-slug> or NELL_MODEL")
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY")):
        sys.exit("error: set OPENROUTER_API_KEY")
    vault = Path(args.vault or f".nell-{datetime.now():%Y%m%d-%H%M%S}")
    print(f"topic: {args.topic!r} · model: {model} · cycles: {args.cycles} · vault: {vault}")


if __name__ == "__main__":
    main()
