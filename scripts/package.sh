#!/bin/sh
# Build the submission zip next to the project folder:
#   ../volta-newsletter-agent-submission.zip
# The zip contains one top-level folder, volta-newsletter-agent/.
# Private, local and generated files are left out (see excluded below).
# Nothing in the project is deleted or moved.
#
# Usage, from the project root:  sh scripts/package.sh

set -eu

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
TOP=volta-newsletter-agent
OUT="$(dirname "$PROJECT_DIR")/volta-newsletter-agent-submission.zip"
DNF=sources/do-not-feature.md

# excluded PATH: succeeds if PATH (relative to the project root) must not be shipped.
excluded() {
    p=${1#./}
    case "$p" in
        .git|.git/*|research|research/*|.idea|.idea/*|work|work/*) return 0 ;;
        __pycache__|__pycache__/*|*/__pycache__|*/__pycache__/*) return 0 ;;
        .DS_Store|*/.DS_Store|._*|*/._*|__MACOSX|__MACOSX/*|*/__MACOSX/*) return 0 ;;
        .env|.env.*|*/.env|*/.env.*) return 0 ;;
        *credentials*|*token*|*.key|*.zip) return 0 ;;
        .claude/settings.local.json) return 0 ;;
        state/ledger.md|state/ledger.md.bak) return 0 ;;
        state/issues/.gitkeep|state/issues/example.md) return 1 ;;
        state/issues/*) return 0 ;;
        inbox/.gitkeep|drafts/.gitkeep|intake/.gitkeep) return 1 ;;
        inbox/*|drafts/*|intake/*) return 0 ;;
    esac
    return 1
}

# has_names FILE: succeeds if FILE lists anyone. Every entry on the list is a
# line starting with "- ", so any such line counts as a name.
has_names() {
    grep -q '^- ' "$1"
}

refuse() {
    echo "ERROR: $1"
    echo "No zip was built."
    exit 1
}

# A fresh zip every time (zip would otherwise add to an old one). The old zip
# is removed first, so a refused run never leaves an outdated zip behind.
rm -f "$OUT"

if [ -f "$DNF" ] && has_names "$DNF"; then
    refuse "the real do-not-feature list must not be submitted; empty it or use the example ($DNF has names in it)."
fi

find . -type f | sort | while IFS= read -r f; do
    p=${f#./}
    if ! excluded "$p"; then
        printf '%s\n' "$TOP/$p"
    fi
done > "$OUT.list"

# Zip from a temporary folder that links the project in under the top-level name.
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE" "$OUT.list"' EXIT
ln -s "$PROJECT_DIR" "$STAGE/$TOP"
(cd "$STAGE" && zip -X -q "$OUT" -@ < "$OUT.list")

echo "Built $OUT"
echo
echo "Files in the zip:"
unzip -Z1 "$OUT"

# Check the finished zip. unzip -Z1 prints only file names (unzip -l would
# also print a header line that ends in .zip).
bad=$(unzip -Z1 "$OUT" | while IFS= read -r entry; do
    p=${entry#"$TOP"/}
    if excluded "$p"; then
        printf '%s\n' "$entry"
    fi
done)
if [ -n "$bad" ]; then
    rm -f "$OUT"
    echo
    echo "ERROR: the zip contained files that must not be shipped, so it was removed:"
    printf '%s\n' "$bad"
    exit 1
fi
if unzip -p "$OUT" "$TOP/$DNF" 2>/dev/null | grep -q '^- '; then
    rm -f "$OUT"
    refuse "the zipped do-not-feature list has names in it, so the zip was removed."
fi
echo
echo "OK: no excluded files in the zip, and the do-not-feature list in it is empty."
