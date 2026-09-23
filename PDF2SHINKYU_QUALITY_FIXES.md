# pdf2shinkyu Quality Fixes

## Overview

This document describes three focused fixes to improve `pdf2shinkyu` quality for real 保医発 partial-amendment PDFs (pair #7 style), reducing manual correction needed after extraction.

## Issues Fixed

### Issue #1: Half-width parentheses → Full-width parentheses

**Problem:** PDF extraction sometimes produced half-width `(略)` instead of the required full-width `（略）`.

**Solution:** Added normalization in the `page_lines()` function (line ~109) to convert half-width parentheses to full-width during character extraction:

```python
# Issue #1 fix: Normalize half-width parentheses to full-width
char_text = c["text"].replace("(", "（").replace(")", "）")
```

**Impact:** 
- All special markers `（略）`, `（新設）`, `（削る）` now consistently use full-width parentheses
- Matches expected format in existing test fixtures
- No manual correction needed for parenthesis style

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

**Problem:** Text from adjacent columns sometimes leaked into the extracted content, causing extra 「第」 characters to appear.

**Solution:** Added column boundary check in `page_lines()` (line ~103-105) to skip characters outside the crop bounds:

```python
# Issue #3 fix: Skip characters that are clearly from the other column
# If a character's x position is outside the crop bounds, skip it
if not (x0 <= c["x0"] < x1):
    continue
```

**Impact:**
- Characters from the opposite column (left/right) are now filtered out
- Cleaner extraction without spurious text
- Fewer formatting artifacts from column layout

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

## Files Modified

- `pdf2shinkyu.py` - Core extraction logic (3 focused fixes)
- `tests/test_pdf2shinkyu_quality.py` - New unit tests
- `tests/test_quality_integration.py` - New integration test
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
