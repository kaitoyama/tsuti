# Horizontal Expansion Validation: 特掲診療料 (Tokkatei)

**Status: BLOCKED** ❌

## Executive Summary

Pipeline test for T1 (保医発0305第6号, 特掲診療料) → T2 (Page 3, 保医発0630第3号) is **BLOCKED** due to pdf2tsuchi parser gap: sections ５ and ６ of 第２ exist in source PDF but were not extracted to tsuchi.txt.

This is NOT a same-type issue covered by PR #5 scope (which addresses pdf2shinkyu issues: fullwidth parens, indent, combined labels, spurious 第). This requires pdf2tsuchi investigation beyond "tiny fix" threshold.

## Pipeline Execution

### Step 1: pdf2tsuchi (T1 → tsuchi.txt) ✓ Executed, ⚠️ Quality Issue

**Command:**
```bash
python3 pdf2tsuchi.py artifacts/T1_001293315.pdf \
  -o artifacts/tsuchi.txt \
  --number 6 \
  --date 2024-03-05 \
  --version R06
```

**Exit Code:** 0

**Output:** 6389 lines generated

**Quality Issue:** Sections ５ and ６ under 第２ were NOT extracted.

- **第２ in tsuchi.txt:** Only has children １, ２, ３, ４, ①, ①, ①, ①
- **第２ in T1 PDF (page 16):**
  - ５ 特掲診療料の施設基準等に係る届出を行う保険医療機関…
  - ６ 届出の要件を満たしている場合は届出を受理し、次の受理番号を決定し、提出者に対して受理番号を付して通知する…

**Root Cause:** Section ４ spans ~13 pages (pages 3-15). Parser likely lost track of sibling sections ５ and ６ on page 16.

### Step 2: pdf2shinkyu (T2 page 3 → shinkyu.txt) ✓ PASS

**Command:**
```bash
python3 pdf2shinkyu.py artifacts/T2_001511313.pdf \
  --pages 3-3 \
  -o artifacts/shinkyu.txt \
  --number 3 \
  --date 2025-06-30 \
  --effective 2025-07-01 \
  --base-version R06 \
  --new-version R07
```

**Exit Code:** 0

**Output:** 21 lines, zero manual corrections needed ✓

**shinkyu.txt structure:**
```
 第２　届出に関する手続き
   １～５　（略）
-  ６　届出の要件を満たしている場合は届出を受理し、次の受理番号を決定し、提出者に対して受理番号を付して通知するとともに、審査支払機関に対して受理番号を付して通知するものであること。
+  ６　届出の要件を満たしている場合は届出を受理し、次の受理番号を決定し、地方厚生（支）局において閲覧（ホームページへの掲載等を含む。）に供するとともに、審査支払機関に対して受理番号を付して通知するものであること。
 第３　（略）
 第４　（略）
```

**Evidence:** pdf2shinkyu correctly extracted the change to section ６ with full-width （略）, correct hierarchy, no spurious characters. PR #5 quality fixes working as expected.

### Step 3: shinkyu.py apply --partial ❌ FAIL

**Command:**
```bash
python3 shinkyu.py apply artifacts/tsuchi.txt artifacts/shinkyu.txt \
  --partial \
  -o artifacts/tsuchi_amended.txt
```

**Exit Code:** 1

**Error:**
```
適用できない箇所 3 件:
 - /第２: （略）とされた「５」が原本にない
 - /第２: 削る・改める「６」が原本にない
 - /第２: 番号が連続していない １・２・３・４・６
```

**Cause:** shinkyu.txt expects 第２/５ and 第２/６, but tsuchi.txt only has 第２/１, ２, ３, ４.

## Evidence: Sections ５ and ６ Exist in T1 PDF

**T1 PDF Page 16 (confirmed via pdfplumber):**

```
Line 2:  ５ 特掲診療料の施設基準等に係る届出を行う保険医療機関又は保険薬局が、次のいずれかに該
Line 3:  当する場合にあっては当該届出の受理は行わないものであること。
...
Line 21: ６ 届出の要件を満たしている場合は届出を受理し、次の受理番号を決定し、提出者に対して受
Line 22: 理番号を付して通知するとともに、審査支払機関に対して受理番号を付して通知するものである
Line 23: こと。
```

