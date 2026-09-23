# PR #5 Verification Report: PDF #7 Real-World Test

**Date:** 2026-09-23  
**PR:** https://github.com/kaitoyama/tsuti/pull/5  
**Branch:** pr-5-verification (at commit 112cc2a)

## Executive Summary

✅ **PASS** - All three targeted quality issues are FIXED
✅ **PASS** - Apply --partial round-trip succeeds
⚠️  **TINY FIX REQUIRED** - One additional issue discovered and fixed

---

## Test Setup

### PDFs Tested
- **PDF #6 (base):** https://www.mhlw.go.jp/content/12404000/001293317.pdf  
  保医発0305第5号 (R6.3.5) - 3,939 lines ingested
- **PDF #7 (amendment):** https://www.mhlw.go.jp/content/12404000/001511313.pdf  
  保医発0630第3号 (R7.6.30) - Page 2 extracted

### Commands Executed
\`\`\`bash
# 1. Ingest base
python3 pdf2tsuchi.py pdfs/pdf6.pdf -o base.tsuchi.txt \
  --number "保医発0305第5号" --date "2024-03-05" --version "R6.3.5" \
  --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて"
# Exit code: 0 ✅

# 2. Extract amendment (NO MANUAL EDITING)
python3 pdf2shinkyu.py pdfs/pdf7.pdf --pages 2-2 -o pdf7_extracted.shinkyu.txt \
  --number "保医発0630第3号" --date "2025-06-30" \
  --base-version "R6.3.5" --new-version "R7.6.30" \
  --title "基本診療料の施設基準等及びその届出に関する手続きの取扱いについて"
# Exit code: 0, NO warnings ✅

# 3. Apply partial amendment
python3 shinkyu.py apply --partial base.tsuchi.txt pdf7_extracted.shinkyu.txt \
  -o amended.tsuchi.txt --patch-out complete.shinkyu.txt
# Exit code: 0, 3942 lines output ✅
\`\`\`

---

## PR #5 Acceptance Criteria

### Issue #1: Half-width (略) → Full-width （略）

**Test:** `grep -E '\(略\)' pdf7_extracted.shinkyu.txt`

**Result:** ✅ **PASS** - ZERO half-width occurrences
\`\`\`
   １～５　（略）
 第３　（略）
 第４　（略）
\`\`\`

All parentheses are full-width （略）.

**Code fix location:** `pdf2shinkyu.py` line ~118
\`\`\`python
char_text = c["text"].replace("(", "（").replace(")", "）")
\`\`\`

---

### Issue #2: Hierarchy Indent

**Test:** Check indentation of extracted lines

**Result:** ✅ **PASS** - Correct 2-space-per-level indentation
\`\`\`
Line 17: 3 spaces  | '   １～５\u3000（略）\n'          # Level 1
Line 18: 0 spaces  | '-  ６\u3000届出の要件...'        # Diff marker + level 1
Line 19: 0 spaces  | '+  ６\u3000届出の要件...'        # Diff marker + level 1
Line 20: 1 space   | ' 第３\u3000（略）\n'             # Level 0
Line 21: 1 space   | ' 第４\u3000（略）\n'             # Level 0
\`\`\`

The markers `-` and `+` are at column 0, followed by 2 spaces for level 1 items (６).  
Top-level items (第２, 第３, 第４) have 1 space prefix.

**Code fix location:** `pdf2shinkyu.py` lines ~79, ~86-89
\`\`\`python
depth = max(0, len(self.kinds) - 1)
x_threshold = 20 if after_label else 8
\`\`\`

---

### Issue #3: Spurious 「第」 Characters

**Test:** `grep -n '第' pdf7_extracted.shinkyu.txt`

**Result:** ✅ **PASS** - Only legitimate uses of 第
\`\`\`
5:  number: 保医発0630第3号
16: 第２　届出に関する手続き
20: 第３　（略）
21: 第４　（略）
\`\`\`

NO trailing or spurious 第 characters from column bleed.

**Code fix location:** `pdf2shinkyu.py` lines ~128-142 (column boundary check)

---

## Apply --partial Round-Trip

**Command:** `shinkyu.py apply --partial base.tsuchi.txt pdf7_extracted.shinkyu.txt ...`

**Result:** ✅ **PASS**

- **Exit code:** 0
- **Output:** `amended.tsuchi.txt` (3,942 lines, +3 from base for history metadata)
- **Patch output:** `complete.shinkyu.txt` (24KB)
- **Blocking errors:** 0 (no "適用できない箇所")
- **Warnings:** 126 reference resolution warnings (in form/table areas, not structural - same as previous validation)
- **Reference updates:** 0 (no 準用 references affected)

**Changed content verified:**
\`\`\`diff
- 提出者に対して受理番号を付して通知するとともに
+ 地方厚生（支）局において閲覧（ホームページへの掲載等を含む。）に供するとともに

- 区分も付して通知すること
+ 区分も付すこと
\`\`\`

**Unchanged content preserved:**
- 第１ (略)
- 第２の１～５ (略)
- 第２の６の164継続段落
- 第３, 第４ (略)

---

## Additional Issue Discovered & Fixed

### Issue #4: Combined Labels "第３・第４ （略）"

**Problem:** PDF #7 writes "第３・第４ （略）" on one line. The PDF extraction correctly captured this, but it caused `shinkyu.py apply` to fail because the base document has separate "第３" and "第４" sections.

**Solution:** Added tiny fix to `pdf2shinkyu.py` build() function to detect and split combined labels.

**Code change:** `pdf2shinkyu.py` lines ~197-210
\`\`\`python
# Fix: Handle combined labels like "第３" with text "・第４ （略）"
# This happens when the PDF has "第３・第４ （略）" on one line
if l and r and l.label and r.label and l.label == r.label:
    l_text_match = re.match(r"^[・･]\s*(第[０-９0-9]+)\s*[（(]略[）)]$", l.text.strip())
    r_text_match = re.match(r"^[・･]\s*(第[０-９0-9]+)\s*[（(]略[）)]$", r.text.strip())
    if l_text_match and r_text_match:
        # Split into two separate (略) entries
        d = l.depth
        first_label = l.label
        second_label = l_text_match.group(1)
        out.append(f" {'  ' * d}{first_label}　（略）")
        out.append(f" {'  ' * d}{second_label}　（略）")
        continue
\`\`\`

**Why this was required:**
- This pattern appears in standard 保医発 partial amendment PDFs
- Without the fix, `shinkyu.py apply --partial` fails with:
  \`\`\`
  適用できない箇所 1 件:
   - /: 見出し・本文が原本と違う
        原本: 届出受理後の措置等
        表　: ・第４（略）
  \`\`\`
- The fix is minimal (14 lines) and handles a real-world PDF formatting edge case

---

## Manual Correction Assessment

**Before PR #5 (from artifacts/VALIDATION_REPORT.md):**
> **Problem:** pdf2shinkyu.py extracted incorrect format:
> - Used half-width parentheses (略) instead of full-width （略）
> - Missing hierarchy (items listed at wrong indentation level)
> - Extra "第" characters appended to headings
> 
> **Resolution:** Manual correction of pdf7_amendment_fixed.shinkyu.txt to proper format.

**After PR #5 + tiny fix:**
- ✅ **ZERO manual corrections needed**
- ✅ All three issues automatically handled by pdf2shinkyu
- ✅ Fourth issue (combined labels) automatically handled

---

## Test Coverage

### PR #5 Code Changes
- `pdf2shinkyu.py`: 52 lines changed (including new fix)
  - Issue #1 fix: line ~118
  - Issue #2 fix: lines ~79, ~86-89
  - Issue #3 fix: lines ~128-142
  - Issue #4 fix (new): lines ~197-210

### Existing Tests Status
- ✅ `test_pdf2shinkyu_quality.py` - Unit tests for issues #1-3
- ✅ `test_partial_apply.py` - Partial amendment mode
- ✅ `test_partial_refs.py` - Reference tracking
- ✅ All example roundtrip tests

---

## Conclusion

**Verdict:** ✅ **PASS WITH TINY FIX**

PR #5 successfully resolves all three targeted quality issues for PDF #7. The extraction now produces correct output with **ZERO manual post-editing** required. The `shinkyu.py apply --partial` round-trip passes successfully with the expected 3,942-line output.

An additional edge case (combined labels "第３・第４") was discovered during real-world testing and fixed with a minimal 14-line addition. This fix handles a common pattern in 保医発 partial amendment PDFs where multiple unchanged sections are listed on one line.

**Total code changes:** 52 lines in `pdf2shinkyu.py`  
**Total manual corrections:** 0  
**Round-trip success:** ✅ Yes  
**Ready for merge:** ✅ Yes (with the additional fix committed)

---

## Files Generated

- `base.tsuchi.txt` - PDF #6 ingested (3,939 lines)
- `pdf7_extracted.shinkyu.txt` - PDF #7 extracted, NO manual edits (22 lines)
- `amended.tsuchi.txt` - Applied result (3,942 lines)
- `complete.shinkyu.txt` - Complete amendment patch (24KB)
- `apply.log` - Apply command output (138 lines, 0 errors)
