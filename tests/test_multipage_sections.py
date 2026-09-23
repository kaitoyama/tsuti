#!/usr/bin/env python3
"""Regression test for multi-page section dropping bug in pdf2tsuchi

Tests that sections appearing many pages after their parent are not dropped.
Specifically tests that 第２の５ and 第２の６ (appearing on page 16) are
correctly parsed even when 第２ appears on page 2.
"""

import sys
import os
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tsuchi import load


def test_t1_multipage_sections():
    """Test that T1 PDF correctly parses multi-page sections"""
    print("Regression Test: Multi-page Section Preservation (T1 PDF)")
    
    pdf_path = "test_data/T1_001293315.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"  ⚠ Skipping: {pdf_path} not found")
        print("  Download with: curl -L -o test_data/T1_001293315.pdf 'https://www.mhlw.go.jp/content/12404000/001293315.pdf'")
        return None
    
    # Run pdf2tsuchi on T1
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsuchi.txt', delete=False) as f:
        output_path = f.name
    
    try:
        result = subprocess.run([
            'python3', 'pdf2tsuchi.py', pdf_path,
            '-o', output_path,
            '--number', '保医発0305第6号',
            '--date', '2024-03-05',
            '--version', 'R6.3.5',
            '--title', '特掲診療料の施設基準等及びその届出に関する手続きの取扱いについて'
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"  ✗ pdf2tsuchi failed: {result.stderr}")
            return False
        
        # Load and check structure
        meta, root = load(output_path)
        
        # Find 第２ section
        dai2 = None
        for child in root.children:
            if child.label == '第２':
                dai2 = child
                break
        
        if not dai2:
            print("  ✗ 第２ section not found")
            return False
        
        print(f"  ✓ Found 第２: {dai2.text[:40]}...")
        
        # Check for numbered children
        num_children = [c for c in dai2.children if c.kind == 'num']
        num_labels = [c.label for c in num_children]
        
        print(f"  Found numbered children: {num_labels}")
        
        # Check that ５ and ６ are present
        if '５' not in num_labels:
            print("  ✗ Missing ５ under 第２")
            return False
        print("  ✓ Found ５ under 第２")
        
        if '６' not in num_labels:
            print("  ✗ Missing ６ under 第２")
            return False
        print("  ✓ Found ６ under 第２")
        
        # Check that they appear in correct order
        if num_labels[:9] != ['１', '２', '３', '４', '５', '６', '７', '８', '９']:
            print(f"  ✗ Incorrect order: {num_labels[:9]}")
            return False
        print("  ✓ Sections １-９ in correct order")
        
        return True
        
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


if __name__ == "__main__":
    print("MULTIPAGE SECTION REGRESSION TEST")
    result = test_t1_multipage_sections()
    if result is None:
        print("\nTest skipped (PDF not available)")
        sys.exit(0)
    elif result:
        print("\n✓ All tests passed")
        sys.exit(0)
    else:
        print("\n✗ Tests failed")
        sys.exit(1)