Section ６ content matches T2 amendment exactly (before the change).

## Scope Assessment vs. PR #5

### PR #5 Covers (pdf2shinkyu issues):
1. Half-width → full-width （略）
2. Hierarchy indent corrections
3. Spurious 「第」 from column cropping
4. Combined labels 第N・第M splitting

### This Issue (NOT in PR #5 scope):
- **Tool:** pdf2tsuchi (not pdf2shinkyu)
- **Pattern:** Long multi-page sections causing sibling section loss
- **Impact:** Structural parsing failure, not character/spacing cleanup
- **Fix Effort:** Requires investigation of pdf2tsuchi state tracking across pages → Beyond "tiny fix"

## Artifacts Generated

All files saved to `/workspace/artifacts/`:
- `T1_001293315.pdf` (17.5 MB, 934 pages)
- `T2_001511313.pdf` (66 KB, 5 pages)
- `tsuchi.txt` (6389 lines, ⚠️ missing 第２/５, ６)
- `shinkyu.txt` (21 lines, ✓ zero manual edits)

No tsuchi_amended.txt generated (step 3 failed).

## Acceptance Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| Near-zero manual ingest | ✓ PASS | pdf2shinkyu: 0 edits |
| Hierarchy / 準用 not broken | ⚠️ N/A | Could not reach apply step |
| Untouched sections preserved | ⚠️ N/A | Could not reach apply step |
| Zero code changes preferred | ✓ | No code changes made |
| Tiny fix OK if same-type as #5 | ❌ FAIL | Issue NOT in #5 scope |

## Recommendation

**BLOCKED:** Do not proceed with 特掲診療料 expansion until pdf2tsuchi correctly extracts all sections.

### Options:

1. **Fix pdf2tsuchi (recommended if expanding to tokkatei):**
   - Investigate state tracking for long sections (13+ pages)
   - Add test case: T1 第２ sections １-６
   - Estimated effort: Requires parser debugging, NOT a tiny fix

2. **Defer tokkatei expansion (if low priority):**
   - Current tsuti validated for 基本診療料 only
   - Mark tokkatei as future work
   - Document known gap in README

3. **Manual workaround (NOT recommended):**
   - Hand-edit tsuchi.txt to add sections ５, ６
   - Fragile, not reproducible
   - Defeats "zero manual ingest" goal

## Commands for Reproduction

```bash
# Step 1: Extract T1
python3 pdf2tsuchi.py artifacts/T1_001293315.pdf \
  -o artifacts/tsuchi.txt \
  --number 6 --date 2024-03-05 --version R06

# Verify missing sections
python3 -c "
import tsuchi
meta, root = tsuchi.load('artifacts/tsuchi.txt')
sec2 = [c for c in root.children if c.label == '第２'][0]
print(f'第２ children: {[c.label for c in sec2.children]}')
# Output: ['１', '２', '３', '４', '①', '①', '①', '①']
# Expected: ['１', '２', '３', '４', '５', '６', ...] 
"

# Step 2: Extract T2 page 3
python3 pdf2shinkyu.py artifacts/T2_001511313.pdf \
  --pages 3-3 -o artifacts/shinkyu.txt \
  --number 3 --date 2025-06-30 --effective 2025-07-01 \
  --base-version R06 --new-version R07

# Step 3: Attempt apply (fails)
python3 shinkyu.py apply artifacts/tsuchi.txt artifacts/shinkyu.txt \
  --partial -o artifacts/tsuchi_amended.txt
# Exit code: 1
# Error: /第２: （略）とされた「５」が原本にない
```

## Optional T3 Test

NOT executed (T1→T2 already blocked).

T3 pair: `001535049.pdf` pages 8-11 vs same T1 → defer until T1 extraction fixed.

---

**Validation Date:** 2026-09-23  
**Commit:** 745f253 (latest main)  
**Verdict:** BLOCKED - pdf2tsuchi gap, NOT #5 scope
