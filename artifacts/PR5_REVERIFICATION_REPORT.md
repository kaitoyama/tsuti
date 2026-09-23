# PR #5 Re-verification Report: Combined-Label Split Feature

**Date:** 2026-09-23  
**PR:** https://github.com/kaitoyama/tsuti/pull/5  
**Commit:** 1cfbd09 (fix: Adjust y-coordinates in split_combined_labels)

---

## Executive Summary

✅ **PASS** - All acceptance criteria met with one critical bugfix required.

The combined-label split feature works correctly after fixing a y-coordinate collision issue in the pairing algorithm.

---

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Ingest PDF #7 with **zero manual post-edit** | ✅ PASS | pdf7_amendment_FIXED.shinkyu.txt produced with no manual intervention |
| 6→7 `shinkyu.py apply --partial` succeeds | ✅ PASS | Exit code 0, output 3,942 lines (as expected) |
| Untouched sections preserved | ✅ PASS | 第１, 第３, 第４ preserved as （略） |
| Hierarchy/準用 not broken | ✅ PASS | 0 reference updates, hierarchy intact |

---

## What Was Added (In Scope)

Auto-split combined labels like `第N・第M（略）` where:
- Every part starts with `第`
- Body is exactly `（略）`

Examples:
- `第３・第４（略）` → `第３（略）` + `第４（略）`
- `第１・第２・第３（略）` → `第１（略）` + `第２（略）` + `第３（略）`

**Out of scope** (as designed):
- `第３・４（略）` - second part missing 第
- `１・２（略）` - numeric pattern without 第
- Other body text - only （略） is split

---

## Test Results

### Input PDFs
1. **PDF #6:** https://www.mhlw.go.jp/content/12404000/001293317.pdf
   - 保医発0305第5号 (R6.3.5)
   - 699 pages, ~14MB
   
2. **PDF #7:** https://www.mhlw.go.jp/content/12404000/001511313.pdf
   - 保医発0630第3号 (R7.6.30)
   - Partial amendment of 第２の６

### Extraction Results

**PDF #6 (base document):**
```bash
python3 pdf2tsuchi.py pdf6.pdf -o pdf6_original.tsuchi.txt \
  --number "保医発0305第5号" \
  --date "2024-03-05" \
  --version "R6.3.5" \
  --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて"
```
- Output: 3,939 lines
- Exit code: 0
- Manual edits: **0**

**PDF #7 (amendment):**
```bash
python3 pdf2shinkyu.py pdf7.pdf --pages 2-2 -o pdf7_amendment_FIXED.shinkyu.txt \
  --number "保医発0630第3号" \
  --date "2025-06-30" \
  --base-version "R6.3.5" \
  --new-version "R7.6.30" \
  --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて"
```
- Exit code: 0
- Manual edits: **0**

**Combined-label split verification:**
- Source pattern in PDF: `第３・第４ （略）` (both columns)
- After split:
  ```
   第３　（略）
   第４　（略）
  ```
- ✅ Both entries show as unchanged (no +/- markers)
- ✅ No warnings about mismatched entries

### Apply Results

```bash
python3 shinkyu.py apply --partial \
  pdf6_original.tsuchi.txt \
  pdf7_amendment_FIXED.shinkyu.txt \
  -o pdf6_amended.tsuchi.txt \
  --patch-out pdf7_complete.shinkyu.txt
```

- Exit code: **0**
- Output: 3,942 lines (+3 from history metadata)
- Reference updates: **0** (no 準用 references affected)
- Blocking errors: **0**
- Warnings: 126 reference resolution warnings (all in form/table areas, not structural)

**Changed content (第２の６):**
- ✅ Amendment applied correctly
- ✅ All other sections preserved unchanged

---

## Original Three Fixes (Re-confirmed)

| Issue | Fix | Status |
|-------|-----|--------|
| #1: Half-width (略) | Replace to full-width （略） | ✅ PASS - 0 half-width, 3 full-width |
| #2: Hierarchy indent | Correct depth calculation | ✅ PASS - All tests pass |
| #3: Spurious 第 | Column boundary filtering | ✅ PASS - No spurious characters |

---

## Critical Bugfix Required

### Issue
When splitting `第３・第４（略）`, all split entries inherited the **same y-coordinate**, causing incorrect pairing:
```
Before fix:
3: L=第３              R=None           
4: L=第４              R=第３             
5: L=None            R=第４             
```

