#!/usr/bin/env bash
# 厚生労働省の公開PDFを取得し、検証用データ（data/）を作る。data/ はリポジトリには含めない。
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data
curl -fL -o "data/001227974_R6原本.pdf" https://www.mhlw.go.jp/content/12300000/001227974.pdf
curl -fL -o "data/001676185_R8改正.pdf" https://www.mhlw.go.jp/content/12404000/001676185.pdf

TITLE="介護給付費算定に係る体制等に関する届出等における留意点について"
python3 pdf2tsuchi.py "data/001227974_R6原本.pdf" -o data/R6.tsuchi.txt \
  --number 老発0315第1号 --date 2024-03-15 --version R6.3.15 \
  --title "$TITLE" --issuer 厚生労働省老健局長 --to 各都道府県知事
python3 pdf2shinkyu.py "data/001676185_R8改正.pdf" --pages 2-8 -o data/R8.shinkyu.txt \
  --underlines data/R8_underlines.json \
  --number 老発0313第5号 --date 2026-03-13 --effective 2026-06-01 \
  --base-version R7.3.13 --new-version R8.3.13 --title "$TITLE" \
  --target-ref "（令和６年３月15日老発0315第１号　厚生労働省老健局長通知）"
python3 shinkyu.py render data/R8.shinkyu.txt -o data/R8_新旧対照表.html
echo "完了: data/ を作成しました"
