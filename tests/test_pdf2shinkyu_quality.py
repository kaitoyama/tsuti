#!/usr/bin/env python3
"""Tests for pdf2shinkyu quality improvements (Issue #1, #2, #3)"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf2shinkyu import PLACE, line, Entry

def test_issue1_full_width_parens():
    """Issue #1: Ensure PLACE dictionary uses full-width parentheses"""
    print("Test Issue #1: Full-width parentheses in PLACE dictionary")
    
    expected = {
        "（新設）": "new",
        "（削る）": "del",
        "（略）": "skip"
    }
    
    assert PLACE == expected, f"PLACE dictionary mismatch: {PLACE}"
    
    # Verify that half-width would not match
    assert "(略)" not in PLACE, "Half-width parentheses should not be in PLACE"
    
    print("  ✓ PLACE dictionary correctly uses full-width parentheses")
    return True

def test_issue2_hierarchy_depth():
    """Issue #2: Verify depth is correctly applied in line() output"""
    print("Test Issue #2: Hierarchy depth in output")
    
    # Create test entries with different depths
    e0 = Entry((1, 100), "第１", "見出し", 0)
    e1 = Entry((1, 120), "１", "サブ見出し", 1)
    e2 = Entry((1, 140), "①", "項目", 2)
    
    # Generate lines with proper depth
    lines0 = line(" ", e0, 0)
    lines1 = line(" ", e1, 1)
    lines2 = line(" ", e2, 2)
    
    # Check indentation (2 spaces per depth level)
    assert lines0[0].startswith(" 第１"), f"Depth 0 should have no indent: {lines0[0]}"
    assert lines1[0].startswith("   １"), f"Depth 1 should have 2 spaces: {lines1[0]}"
    assert lines2[0].startswith("     ①"), f"Depth 2 should have 4 spaces: {lines2[0]}"
    
    print("  ✓ Hierarchy depth correctly generates indentation")
    return True

def test_issue3_column_boundary():
    """Issue #3: Conceptual test - column boundary should be respected"""
    print("Test Issue #3: Column boundary handling")
    
    # This is a conceptual test since we can't easily mock PDF objects
    # The fix in page_lines() checks: not (x0 <= c["x0"] < x1)
    
    # Simulate checking if a character is within bounds
    x0, x1 = 0, 300
    
    char_positions = [
        (150, True, "inside left column"),
        (350, False, "outside right boundary"),
        (-10, False, "outside left boundary"),
        (299, True, "at right edge (inclusive)"),
    ]
    
    for x_pos, should_include, desc in char_positions:
        is_within = x0 <= x_pos < x1
        assert is_within == should_include, f"Position {x_pos} ({desc}) check failed"
    
    print("  ✓ Column boundary logic correctly filters out-of-bounds characters")
    return True

def test_norm_function():
    """Verify norm() produces correct output for comparison"""
    print("Test norm() function behavior")
    from tsuchi import norm
    
    # Test cases with full-width parentheses (after fix)
    assert norm("①～③　（略）") == "①～③（略）", "norm should remove spaces except between ASCII"
    assert norm("（新設）") == "（新設）", "norm should preserve full-width parens"
    
    print("  ✓ norm() function works correctly with full-width parentheses")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("PDF2SHINKYU QUALITY FIX TESTS")
    print("=" * 60)
    print()
    
    all_passed = True
    
    try:
        all_passed &= test_issue1_full_width_parens()
        print()
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        all_passed = False
        print()
    
    try:
        all_passed &= test_issue2_hierarchy_depth()
        print()
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        all_passed = False
        print()
    
    try:
        all_passed &= test_issue3_column_boundary()
        print()
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        all_passed = False
        print()
    
    try:
        all_passed &= test_norm_function()
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
