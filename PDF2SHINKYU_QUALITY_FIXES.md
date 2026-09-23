# pdf2shinkyu Quality Fixes

## Overview

This document describes three focused fixes to improve `pdf2shinkyu` quality for real 保医発 partial-amendment PDFs (pair #7 style), reducing manual correction needed after extraction.

## Issues Fixed

### Issue #1: Half-width parentheses → Full-width parentheses

**Problem:** PDF extraction sometimes produced half-width `(略)` instead of the required full-width `（略）`.

**Solution:** Added normalization in the `page_lines()` function (line ~119) to convert half-width parentheses to full-width during character extraction:

```python
# Issue #1 fix: Normalize half-width parentheses to full-width
char_text = c["text"].replace("(", "（").replace(")", "）")
```

**Impact:** 
- All special markers `（略）`, `（新設）`, `（削る）` now consistently use full-width parentheses
- Matches expected format in existing test fixtures
- No manual correction needed for parenthesis style

**Note:** This normalization is applied wholesale to all extracted text. If source PDFs contain intentional half-width parentheses (e.g., in tables or technical notation), those will also be converted to full-width. For 保医発 新旧対照表 documents, this is not an issue as the format consistently uses full-width Japanese punctuation.

### Issue #2: Hierarchy indent corrections

**Problem:** Items sometimes appeared at wrong nesting levels (incorrect indentation depth).

**Solution:** Two improvements:

1. **Paragraph detection threshold** (line ~83-85): Increased thresholds for detecting new paragraphs vs. continuations to be more conservative:
   ```python
   # Issue #2 fix: More conservative paragraph detection
   x_threshold = 20 if after_label else 8
   ```

2. **Depth safety check** (line ~79): Added explicit non-negative depth check to prevent negative indentation:
   ```python
   # Ensure depth is non-negative
   depth = max(0, len(self.kinds) - 1)
   ```

**Impact:**
- More accurate hierarchy detection from PDF layout
- Correct 2-space indentation per nesting level
- Reduced incorrect paragraph breaks

### Issue #3: Spurious 「第」 characters from column cropping

**Problem:** Text from adjacent columns sometimes leaked into the extracted content, causing extra 「第」 characters to appear at line endings (e.g., "届出に関する手続き第").

**Solution:** Added gap-based detection in `page_lines()` (lines ~126-141) to remove isolated trailing characters:

```python
# Issue #3 fix: Remove trailing isolated characters near the column boundary
# These are typically from the adjacent column (e.g., trailing 「第」)
if char_list and char_list[-1] is not None:
    last_char = char_list[-1]
    # Check if last character is within 10 points of the right boundary
    if x1 - last_char["x1"] < 10:
        # Check if there's a large gap before it (indicating it's isolated)
        gap = last_char["x0"] - prev_char["x1"]
        # If gap > 200 points, it's likely from the other column
        if gap > 200:
            chars.pop()  # Remove the spurious character
```

**Algorithm:**
1. After extracting all characters in a line, check the last character
2. If it's near the column boundary (< 10 points from edge) AND
3. Has a large gap before it (> 200 points), then
4. Remove it as spurious text from the adjacent column

**Impact:**
- Isolated trailing characters from column bleed are removed
- Cleaner extraction without spurious 「第」 at line endings
- No impact on legitimate text (which doesn't have 200+ point gaps)

## Testing

### Unit Tests

Created `tests/test_pdf2shinkyu_quality.py` to verify:
- ✓ PLACE dictionary uses full-width parentheses
- ✓ Hierarchy depth generates correct indentation
- ✓ Column boundary logic works correctly
- ✓ norm() function handles full-width parens

### Integration Tests

Created `tests/test_quality_integration.py` to verify:
- ✓ Fixtures use full-width （略）
- ✓ No half-width (略) in output

### Existing Test Suite

All existing tests pass:
- ✓ `test_partial_apply.py` - partial amendment mode
- ✓ `test_partial_refs.py` - reference tracking
- ✓ Example roundtrip tests

## Regression Safety

- Changes are localized to the `page_lines()` and label extraction logic in `pdf2shinkyu.py`
- No changes to core data structures or the apply/diff/render pipeline
- All existing tests continue to pass
- Backward compatible with existing `.shinkyu.txt` files

## Known Limitations

### Still may need manual correction:

1. **Complex table layouts** - Multi-column tables with irregular spacing may still have alignment issues
2. **OCR artifacts** - Scanned PDFs with poor quality may have character recognition errors
3. **Unusual formatting** - Non-standard document layouts not following typical 新旧対照表 conventions
4. **Reference resolution** - Cross-references to sections not in the partial amendment may need verification

### Out of scope (as specified):

- Q&A / 事務連絡 parsers (different document structure)
- Changing `--partial` apply semantics (already implemented in PR #3)
- Broad rewrite of PDF pipeline (focused fixes only)

## Example Improvement

**Before fixes:**
```
 第１　基本事項
   １　共通項目
     ①～③　(略)              # Half-width parens
    ④　旧規定である。         # Wrong indent (1 space instead of 5)
```

**After fixes:**
```
 第１　基本事項
   １　共通項目
     ①～③　（略）            # Full-width parens
     ④　旧規定である。       # Correct indent (5 spaces = depth 2)
```

### Issue #4: Combined-Label Splitting

**Problem:** PDF #7 has `第３・第４ （略）` as a combined label. When ingested as-is, `apply --partial` fails because base documents have separate `第３` and `第４` sections.

**Solution:** Split combined labels into individual entries during ingest.

**Scope - ONLY:**
- Pattern: `第N・第M （略）` or `第N・第M・第K... （略）`
- **Required:** ALL parts must start with `第`
- **Required:** Text must be `（略）`

```python
# Detection (line ~60-76)
combined_match = re.match(r"^(第[０-９0-9]+(?:・第[０-９0-9]+)+)\s+(.+)$", t)

# Splitting (lines ~189-209)
def split_combined_labels(entries):
    if e.label and "・" in e.label and e.text.strip() == "（略）":
        parts = [p.strip() for p in e.label.split("・")]
        # ONLY if ALL parts start with 第
        if all(p.startswith("第") for p in parts) and len(parts) > 1:
            # Split into separate entries
```

**Examples:**

IN SCOPE (split):
- `第３・第４ （略）` → `第３ （略）`, `第４ （略）`
- `第１・第２・第３ （略）` → `第１ （略）`, `第２ （略）`, `第３ （略）`

OUT OF SCOPE (NOT split):
- `第３・４ （略）` - second part missing `第`
- `１・２ （略）` - no `第` prefix
- `第３・第４ 内容` - text not `（略）`

**Impact:**
- Combined labels split before matching during apply
- Individual sections can now match with base document
- `apply --partial` succeeds with real PDF #7

## Files Modified

- `pdf2shinkyu.py` - Core extraction logic (4 focused fixes)
- `tests/test_pdf2shinkyu_quality.py` - Unit tests (issues #1-3)
- `tests/test_combined_label_split.py` - Unit tests (issue #4)
- `tests/test_quality_integration.py` - Integration test
- `tests/fixtures/test_quality_issues.txt` - Test fixture
- `PDF2SHINKYU_QUALITY_FIXES.md` - This documentation

## Next Steps

After merging these fixes:

1. **Re-run pair #7 extraction** with the improved `pdf2shinkyu` to verify reduction in manual corrections
2. **Document remaining issues** encountered during pair #7 extraction for future improvements
3. **Consider additional edge cases** if more real PDFs reveal new patterns

## References

- Original validation report: `/workspace/artifacts/VALIDATION_REPORT.md`
- Issue description: PR goal focused on pair #7 style PDFs
- Test coverage: All tests in `tests/` directory
