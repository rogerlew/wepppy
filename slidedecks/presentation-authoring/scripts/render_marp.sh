#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 <deck.md> [output_dir]" >&2
  exit 2
fi

deck="$1"
out_dir="${2:-$(dirname "$deck")}"

if [ ! -f "$deck" ]; then
  echo "Deck not found: $deck" >&2
  exit 1
fi

mkdir -p "$out_dir"

base_name="$(basename "$deck")"
base_stem="${base_name%.md}"

cli=(npx @marp-team/marp-cli@latest)

# Export primary deliverables.
"${cli[@]}" "$deck" -o "$out_dir/$base_stem.html"
"${cli[@]}" "$deck" --pdf -o "$out_dir/$base_stem.pdf"
"${cli[@]}" "$deck" --pptx -o "$out_dir/$base_stem.pptx"
"${cli[@]}" "$deck" --notes -o "$out_dir/$base_stem.notes.txt"

echo "Rendered:"
echo "  $out_dir/$base_stem.html"
echo "  $out_dir/$base_stem.pdf"
echo "  $out_dir/$base_stem.pptx"
echo "  $out_dir/$base_stem.notes.txt"
