#!/usr/bin/env python3
"""Regression tests for sono spacing bugs (Bug 1 and Bug 2)

Bug 1: Handle half-width space in その N patterns
Bug 2: Don't treat question references (like 問122 の③) as new questions
"""
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_sono_spacing_regex():
    """Test that the regex pattern handles various spacing in その N"""
    pattern = r"[（(]その\s*[０-９0-9１-９]+[）)]"
    
    # No space (existing case)
    text1 = "疑義解釈資料の送付について（その12）"
    match1 = re.search(pattern, text1)
    assert match1 is not None, "Should match その12 without space"
    result1 = re.sub(r"[（(）)\s]", "", match1.group(0))
    assert result1 == "その12", f"Expected 'その12', got '{result1}'"
    
    # Half-width space (Bug 1 - P4 R4 その65)
    text2 = "疑義解釈資料の送付について（その 65）"
    match2 = re.search(pattern, text2)
    assert match2 is not None, "Should match その 65 with half-width space"
    result2 = re.sub(r"[（(）)\s]", "", match2.group(0))
    assert result2 == "その65", f"Expected 'その65', got '{result2}'"
    
    # Three-digit with space (Bug 1 - P6 R2 その101)
    text3 = "疑義解釈資料の送付について（その 101）"
    match3 = re.search(pattern, text3)
    assert match3 is not None, "Should match その 101 with half-width space"
    result3 = re.sub(r"[（(）)\s]", "", match3.group(0))
    assert result3 == "その101", f"Expected 'その101', got '{result3}'"
    
    print("✓ Sono spacing regex tests passed")


def test_question_reference_detection():
    """Test that question references are distinguished from real questions"""
    
    # Reference: "問122 の③" should be detected as reference (の particle)
    ref_line = "問122 の③及び④の場合について、それぞれどのように考えればよいか。"
    q_match = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.)", ref_line)
    assert q_match is not None, "Should match pattern"
    assert q_match.group(2) == 'の', "Should detect の particle indicating reference"
    
    # Real question: should not start with の
    real_line = "問 124 精神科救急急性期医療入院料等の施設基準について"
    q_match2 = re.match(r"^(問\s*[０-９0-9１-９]+[－\-]?[０-９0-9１-９]*|Q[０-９0-9１-９]+)\s+(.)", real_line)
    assert q_match2 is not None, "Should match real question"
    assert q_match2.group(2) != 'の', "Real question should not start with の"
    
    print("✓ Question reference detection tests passed")


def test_sono65_metadata():
    """Test Bug 1 fix: P4 R4 その65 metadata extraction"""
    try:
        from pdf2qa import parse
        import os
        
        pdf_path = "test_pdfs/sono65.pdf"
        if not os.path.exists(pdf_path):
            print(f"⊘ Skipping {pdf_path} test (file not found)")
            return
        
        meta, items = parse(pdf_path)
        
        # Bug 1: 番号 should be extracted despite space in subject
        assert "番号" in meta, "Should have 番号 field"
        assert meta["番号"] == "その65", f"Expected 'その65', got '{meta['番号']}'"
        assert "件名" in meta, "Should have 件名 field"
        assert "その 65" in meta["件名"], "Subject should contain 'その 65' with space"
        
        print(f"✓ sono65 test passed (番号: {meta['番号']})")
    except ImportError:
        print("⊘ Skipping sono65 test (pdfplumber not available)")


def test_sono101_metadata():
    """Test Bug 1 fix: P6 R2 その101 metadata extraction"""
    try:
        from pdf2qa import parse
        import os
        
        pdf_path = "test_pdfs/sono101.pdf"
        if not os.path.exists(pdf_path):
            print(f"⊘ Skipping {pdf_path} test (file not found)")
            return
        
        meta, items = parse(pdf_path)
        
        # Bug 1: 番号 should be extracted despite space in subject
        assert "番号" in meta, "Should have 番号 field"
        assert meta["番号"] == "その101", f"Expected 'その101', got '{meta['番号']}'"
        assert "件名" in meta, "Should have 件名 field"
        assert "その 101" in meta["件名"], "Subject should contain 'その 101' with space"
        
        print(f"✓ sono101 test passed (番号: {meta['番号']})")
    except ImportError:
        print("⊘ Skipping sono101 test (pdfplumber not available)")


def test_sono1_q124_answer():
    """Test Bug 2 fix: P1 R6 その1 問124 should have non-empty answer"""
    try:
        from pdf2qa import parse
        import os
        
        pdf_path = "test_pdfs/sono1.pdf"
        if not os.path.exists(pdf_path):
            print(f"⊘ Skipping {pdf_path} test (file not found)")
            return
        
        meta, items = parse(pdf_path)
        
        # Find 問124 (could be "問124" or "問 124")
        q124 = None
        for item in items:
            if '124' in item['問番号'] and '問' in item['問番号']:
                # Make sure it's actually 124, not 1240 or something
                q_num_clean = re.sub(r'\s', '', item['問番号'])
                if q_num_clean == '問124':
                    q124 = item
                    break
        
        assert q124 is not None, "Should find 問124"
        
        # Bug 2: 答 should not be empty
        assert "答" in q124, "問124 should have 答 field"
        assert isinstance(q124["答"], list), "答 should be a list"
        assert len(q124["答"]) > 0, "問124 答 should not be empty"
        
        # Check it contains the expected answer text
        answer_text = "".join(q124["答"])
        assert "分母に計上" in answer_text, "Answer should contain expected text"
        assert "分子には計上しない" in answer_text, "Answer should contain expected text"
        
        # Check question text contains reference to 問122
        assert "問122" in q124["問"], "Question should reference 問122"
        
        print(f"✓ sono1 問124 test passed (答 has {len(q124['答'])} paragraphs)")
    except ImportError:
        print("⊘ Skipping sono1 test (pdfplumber not available)")


if __name__ == "__main__":
    try:
        # Unit tests (always run)
        test_sono_spacing_regex()
        test_question_reference_detection()
        
        # PDF-based tests (run if PDFs available)
        test_sono65_metadata()
        test_sono101_metadata()
        test_sono1_q124_answer()
        
        print("\n✓ All regression tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
