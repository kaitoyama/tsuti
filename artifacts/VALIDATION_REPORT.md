# tsuti Pipeline Validation Report

## Executive Summary

**Pair #1→#2 (介護 smoke test): PASS ✓**
- Round-trip validation completed successfully
- Hierarchy labels intact
- 準用 references tracked correctly

**Pair #6→#7 (診療報酬 A' main): BLOCKED ✗**
- PDF extraction partially successful with fixes
- Apply failed due to structural incompatibility
- Root cause: Partial amendment vs. complete 新旧対照表 format mismatch

---

## Pair #1→#2: 介護給付費算定 (Smoke Test)

### PDFs
- **#1 原本**: https://www.mhlw.go.jp/content/12300000/001227974.pdf (老発0315第1号 / 2024-03-15)
- **#2 新旧対照**: https://www.mhlw.go.jp/content/12404000/001676185.pdf (老発0313第5号 / 2026-03-13, pages 2-8)

### Commands Run
```bash
bash scripts/fetch_data.sh
python3 tests/roundtrip.py
python3 tests/refs_test.py  
python3 tests/underline_check.py
```

### Results: **PASS ✓**

#### fetch_data.sh
- **Exit code**: 0
- **Output files**: 
  - `data/R6.tsuchi.txt` (原本テキスト)
  - `data/R8.shinkyu.txt` (改正テキスト)
  - `data/R8_新旧対照表.html`
- **Issues detected** (PDF quality, not tool issues):
  - 1 original PDF typo: duplicate ⑳ on p.44
  - 4 amendment PDF issues: label mismatch (43→3), missing （略） markers

#### roundtrip.py
- **Exit code**: 0
- **Key outputs**:
  - ✓ 改変版 == 対照表テキストから復元した版: **一致**
  - ✓ 対照表テキストの再生成: **一致**
  - ✓ 原本を1字改ざんすると適用が止まるか: **止まる**

#### refs_test.py
- **Exit code**: 0
- **All 7 reference tracking tests passed**:
  - ✓ Number renumbering (㉕→㉖)
  - ✓ Range adjustment (②から⑥まで → ②から⑦まで)
  - ✓ Mid-range insertion warnings
  - ✓ Cross-service references (９㉑→９㉒)
  - ✓ Deletion warnings
  - ✓ Upward shift tracking
  - ✓ Invalid reference rejection

#### underline_check.py
- **Exit code**: 0
- **Results**: 52 comparisons
  - **Precision**: 95.0%
  - **Recall**: 82.9%
- Note: Differences due to human vs. automated grouping decisions (e.g., "加算Ⅰ～Ⅱロ" treated as unit)

### Evidence
- Logs: `artifacts/pair1-2_*.log`
- Test outputs: `tests/out/`
- Data: `data/R6.tsuchi.txt`, `data/R8.shinkyu.txt`, etc.

---

## Pair #6→#7: 基本診療料の施設基準 (A' Main)

### PDFs
- **#6 原本**: https://www.mhlw.go.jp/content/12404000/001293317.pdf (保医発0305第5号 / 2024-03-05, ~14MB, 699 pages)
- **#7 新旧対照**: https://www.mhlw.go.jp/content/12404000/001511313.pdf (保医発0630第3号 / 2025-06-30, page 2 = 別添1)

### Commands Run & Status

#### Step 1: pdf2tsuchi (Original PDF → tsuchi.txt)
```bash
python3 pdf2tsuchi.py data/001293317_A_原本.pdf -o data/A_R6.tsuchi.txt \
  --number 保医発0305第5号 --date 2024-03-05 --version R6.3.05 \
  --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて"
```
- **Status**: SUCCESS (after bugfix)
- **Output**: 3939 lines
- **Bugfix required**: 
  - Fixed `pdf2tsuchi.py` to check for range labels ("～") before calling `kind_num()` (lines 30-36, 91-93)
  - Issue: Label "0～10" caused `ValueError` when parsed as integer

#### Step 2: pdf2shinkyu (Amendment PDF → shinkyu.txt)
```bash
python3 pdf2shinkyu.py data/001511313_A_新旧対照.pdf --pages 2-2 \
  -o data/A_R7.shinkyu.txt --number 保医発0630第3号 \
  --date 2025-06-30 --effective 2025-07-01 \
  --base-version R6.3.05 --new-version R7.6.30
```
- **Status**: PARTIAL SUCCESS (after bugfix)
- **Output**: 22 lines (mostly metadata, minimal content)
- **Bugfix required**:
  - Modified `pdf2shinkyu.py` Col.add() to handle documents without 前文 section (lines 36-53)
  - Added check for documents starting directly with body (第[0-9])
- **Issues**:
  - Text artifacts from PDF extraction (e.g., extra "第" character due to column cropping)
  - Only extracted the changed section (第２の６), not full document structure

#### Step 3: apply (Amendment → Original)
```bash
python3 shinkyu.py apply data/A_R6.tsuchi.txt data/A_R7.shinkyu.txt \
  -o data/A_R7_applied.tsuchi.txt --patch-out data/A_R7_完成版.shinkyu.txt
```
- **Status**: **FAILED ✗**
- **Exit code**: 0 (but no output files generated)
- **Bugfix required**:
  - Fixed `shinkyu.py` check_numbering() to skip range labels (line 105)
