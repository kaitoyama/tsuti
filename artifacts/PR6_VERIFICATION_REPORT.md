# PR #6 Verification Report: 特掲 T1→T2 Multi-page Section Tracking

**Date:** 2026-09-23  
**PR:** https://github.com/kaitoyama/tsuti/pull/6  
**Commit:** e9f3c06 (PR #6 head)  
**Verdict:** ✅ **PASS**

---

## Executive Summary

All acceptance criteria **PASSED**:

1. ✅ T1 ingest retains **第２の５** and **第２の６** (no drop across long multi-page section ４)
2. ✅ T1→T2 `pdf2shinkyu --pages 3-3` + `apply --partial` **succeeds** (exit code 0)
3. ✅ Amendment correctly applied with **near-zero manual edits**
4. ✅ Regression tests pass (no breakage to existing functionality)

---

## Test Details

### Input Documents

| Document | URL | Purpose |
|----------|-----|---------|
| T1 (base) | https://www.mhlw.go.jp/content/12404000/001293315.pdf | 特掲診療料 R6.3.5 原本 |
| T2 (amendment) | https://www.mhlw.go.jp/content/12404000/001511313.pdf | 保医発0630第3号 一部改正 (page 3 only) |

### T1 Metadata
```
number:  保医発0305第6号
date:    2024-03-05
version: R6.3.5
title:   特掲診療料の施設基準等及びその届出に関する手続きの取扱いについて
```

### T2 Metadata
```
amendment_number: 保医発0630第3号
amendment_date:   2025-06-30
effective:        2025-07-01
base_version:     R6.3.5
new_version:      R7.6.30
pages:            3-3 (別添２: 特掲診療料 新旧対照表)
```

---

## Acceptance Criterion 1: T1 Ingest Preserves 第２の５ and 第２の６

### Test Command
```bash
python3 pdf2tsuchi.py T1.pdf \
  -o T1_tsuchi.txt \
  --number '保医発0305第6号' \
  --date '2024-03-05' \
  --version 'R6.3.5' \
  --title '特掲診療料の施設基準等及びその届出に関する手続きの取扱いについて'
```

### Result: ✅ PASS

Verification output:
```
✓ Found 第２: 届出に関する手続き...
Found numbered children: ['１', '２', '３', '４', '５', '６', '７', '８', '９']
✓ Found ５ under 第２
✓ Found ６ under 第２
✓ Sections １-９ in correct order

✓ T1 INGEST VERIFICATION PASSED: 第２の５ and 第２の６ are present
```

**Evidence:** Before PR #6, section ４ spans many pages, causing ５ and ６ (appearing on page 16) to be dropped due to stack collision at page boundaries. The fix in PR #6 adds protection for shallow hierarchy levels (第N, 数字) when processing deep hierarchy labels (丸数字, etc.), plus a fallback search to find the correct parent when the stack is disrupted.

### Additional Architecture-Specific Acceptance Check

**Requirement:** Protection mechanism must not cause erroneous ① to be added under 第２ as a "first occurrence" due to same x-coordinate collision.

**Verification:**
```
=== ARCHITECTURE-SPECIFIED ACCEPTANCE CHECK ===

Verification: 第２ direct children must be only 数字 (１〜９), no 丸数字 (①)

Total direct children under 第２: 9

Direct children grouped by kind:
  num: ['１', '２', '３', '４', '５', '６', '７', '８', '９']

数字 (num) children: ['１', '２', '３', '４', '５', '６', '７', '８', '９']
丸数字 (maru) children: (none)

============================================================
VALIDATION RESULTS:
============================================================
✓ PASS: 第２直下の数字は１〜９が揃っている
✓ PASS: 第２直下に丸数字（①など）は存在しない
✓ PASS: 第２の５と第２の６が存在する（多ページセクション保存成功）
✓ PASS: 第２直下に数字以外の種類は存在しない

保護メカニズムは正常動作:
- 第２は保護されている
- 同x座標の①は第２直下に追加されていない
- 第２の直下は正しく１〜９のみ
```

**Result: ✅ PASS**

- ✅ 第２直下の子は正しく数字（１〜９）のみ
- ✅ 丸数字（①など）は第２直下に存在しない
- ✅ 保護メカニズムが正常動作（同x座標の①が誤って第２直下に追加されていない）

---

## Acceptance Criterion 2: T1→T2 Partial Amendment Succeeds

### Test Commands
```bash
# Step 1: Extract amendment from T2 PDF page 3
python3 pdf2shinkyu.py T2.pdf \
  -o T2_shinkyu.txt \
  --pages 3-3 \
  --number '保医発0630第3号' \
  --date '2025-06-30' \
  --effective '2025-07-01' \
  --base-version 'R6.3.5' \
  --new-version 'R7.6.30' \
  --title '特掲診療料の施設基準等及びその届出に関する手続きの取扱いについて'

# Step 2: Apply amendment to T1 base
python3 shinkyu.py apply --partial \
  T1_tsuchi.txt \
  T2_shinkyu.txt \
  -o T1_T2_applied.tsuchi.txt \
  --patch-out T2_complete.shinkyu.txt
```

### Result: ✅ PASS

**Exit code:** 0 (success)

**Amendment extracted:**
```yaml
---
target: 特掲診療料の施設基準等及びその届出に関する手続きの取扱いについて
amendment:
  kind: 一部改正
  number: 保医発0630第3号
  date: '2025-06-30'
  effective: '2025-07-01'
base_version: R6.3.5
new_version: R7.6.30
---
 第２　届出に関する手続き
   １～５　（略）
-  ６　届出の要件を満たしている場合は届出を受理し、次の受理番号を決定し、提出者に対して受理番号を付して通知するとともに、審査支払機関に対して受理番号を付して通知するものであること。
+  ６　届出の要件を満たしている場合は届出を受理し、次の受理番号を決定し、地方厚生（支）局において閲覧（ホームページへの掲載等を含む。）に供するとともに、審査支払機関に対して受理番号を付して通知するものであること。
 第３　（略）
 第４　（略）
```

**Apply output:**
```
→ T1_T2_applied.tsuchi.txt（R7.6.30）
→ T2_complete.shinkyu.txt（参照の追従 0 件を含む対照表テキスト）
```

---

## Acceptance Criterion 3: Near-Zero Manual Edits, Hierarchy Preserved

### Verification
```python
# Automated verification of applied result
meta, root = load('T1_T2_applied.tsuchi.txt')

# Check version update
assert meta['version'] == 'R7.6.30'  # ✓

# Check 第２ structure preserved
dai2 = find_section(root, '第２')
num_children = [c.label for c in dai2.children if c.kind == 'num']
assert num_children[:9] == ['１', '２', '３', '４', '５', '６', '７', '８', '９']  # ✓

# Check amendment applied to 第２の６
roku = find_section(dai2, '６')
assert '地方厚生（支）局において閲覧' in roku.text  # ✓ New text present
assert '提出者に対して受理番号を付して通知するとともに' not in roku.text  # ✓ Old text removed
```

### Result: ✅ PASS

**Manual edits required:** 0

**Evidence:**
```
=== ✓ ALL VERIFICATIONS PASSED ===
- 第２の５ present
- 第２の６ present
- Amendment correctly applied to 第２の６
- Section order preserved
```

The amended text in 第２の６ correctly shows:
- Old: "提出者に対して受理番号を付して通知するとともに、審査支払機関に対して受理番号を付して通知する"
- New: "地方厚生（支）局において閲覧（ホームページへの掲載等を含む。）に供するとともに、審査支払機関に対して受理番号を付して通知する"

---

## Acceptance Criterion 4: Regression Tests

### Tests Run

| Test | Result | Evidence |
|------|--------|----------|
| Partial apply core logic | ✅ PASS | `test_partial_apply.py` exit 0 |
| Combined label split | ✅ PASS | `test_combined_label_split.py` exit 0 |
| Multi-page section fix | ✅ PASS | Manual verification with T1 |

### test_partial_apply.py Output
```
=== テスト1: --partial なしでは失敗する ===
✓ 期待通り失敗した

=== テスト2: --partial ありで成功する ===
✓ 成功した

=== テスト3: 結果の検証 ===
✓ 第１が残っている
✓ 第２の１の①が改正されている
✓ 第２の１の③が新設されている
✓ 第２の２の①が改正されている
✓ 第２の３が残っている
✓ 第３が残っている
✓ バージョンが更新されている

=== すべてのテストに合格 ===
```

### test_combined_label_split.py Output
```
Test: Split 第N・第M（略）pattern
  ✓ 第３・第４（略）→ 第３（略）, 第４（略）

Test: Split 第N・第M・第K（略）pattern
  ✓ 第１・第２・第３（略）→ 3 separate entries

Test: NO split when text is not （略）
  ✓ NOT split (text not （略）)

...

============================================================
✓ ALL TESTS PASSED
```

**Conclusion:** No regressions detected in existing functionality.

---

## Technical Analysis: PR #6 Fix

### Problem
Multi-page sections were dropped when:
1. Parent section (第２) at page 2, x-coordinate 70.80
2. Deep child (①) at page 15, **same x-coordinate** 70.80
3. Original code pops parent when processing ①
4. Later children (５, ６) at page 16 cannot find parent

### Solution (23 lines)
1. **Protection (11 lines):** Prevent deep hierarchy labels (丸数字, かな) from popping shallow hierarchy (第N, 数字)
2. **Fallback (12 lines):** When label cannot be accepted by stack top, search upward to find correct parent

```python
# Protection: don't pop shallow hierarchy for deep labels
if stack_kind in ("dai", "num") and label_kind in ("maru", "paren", "kana", "dot"):
    break

# Fallback: search upward for accepting parent
if not ok and label_kind in ("num",):
    while len(stack) > 1:
        stack.pop()
        parent = stack[-1][1]
        ok = accept(parent, label)
        if ok:
            break
```

---

## Artifacts

All test artifacts saved to `/workspace/artifacts/`:

- `T1.pdf` - Base document (特掲診療料 R6.3.5)
- `T2.pdf` - Amendment document (保医発0630第3号)
- `T1_tsuchi.txt` - T1 ingestion output
- `T1_ingest.log` - T1 ingestion log
- `T2_shinkyu.txt` - T2 amendment extraction
- `T2_pdf2shinkyu.log` - T2 extraction log
- `T1_T2_applied.tsuchi.txt` - Final applied version (R7.6.30)
- `T2_complete.shinkyu.txt` - Complete amendment with reference tracking
- `apply.log` - Apply command log

---

## Final Verdict

### ✅ **PASS**

PR #6 successfully fixes the multi-page section tracking bug:

1. ✅ **第２の５ and 第２の６ preserved** across 14-page gap in section ４
2. ✅ **T1→T2 partial amendment succeeds** with exit code 0
3. ✅ **Zero manual edits** required - amendment correctly applied
4. ✅ **No regressions** - all existing tests pass
5. ✅ **Minimal code change** - 23 lines, surgical fix to x-based stack logic

**Recommendation:** PR #6 is ready to merge.

---

## Notes

- Reference tracking warnings in apply.log are expected (cross-references to sections not included in partial amendment)
- Some references like "１①" or "３①" cannot be resolved because they refer to sections outside the scope of the partial amendment (only 第２の６ was changed)
- These warnings do not affect the correctness of the amendment application

---

**Report generated:** 2026-09-23  
**Environment:** PR #6 head (e9f3c06)  
**Branch:** pr-6-test
