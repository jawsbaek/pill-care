#!/usr/bin/env bash
# Build 5-page Korean proposal PDF (and HTML fallback) from markdown.
#
# Prerequisites (macOS):
#   brew install pandoc basictex
#   sudo tlmgr update --self
#   sudo tlmgr install xecjk koreanfonts collection-xetex
#   # Pretendard (Korean font) — install as system font:
#   brew tap homebrew/cask-fonts
#   brew install --cask font-pretendard
#
# Usage:
#   bash scripts/build_proposal_pdf.sh
#
# Output:
#   docs/proposal/2026-demo-submission/proposal-5p.pdf   (if xelatex available)
#   docs/proposal/2026-demo-submission/proposal-5p.html  (always, for remote review)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SUB="${ROOT}/docs/proposal/2026-demo-submission"
SRC="${SUB}/proposal-5p-draft.md"
OUT_PDF="${SUB}/proposal-5p.pdf"
OUT_HTML="${SUB}/proposal-5p.html"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "ERROR: pandoc not found. Install: brew install pandoc" >&2
  exit 1
fi

if [ ! -f "${SRC}" ]; then
  echo "ERROR: source not found: ${SRC}" >&2
  exit 1
fi

# --- PDF build (xelatex required for Korean) ----------------------------------
if command -v xelatex >/dev/null 2>&1; then
  echo "Building PDF via xelatex..."
  pandoc "${SRC}" \
    -o "${OUT_PDF}" \
    --pdf-engine=xelatex \
    -V mainfont="Pretendard" \
    -V CJKmainfont="Pretendard" \
    -V geometry:margin=1.5cm \
    -V fontsize=9pt \
    -V linkcolor=blue \
    --toc=false \
    --number-sections=false || {
      echo "PDF build failed with Pretendard — falling back to NanumGothic..." >&2
      pandoc "${SRC}" \
        -o "${OUT_PDF}" \
        --pdf-engine=xelatex \
        -V mainfont="NanumGothic" \
        -V CJKmainfont="NanumGothic" \
        -V geometry:margin=1.5cm \
        -V fontsize=9pt
    }
  echo "PDF: ${OUT_PDF}"
  if command -v pdfinfo >/dev/null 2>&1; then
    PAGES=$(pdfinfo "${OUT_PDF}" | awk '/^Pages:/ {print $2}')
    echo "Pages: ${PAGES}"
    if [ "${PAGES}" -gt 5 ]; then
      echo "WARNING: PDF exceeds 5 pages (${PAGES} pages). See docs/proposal/2026-demo-submission/typesetting-notes.md for tuning steps." >&2
    fi
  fi
else
  echo "xelatex not found; skipping PDF. Install with: brew install basictex" >&2
  echo "HTML fallback will still be produced below."
fi

# --- HTML fallback (always works, no LaTeX needed) ----------------------------
# Use a sidecar header file rather than process substitution so this script is
# portable across shells (bash/zsh/sh) and git-hook sandboxes.
HEADER_TMP="$(mktemp -t pillcare-header.XXXXXX.html)"
trap 'rm -f "${HEADER_TMP}"' EXIT
cat > "${HEADER_TMP}" <<'CSS'
<style>
body { font-family: Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; line-height: 1.55; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.8em; text-align: left; vertical-align: top; }
th { background: #f5f5f5; }
pre { background: #f8f8f8; padding: 1em; overflow-x: auto; font-size: 0.85em; }
code { font-family: 'Menlo', 'SF Mono', monospace; }
h1, h2, h3 { margin-top: 1.5em; }
blockquote { border-left: 3px solid #ccc; padding-left: 1em; color: #555; }
</style>
CSS

echo "Building HTML..."
pandoc "${SRC}" \
  -o "${OUT_HTML}" \
  --standalone \
  --metadata title="필케어(PillCare) 제안서 데모 제출본" \
  --toc --toc-depth=2 \
  -c "https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" \
  -H "${HEADER_TMP}"
echo "HTML: ${OUT_HTML}"