- **Blocking errors** (5 validation failures):
  1. Position mismatch: Expected 第２ at root but found 前文
  2. Position mismatch: Expected 第３ at root but found 前文  
  3. Incomplete coverage: 180+ items from original not in amendment
  4. Non-consecutive numbering errors
  5. Duplicate label 第２/６

### Root Cause: **BLOCKED ✗**

**The PDF #7 provides a PARTIAL amendment (only showing changed sections), but the tsuti tool expects a COMPLETE 新旧対照表 covering all document sections.**

#### PDF Structure Comparison

| Aspect | Pair #1→#2 (介護) | Pair #6→#7 (診療報酬) |
|--------|------------------|-------------------|
| Amendment format | Complete 新旧対照表 (pages 2-8) | Partial (1 page showing only 第２の６) |
| Content coverage | Full document structure | Single changed section only |
| 前文 section | Present | Absent |
| Header format | Standard two-column | Two-column merged into single text lines |
| Tool compatibility | ✓ Full support | ✗ Incompatible with current tool design |

#### Technical Details

1. **PDF Extraction Issues** (mitigated by fixes):
   - pdfplumber extracts both columns as single text lines
   - Character positions used to split columns (works but imperfect)
   - Cropping at page.width/2 causes minor text artifacts

2. **Structural Incompatibility** (blocking):
   - Tool's `apply` command expects:
     - Complete document structure in shinkyu file
     - All parent nodes listed (even if unchanged)
     - Consistent depth traversal
   - PDF #7 provides:
     - Only changed section (第２の６)
     - No context for surrounding structure
     - Flat representation starting mid-document

3. **Validation Logic**:
   - Tool verifies every item in original appears in amendment (as changed, unchanged, or skipped)
   - Partial amendments violate this assumption
   - No "--partial" mode exists in current tool

### Evidence
- Logs: `artifacts/pair6-7_*.log`
- Extracted files: `data/A_R6.tsuchi.txt` (3939 lines), `data/A_R7.shinkyu.txt` (22 lines)
- No successful apply output (blocked)

---

## Code Changes Summary

### Minimal Bugfixes Applied (3 fixes, ~15 lines changed)

All changes necessary to run the documented pipeline on the test PDFs. No scope expansion. Created branch for PR.

#### 1. `pdf2tsuchi.py` (lines 30-36)
**Issue**: Range labels like "0～10" passed to `kind_num()` before checking for "～"  
**Fix**: Move range check before `kind_num()` call
```python
# Before: kind_num(label) called first, then check for "～"
# After: Check for "～" first, skip if found
```

#### 2. `pdf2tsuchi.py` (lines 91-93)  
**Issue**: Second call site with same range label issue  
**Fix**: Guard `kind_num()` calls with range check

#### 3. `pdf2shinkyu.py` (lines 36-53)
**Issue**: Documents without 前文 section stuck in "head" stage  
**Fix**: Added transition to "body" stage when line starts with "第[0-9]"
```python
# Added: elif re.match(r"^第[０-９0-9]", t):
#     self.stage = "body"  # Direct to body, no 前文
```

#### 4. `shinkyu.py` (line 105)
**Issue**: `check_numbering()` calls `kind_num()` on range labels  
**Fix**: Skip labels containing "～" or "・"

### Not Changed
- Language/text generation (per user constraint)
- Q&A, 事務連絡, HTML adapter logic
- Scope beyond A→A' hierarchical documents
- No expansion to handle partial amendments (would require significant refactoring)

---

## Conclusion

### Pair #1→#2: **PASS ✓**
- All round-trip tests passed
- Hierarchy labels preserved
- 準用 references tracked accurately
- Underline matching 95%/83% precision/recall
- Tool works as documented for complete 新旧対照表 format

### Pair #6→#7: **BLOCKED ✗**
- PDF ingestion successful (with minimal fixes)
- **Cannot complete round-trip validation**
- **Reason**: Tool designed for complete 新旧対照表, PDF #7 is partial amendment
- **Not a tool bug**: Design assumption mismatch

### Recommendation

**Pair #6→#7 validation cannot be completed with current tool architecture.** To support partial amendments would require:
1. Relaxing validation requirements (allow missing sections)
2. Adding merge logic (partial updates to full documents)
3. Context inference (determine insertion points from minimal headers)
4. This represents significant scope expansion beyond "minimal bugfix"

**For A' coverage validation, either:**
- Obtain complete 新旧対照表 PDF (not partial)
- OR consider this format out of scope per original design
- OR accept partial validation as blocked by format incompatibility

### Artifacts Available
```
artifacts/
├── VALIDATION_REPORT.md (this file)
├── pair1-2_fetch_data.log
├── pair1-2_roundtrip.log  
├── pair1-2_refs_test.log
├── pair1-2_underline_check.log
├── pair6-7_pdf2tsuchi_v3.log
├── pair6-7_pdf2shinkyu_v2.log
└── pair6-7_apply_v2.log

data/
├── R6.tsuchi.txt, R8.shinkyu.txt (pair #1→#2, complete)
├── A_R6.tsuchi.txt (pair #6 original, 3939 lines)
├── A_R7.shinkyu.txt (pair #7 amendment, 22 lines, partial)
└── (no successful apply output for pair #6→#7)
```
