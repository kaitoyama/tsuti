#!/usr/bin/env bash
# 厚生労働省の公開PDFを取得し、検証用データ（data/）を作る。data/ はリポジトリには含めない。
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data

# ─────────────────────────────────────────────────────────
# 介護保険（Priority A: 既存の検証対象）
# ─────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────
# 診療報酬（Priority A': 階層つき通知本体の拡張検証用）
# ─────────────────────────────────────────────────────────
# 診療報酬改定の留意事項通知は介護保険と同様の階層構造を持つため、
# 既存のコアで取り込み可能です。以下は実際のPDF URLを指定する例です。
# 
# 例：令和6年度診療報酬改定「基本診療料の施設基準等及びその届出に関する手続きの取扱いについて」
#     https://www.mhlw.go.jp/content/12400000/00XXXXXX.pdf（実際のURLに置き換える）
#
# 取得・変換する場合は下記のコメントを外して実行してください：
#
# curl -fL -o "data/shinryou_R6_honbun.pdf" https://www.mhlw.go.jp/content/12400000/00XXXXXX.pdf
# python3 pdf2tsuchi.py "data/shinryou_R6_honbun.pdf" -o data/shinryou_R6.tsuchi.txt \
#   --number 保医発0304第1号 --date 2024-03-04 --version R6.3.4 \
#   --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて" \
#   --issuer 厚生労働省保険局医療課長 --to 地方厚生（支）局医療課長
#
# 注：診療報酬通知は「第1」「1」「⑴」「①」「ア」「・」の階層を使用し、
#     介護保険と同じ番号システムでカバーされます。

echo "完了: data/ を作成しました"
