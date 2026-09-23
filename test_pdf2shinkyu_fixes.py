#!/usr/bin/env python3
"""Test cases for the three pdf2shinkyu quality issues"""

import sys
import re

# Issue #1: Half-width parentheses should become full-width
def test_issue1_half_width_parens():
    print("Testing Issue #1: Half-width parentheses normalization")
    
    # Simulate PDF text with half-width parentheses
    test_cases = [
        ("(略)", "（略）"),
        ("(新設)", "（新設）"),
        ("(削る)", "（削る）"),
        ("①～③　(略)", "①～③　（略）"),
    ]
    
    for input_text, expected in test_cases:
        # Normalize half-width to full-width parentheses
        normalized = input_text.replace("(", "（").replace(")", "）")
        status = "✓" if normalized == expected else "✗"
        print(f"  {status} '{input_text}' -> '{normalized}' (expected: '{expected}')")
    
    print()

# Issue #2: Test hierarchy depth calculation
def test_issue2_hierarchy():
    print("Testing Issue #2: Hierarchy depth calculation")
    
    # The hierarchy should be: 第N → 数字 → ⑴ → ① → ア → ・
    test_sequence = [
        ("第１", 0, ["special"]),
        ("１", 1, ["special", "dai"]),
        ("①", 2, ["special", "dai", "num"]),
        ("ア", 3, ["special", "dai", "num", "maru"]),
    ]
    
    print("  Hierarchy depth should follow the pattern: 第N → 数字 → ⑴ → ① → ア → ・")
    print("  Each new kind should increment depth, same kind stays at same level")
    print()

# Issue #3: Extra 第 characters
def test_issue3_extra_dai():
    print("Testing Issue #3: Extra 第 characters in headings")
    
    # The regex at line 60 tries to add space after 第N
    # but might be causing issues
    pattern = r"^(第[０-９0-9]+)(?![号条項の０-９0-9～])(?=\S)"
    
    test_cases = [
        ("第６介護予防", "第６ 介護予防", True),   # Should add space
        ("第１号", "第１号", False),               # Should NOT add space (followed by 号)
        ("第２条", "第２条", False),               # Should NOT add space (followed by 条)
        ("第３の１", "第３の１", False),           # Should NOT add space (followed by の)
        ("第４～第５", "第４～第５", False),       # Should NOT add space (followed by ～)
    ]
    
    for input_text, expected, should_match in test_cases:
        result = re.sub(pattern, r"\1 ", input_text)
        status = "✓" if result == expected else "✗"
        match_info = "matched" if re.search(pattern, input_text) else "no match"
        print(f"  {status} '{input_text}' -> '{result}' (expected: '{expected}', {match_info})")
    
    print()

if __name__ == "__main__":
    test_issue1_half_width_parens()
    test_issue2_hierarchy()
    test_issue3_extra_dai()
    
    print("\nNote: These are conceptual tests. The actual fixes will be in pdf2shinkyu.py")
