#!/usr/bin/env python3
"""Integration test for pdf2shinkyu quality fixes"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_fixture_format():
    """Test that fixtures use correct format"""
    print("Integration Test: Fixture Format Validation")
    
    fixture_path = "tests/fixtures/partial_amendment.shinkyu.txt"
    
    with open(fixture_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for full-width parens
    if '(略)' in content:
        print("  ✗ Found half-width (略)")
        return False
    print("  ✓ No half-width (略) found")
    
    # Check for full-width
    if '（略）' in content:
        print("  ✓ Uses full-width （略）")
    
    return True

if __name__ == "__main__":
    print("PDF2SHINKYU QUALITY INTEGRATION TEST")
    result = test_fixture_format()
    sys.exit(0 if result else 1)
