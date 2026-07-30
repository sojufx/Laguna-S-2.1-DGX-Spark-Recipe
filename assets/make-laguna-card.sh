#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-assets/laguna-spark-benchmark-card.png}"
FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD="/System/Library/Fonts/Supplemental/Arial Bold.ttf"

magick -size 1600x900 xc:'#09070f' \
  -fill '#1b1025' -draw 'circle 1380,110 1700,110' \
  -fill '#3b1d05' -draw 'circle 125,830 500,830' \
  -fill '#111827' -stroke '#3b2f4a' -strokewidth 3 -draw 'roundrectangle 55,50 1545,850 44,44' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 58 -annotate +92+132 'Laguna S 2.1 NVFP4 on 1× DGX Spark' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 29 -annotate +94+184 'vLLM 0.26 · 250K context · FP8 KV · DFlash K=15 · prefix-match-unit 16' \
  \
  -fill '#090a14' -stroke '#4c1d95' -strokewidth 2 -draw 'roundrectangle 92,222 458,338 28,28' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 24 -annotate +122+268 'code-shaped decode' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 58 -annotate +122+320 '44.7' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 30 -annotate +286+318 'tok/s' \
  \
  -fill '#090a14' -stroke '#7c2d12' -strokewidth 2 -draw 'roundrectangle 490,222 856,338 28,28' \
  -stroke none -font "$FONT" -fill '#fed7aa' -pointsize 24 -annotate +520+268 'long-context decode' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 58 -annotate +520+320 '39.5' \
  -stroke none -font "$FONT" -fill '#fed7aa' -pointsize 30 -annotate +684+318 'tok/s' \
  \
  -fill '#171923' -stroke '#334155' -strokewidth 2 -draw 'roundrectangle 888,222 1456,338 28,28' \
  -stroke none -font "$FONT" -fill '#94a3b8' -pointsize 24 -annotate +918+268 'daily-driver shape' \
  -stroke none -font "$BOLD" -fill '#f8fafc' -pointsize 36 -annotate +918+306 '250K stable context' \
  -stroke none -font "$FONT" -fill '#94a3b8' -pointsize 21 -annotate +918+330 'crash-aware single Spark recipe' \
  \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 38 -annotate +98+415 'Practical benchmark snapshot' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 24 -annotate +98+453 'OpenAI-compatible requests · production stability over leaderboard-only tuning' \
  \
  -stroke '#2b2438' -strokewidth 2 -draw 'line 150,730 1450,730' \
  -draw 'line 150,640 1450,640' \
  -draw 'line 150,550 1450,550' \
  -draw 'line 150,460 1450,460' \
  -stroke none -font "$FONT" -fill '#a78bfa' -pointsize 18 -annotate +105+736 '0' \
  -annotate +98+646 '30' \
  -annotate +98+556 '60' \
  -annotate +98+466 '90' \
  \
  -fill '#f97316' -draw 'roundrectangle 255,593 435,730 16,16' \
  -fill '#facc15' -draw 'rectangle 255,593 435,661' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 27 -annotate +251+576 '43.6' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 25 -annotate +316+774 'C1' \
  \
  -fill '#f97316' -draw 'roundrectangle 545,558 725,730 16,16' \
  -fill '#facc15' -draw 'rectangle 545,558 725,644' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 27 -annotate +541+541 '56.3' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 25 -annotate +606+774 'C2' \
  \
  -fill '#f97316' -draw 'roundrectangle 835,493 1015,730 16,16' \
  -fill '#facc15' -draw 'rectangle 835,493 1015,612' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 27 -annotate +831+476 '79.1' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 25 -annotate +896+774 'C3' \
  \
  -stroke '#a78bfa' -strokewidth 7 -fill none -draw 'path \"M 345,593 C 470,570 555,564 635,558 C 740,532 845,505 925,493\"' \
  \
  -fill '#090a14' -stroke '#4c1d95' -strokewidth 2 -draw 'roundrectangle 1110,455 1498,730 24,24' \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 22 -annotate +1140+500 'startup KV capacity' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 42 -annotate +1140+550 '319K tokens' \
  -stroke none -font "$FONT" -fill '#fed7aa' -pointsize 22 -annotate +1140+605 'max-context concurrency' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 38 -annotate +1140+650 '1.28× @ 250K' \
  -stroke none -font "$FONT" -fill '#94a3b8' -pointsize 20 -annotate +1140+697 'thinking off · prefix cache on' \
  \
  -stroke none -font "$FONT" -fill '#c4b5fd' -pointsize 22 -annotate +92+825 'github.com/sojufx/Laguna-S-2.1-DGX-Spark-Recipe' \
  -stroke none -font "$BOLD" -fill '#fff7ed' -pointsize 25 -annotate +1065+825 'Long context. Stable memory. Real endpoint.' \
  "$OUT"

