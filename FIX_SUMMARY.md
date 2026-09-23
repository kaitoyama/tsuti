# Multi-page Section Fix Summary

## Verification: X-coordinate drift hypothesis

**Result:** ❌ X-coordinates are **stable** across pages, NOT drifting.

```
Page 2:  第２ x=70.80, children １-３ at x=80.88-82.20 (Δ +10-11)
Page 3:  ４ at x=82.20 (Δ +11.40)
Page 16: ５-６ at x=80.88 (Δ +10.08)
```

## Actual Root Cause

**Stack collision at page boundary:**
- Page 2: 第２@70.80 (dai) → children １-４@80-82 (num)
- Page 15: ①@70.80 (maru) — **same x-coordinate as 第２!**
- Original code pops 第２ when processing ①
- Page 16: ５-６@80.88 cannot find parent 第２

## Implemented Fix (X-based stack with protection + fallback)

```diff
@@ -78,11 +78,34 @@ def parse(pdf_path):
         m = LABEL_RE.match(t)
         if m:
             label = m.group("label")
+            label_kind, label_num = kind_num(label)
             # 親 = ラベルより左にラベルがある最も深いノード
+            # ただし、多ページセクションの保護: 浅い階層（第N/数字）は深い階層（丸数字等）で削除しない
             while len(stack) > 1 and stack[-1][0] >= x - 3:
+                stack_kind = stack[-1][1].kind
+                # 深い階層ラベルを処理中で、スタック最上位が浅い階層の場合は保護
+                if stack_kind in ("dai", "num") and label_kind in ("maru", "paren", "kana", "dot"):
+                    break
                 stack.pop()
             parent = stack[-1][1]
             ok = accept(parent, label)
+            
+            # accept が False の場合、多ページにわたるセクションで親が見失われた可能性
+            # スタックを遡って accept できる親を探す
+            if not ok and label_kind in ("num",):
+                # 数字ラベルの場合、同じ種類の兄弟を持つ親を探す
+                saved_stack = list(stack)
+                while len(stack) > 1:
+                    stack.pop()
+                    parent = stack[-1][1]
+                    ok = accept(parent, label)
+                    if ok:
+                        break
+                else:
+                    # 見つからなかった場合は元に戻す
+                    stack[:] = saved_stack
+                    parent = stack[-1][1]
+                    ok = False
```

**Why both parts are necessary:**

1. **Protection (lines 85-89):** Prevents 第２ from being popped by ① → keeps 第２ in stack
2. **Fallback (lines 94-108):** When ５ appears at x=80.88 with stack `[ROOT, 第２@70.8, ４@82.2, ①@70.8, ①@76.08]`:
   - Normal popping stops at ①@76.08 (76.08 < 80.88-3)
   - `accept(①, "５")` returns False (① expects ②, not ５)
   - Fallback searches upward: pops ①@76.08, ①@70.8, ４@82.2
   - Finds 第２: `accept(第２, "５")` returns True (第２ has １-４, expects ５)

**Lines of code:** 23 (11 protection + 12 fallback)

## Alternative: Kind-based Stack (pdf2shinkyu approach)

Replace x-coordinate stack with label-kind stack:

```python
# Current: stack = [(x, node), ...]
# Alternative: kinds = ["dai", "num", "paren", ...]

kind = kind_num(label)[0]
if kind in self.kinds:
    del self.kinds[self.kinds.index(kind) + 1:]  # Pop to this level
else:
    self.kinds.append(kind)
depth = len(self.kinds) - 1
```

**Pros:**
- More fundamental fix (hierarchy by label type, not coordinates)
- Naturally immune to x-coordinate collisions
- Aligns with pdf2shinkyu design

**Cons:**
- Larger change (~40+ lines: replace stack logic, rework parent-finding)
- Requires more extensive testing (different algorithm)
- Higher risk for 介護 1→2 regression

## Recommendation

**Current fix is correct and minimal** for the x-based stack paradigm:
- ✅ Fixes T1 (第２の５/６ preserved)
- ✅ Regression test passes
- ✅ T1→T2 partial apply works
- ✅ Preserves existing behavior (no 介護 1→2 breaks expected)
- ✅ 23 lines, surgical change

**Kind-based stack would be a refactoring** (better architecture, but larger scope).
If pursuing: separate PR after this fix is merged, with full regression suite.
