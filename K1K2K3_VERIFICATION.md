# K1-K3 基発 Verification Results

This document shows how to verify the pdf2kihatsu implementation against the three test PDFs.

## Running the Tests

```bash
# Fetch the test PDFs (if not already present)
bash scripts/fetch_data.sh

# Run the automated test suite
python3 tests/test_kihatsu.py
```

## Manual Verification

### K1: 基発0731第7号 / 2026-07-31

```bash
python3 pdf2kihatsu.py data/kihatsu_samples/K1.pdf -o K1_output.txt
```

**Expected metadata:**
- 種別: 基発
- 番号: 基発0731第7号 (normalized from "基発 0731 第 7 号")
- 日付: 令和８年７月31日
- 発出元: 厚生労働省労働基準局長
- 件名: 「定期健康診断等における診断項目の取扱い等について」（平成 29 年８月４日付け基発 0804 第４号）の一部訂正について

**Expected body:** Non-empty paragraphs including "別紙" and correction details

### K2: 基発0919第1号 / 2025-09-19

```bash
python3 pdf2kihatsu.py data/kihatsu_samples/K2.pdf -o K2_output.txt
```

**Expected metadata:**
- 種別: 基発
- 番号: 基発0919第1号 (normalized from "基 発 0919第 １ 号")
- 日付: 令和７年９月19日
- 発出元: 厚生労働省労働基準局長
- 件名: 労働安全衛生規則の一部を改正する省令等の施行について

**Expected body:** Non-empty paragraphs including "記" section and regulation details

### K3: 基発0526第1号 / 2026-05-26

```bash
python3 pdf2kihatsu.py data/kihatsu_samples/K3.pdf -o K3_output.txt
```

**Expected metadata:**
- 種別: 基発
- 番号: 基発0526第1号 (normalized from "基 発 0526第 １ 号")
- 日付: 令和８年５月26日
- 発出元: 厚生労働省労働基準局長
- 件名: 労働安全衛生法及び作業環境測定法の一部を改正する法律の一部の施行に伴う関係政令の整理等に関する政令等の施行について（個人事業者等の安全衛生対策の推進に係る規定関係）

**Expected body:** Non-empty paragraphs (29 pages of content), 記 section, detailed regulation text

## Automated Test Results

All K1-K3 tests pass:
- ✓ Metadata extraction (種別・番号・日付・発出元・件名)
- ✓ Spaced number normalization ("基　発　0　7　3　1　第　7　号" → "基発0731第7号")
- ✓ Body text extraction (non-empty, substantial content)
- ✓ Full-width number handling ("基 発 0919第 １ 号" → "基発0919第1号")
