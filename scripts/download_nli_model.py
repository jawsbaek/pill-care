"""One-time script: download DeBERTa-v3-xsmall zero-shot NLI model.

Usage:
    uv run python scripts/download_nli_model.py

The model (~80MB) is saved under `models/nli/` and loaded by
`pillcare.nli_gate.check_entailment` for the 6-layer guardrail's NLI
entailment gate.
"""
from pathlib import Path

from huggingface_hub import snapshot_download

MODEL_ID = "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33"
DEST = Path(__file__).resolve().parents[1] / "models" / "nli"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=str(DEST),
    )
    print(f"NLI model saved to {DEST}")


if __name__ == "__main__":
    main()
