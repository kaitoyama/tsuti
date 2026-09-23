#!/usr/bin/env python3
"""Test for combined-label splitting (e.g., 第３・第４ → separate entries)"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf2shinkyu import Entry, split_combined_labels

def test_split_combined_dai_labels():
    """Test splitting combined 第N・第M labels"""
    print("Test: Split combined 第N・第M labels")
    
    # Create an entry with combined label: 第３・第４ （略）
    e = Entry((1, 100), "第３・第４", "（略）", depth=0)
    
    result = split_combined_labels([e])
    
    # Should split into two entries
    assert len(result) == 2, f"Expected 2 entries, got {len(result)}"
    assert result[0].label == "第３", f"First label should be 第３, got {result[0].label}"
    assert result[1].label == "第４", f"Second label should be 第４, got {result[1].label}"
    assert result[0].text == "（略）", "First entry text should be （略）"
    assert result[1].text == "（略）", "Second entry text should be （略）"
    
    print("  ✓ 第３・第４ split into 第３ and 第４")
    return True

def test_no_split_without_dot():
    """Test that labels without ・ are not split"""
    print("Test: No split for labels without ・")
    
    e = Entry((1, 100), "第３", "内容", depth=0)
    result = split_combined_labels([e])
    
    assert len(result) == 1, "Should not split single label"
    assert result[0].label == "第３", "Label should remain unchanged"
    
    print("  ✓ Single label not split")
    return True

def test_no_split_with_content():
    """Test that combined labels with actual content are not split"""
    print("Test: No split for combined labels with content (not 略)")
    
    e = Entry((1, 100), "第３・第４", "届出受理後の措置等", depth=0)
    result = split_combined_labels([e])
    
    # Should NOT split because text is not （略）
    assert len(result) == 1, "Should not split when text is not （略）"
    assert result[0].label == "第３・第４", "Label should remain combined"
    
    print("  ✓ Combined label with content not split")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("COMBINED LABEL SPLIT TESTS")
    print("=" * 60)
    print()
    
    all_passed = True
    
    tests = [
        test_split_combined_dai_labels,
        test_no_split_without_dot,
        test_no_split_with_content,
    ]
    
    for test_func in tests:
        try:
            result = test_func()
            all_passed &= result
            print()
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            all_passed = False
            print()
    
    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