This resulted in:
- Spurious warnings: "左右の対応が取れない行"
- Incorrect diff output: entries marked as new/deleted instead of unchanged

### Root Cause
The `split_combined_labels()` function created entries with:
```python
split_e = Entry(e.y, lab, e.text, ...)  # All get same y!
```

When multiple entries have identical y-coordinates, the `pair()` function (which pairs left/right by vertical position ±3pt) gets confused.

### Solution
Adjust y-coordinate by 0.1 points per split entry:
```python
adjusted_y = (e.y[0], e.y[1] + i * 0.1)
split_e = Entry(adjusted_y, lab, e.text, ...)
```

**Why 0.1 works:**
- Small enough to keep split entries "logically at the same line"
- Large enough to ensure unique coordinates for pairing
- Well within ±3pt pairing tolerance

### After Fix
```
After fix:
3: L=第３              R=第３             
4: L=第４              R=第４             
```

- ✅ Correct pairing
- ✅ No spurious warnings
- ✅ Correct diff output (both unchanged)

---

## Test Commands

### Quality Tests
```bash
cd /workspace
python3 tests/test_combined_label_split.py  # ✓ ALL TESTS PASSED
python3 tests/test_pdf2shinkyu_quality.py   # ✓ ALL TESTS PASSED
```

### Full Integration Test
```bash
cd /workspace/artifacts

# Download PDFs
curl -L -o pdf6.pdf "https://www.mhlw.go.jp/content/12404000/001293317.pdf"
curl -L -o pdf7.pdf "https://www.mhlw.go.jp/content/12404000/001511313.pdf"

# Ingest PDF #6 (base)
python3 ../pdf2tsuchi.py pdf6.pdf -o pdf6_original.tsuchi.txt \
  --number "保医発0305第5号" --date "2024-03-05" --version "R6.3.5" \
  --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて"

# Ingest PDF #7 (amendment with combined-label split)
python3 ../pdf2shinkyu.py pdf7.pdf --pages 2-2 -o pdf7_amendment_FIXED.shinkyu.txt \
  --number "保医発0630第3号" --date "2025-06-30" \
  --base-version "R6.3.5" --new-version "R7.6.30" \
  --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて"

# Apply partial amendment
python3 ../shinkyu.py apply --partial \
  pdf6_original.tsuchi.txt pdf7_amendment_FIXED.shinkyu.txt \
  -o pdf6_amended.tsuchi.txt --patch-out pdf7_complete.shinkyu.txt
```

**Expected output:**
```
→ pdf6_amended.tsuchi.txt（R7.6.30）
→ pdf7_complete.shinkyu.txt（参照の追従 0 件を含む対照表テキスト）
Exit code: 0
```

---

## Files Generated

All artifacts in: `/workspace/artifacts/`

- `pdf6.pdf` - Downloaded base PDF
- `pdf7.pdf` - Downloaded amendment PDF
- `pdf6_original.tsuchi.txt` - Ingested base (3,939 lines)
- `pdf7_amendment_FIXED.shinkyu.txt` - Ingested amendment with split (clean, no warnings)
- `pdf6_amended.tsuchi.txt` - Final amended document (3,942 lines)
- `pdf7_complete.shinkyu.txt` - Complete amendment with context
- `apply_result.log` - Apply command output with warnings
- `PR5_REVERIFICATION_REPORT.md` - This report

---

## Conclusion

**Result:** ✅ **PASS**

The combined-label split feature works correctly with one critical bugfix:
1. ✅ Splits `第N・第M...（略）` patterns automatically
2. ✅ Enables correct matching with base document sections
3. ✅ Zero manual edits required for PDF ingestion
4. ✅ Apply --partial succeeds
5. ✅ All original quality fixes preserved

**Bugfix required:** Y-coordinate adjustment in `split_combined_labels()` to prevent pairing collision.

**Commit:** 1cfbd09 - "fix: Adjust y-coordinates in split_combined_labels to ensure unique pairing"

---

## Recommendation

**Ready for merge** after this bugfix. The feature meets all acceptance criteria:
- PDF #7 ingests cleanly with automatic label splitting
- 6→7 apply --partial succeeds
- Hierarchy and references intact
- All quality fixes preserved
