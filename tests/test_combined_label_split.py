#!/usr/bin/env python3
"""Test for combined-label splitting: ONLY 第N・第M...（略）patterns"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf2shinkyu import Entry, split_combined_labels

def test_split_dai_dai_pattern():
    """Test splitting 第N・第M（略）pattern"""
    print("Test: Split 第N・第M（略）pattern")
    
    e = Entry((1, 100), "第３・第４", "（略）", depth=0)
    result = split_combined_labels([e])
    
    assert len(result) == 2, f"Expected 2 entries, got {len(result)}"
    assert result[0].label == "第３", f"First label should be 第３, got {result[0].label}"
    assert result[1].label == "第４", f"Second label should be 第４, got {result[1].label}"
    assert result[0].text == "（略）", "First entry text should be （略）"
    assert result[1].text == "（略）", "Second entry text should be （略）"
    
    print("  ✓ 第３・第４（略）→ 第３（略）, 第４（略）")
    return True

def test_split_three_parts():
    """Test splitting 第N・第M・第K（略）pattern"""
    print("Test: Split 第N・第M・第K（略）pattern")
    
    e = Entry((1, 100), "第１・第２・第３", "（略）", depth=0)
    result = split_combined_labels([e])
    
    assert len(result) == 3, f"Expected 3 entries, got {len(result)}"
    assert result[0].label == "第１"
    assert result[1].label == "第２"
    assert result[2].label == "第３"
    
    print("  ✓ 第１・第２・第３（略）→ 3 separate entries")
    return True

def test_no_split_without_ryaku():
    """Test NO split when text is not （略）"""
    print("Test: NO split when text is not （略）")
    
    e = Entry((1, 100), "第３・第４", "届出受理後の措置等", depth=0)
    result = split_combined_labels([e])
    
    assert len(result) == 1, "Should NOT split - text is not （略）"
    assert result[0].label == "第３・第４", "Label should remain combined"
    
    print("  ✓ NOT split (text not （略）)")
    return True

def test_no_split_single_label():
    """Test NO split for single label"""
    print("Test: NO split for single label")
    
    e = Entry((1, 100), "第３", "（略）", depth=0)
    result = split_combined_labels([e])
    
    assert len(result) == 1, "Should NOT split single label"
    assert result[0].label == "第３"
    
    print("  ✓ NOT split (single label)")
    return True

def test_no_split_numeric_pattern():
    """Test NO split for numeric patterns (out of scope)"""
    print("Test: NO split for １・２（略）pattern (out of scope)")
    
    e = Entry((1, 100), "１・２", "（略）", depth=1)
    result = split_combined_labels([e])
    
    # Should NOT split - not 第N pattern
    assert len(result) == 1, "Should NOT split - not 第N・第M pattern"
    assert result[0].label == "１・２"
    
    print("  ✓ NOT split (numeric pattern out of scope)")
    return True

def test_no_split_abbreviated_pattern():
    """Test NO split for 第N・M pattern (out of scope)"""
    print("Test: NO split for 第３・４（略）pattern (out of scope)")
    
    e = Entry((1, 100), "第３・４", "（略）", depth=0)
    result = split_combined_labels([e])
    
    # Should NOT split - second part missing 第
    assert len(result) == 1, "Should NOT split - second part missing 第"
    assert result[0].label == "第３・４"
    
    print("  ✓ NOT split (abbreviated pattern out of scope)")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("COMBINED LABEL SPLIT TESTS (NARROWED SCOPE)")
    print("=" * 60)
    print()
    
    all_passed = True
    
    tests = [
        test_split_dai_dai_pattern,
        test_split_three_parts,
        test_no_split_without_ryaku,
        test_no_split_single_label,
        test_no_split_numeric_pattern,
        test_no_split_abbreviated_pattern,
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
