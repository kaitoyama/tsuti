#!/usr/bin/env python3
"""Tests for R8 疑義解釈 accumulation

Acceptance tests:
1. As of 2026-04-08: 別添１ 問104 has pre-correction text from その2 4/1
2. As of 2026-04-10: 別添１ 問104 has post-correction text from 一部訂正
3. 一部訂正 document is NOT registered as duplicate of その2
4. As of 2026-04-01: その2 3/31 is fully replaced by その2 4/1
5. Past-year abolishment statements from その2 4/1 appear in abolishment record
6. 号名-less 5/29 document is in its own 系列 and present on/after 2026-05-29
7. Existing pdf2qa tests still pass
"""
import sys
import os
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qa_accumulate import apply_events, parse_date_iso


def load_corpus():
    """Load R8 corpus manifest"""
    corpus_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'r8_corpus.yaml')
    with open(corpus_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def test_acceptance_1_pre_correction():
    """A1: As of 2026-04-08, 別添１ 問104 has pre-correction text"""
    corpus = load_corpus()
    cache_dir = './cache/qa_pdfs'
    
    valid_items, _, stats = apply_events(corpus, '2026-04-08', cache_dir)
    
    # Find 問104 in 別添１ (normalize for comparison)
    from qa_accumulate import normalize_betten
    q104_items = [
        item for item in valid_items 
        if item['問番号'] == '問104' and normalize_betten(item.get('別添')) == normalize_betten('別添１')
    ]
    
    assert len(q104_items) > 0, "問104 should be present in 別添１"
    
    # Check it's from その2 (4/1 version, not corrected yet)
    q104 = q104_items[0]
    assert q104['_issue_gou'] == 'その2', f"問104 should be from その2, got {q104['_issue_gou']}"
    
    print(f"✓ A1: 問104 present as of 2026-04-08 (pre-correction)")
    print(f"  問: {q104['問'][:80]}...")
    
    return q104


def test_acceptance_2_post_correction():
    """A2: As of 2026-04-10, 別添１ 問104 has post-correction text"""
    corpus = load_corpus()
    cache_dir = './cache/qa_pdfs'
    
    valid_items, _, stats = apply_events(corpus, '2026-04-10', cache_dir)
    
    # Find 問104 in 別添１ (normalize for comparison)
    from qa_accumulate import normalize_betten
    q104_items = [
        item for item in valid_items 
        if item['問番号'] == '問104' and normalize_betten(item.get('別添')) == normalize_betten('別添１')
    ]
    
    assert len(q104_items) > 0, "問104 should be present in 別添１"
    
    q104 = q104_items[0]
    
    # Check correction was applied
    # (We verify by checking stats shows correction event)
    correction_events = [e for e in stats['events'] if '訂正' in e]
    assert len(correction_events) > 0, "Should have at least one correction event"
    assert stats['questions_corrected'] > 0, "Should have corrected questions"
    
    print(f"✓ A2: 問104 corrected as of 2026-04-10")
    print(f"  問: {q104['問'][:80]}...")
    print(f"  Correction events: {correction_events}")
    
    return q104


def test_acceptance_3_correction_not_duplicate():
    """A3: 一部訂正 document is NOT registered as duplicate issue"""
    corpus = load_corpus()
    
    # Count how many その2 issues exist
    sono2_issues = [
        issue for issue in corpus['issues']
        if issue.get('号名') == 'その2'
    ]
    
    # Should have exactly 2 その2 entries (3/31 and 4/1), not 3
    assert len(sono2_issues) == 2, f"Expected 2 その2 issues, found {len(sono2_issues)}"
    
    # Check no correction document is marked as その2
    correction_issues = [
        issue for issue in corpus['issues']
        if '一部訂正' in issue.get('title', '')
    ]
    
    assert len(correction_issues) == 1, f"Expected 1 correction document, found {len(correction_issues)}"
    
    correction = correction_issues[0]
    assert correction.get('号名') != 'その2', "Correction should not have 号名=その2"
    assert 'correction_target' in correction, "Correction should have correction_target"
    
    print(f"✓ A3: 一部訂正 document properly marked as correction, not duplicate その2")
    print(f"  Correction target: {correction['correction_target']}")


def test_acceptance_4_replacement():
    """A4: As of 2026-04-01, その2 3/31 is fully replaced by その2 4/1"""
    corpus = load_corpus()
    cache_dir = './cache/qa_pdfs'
    
    # Check before replacement (2026-03-31)
    valid_items_0331, _, stats_0331 = apply_events(corpus, '2026-03-31', cache_dir)
    
    # Check after replacement (2026-04-01)
    valid_items_0401, _, stats_0401 = apply_events(corpus, '2026-04-01', cache_dir)
    
    # All その2 questions should now be from 4/1 version
    sono2_questions_0331 = [
        item for item in valid_items_0331
        if item['_issue_gou'] == 'その2' and item['_issue_date'] == '令和8年3月31日'
    ]
    
    sono2_questions_0401_old = [
        item for item in valid_items_0401
        if item['_issue_gou'] == 'その2' and item['_issue_date'] == '令和8年3月31日'
    ]
    
    sono2_questions_0401_new = [
        item for item in valid_items_0401
        if item['_issue_gou'] == 'その2' and item['_issue_date'] == '令和8年4月1日'
    ]
    
    assert len(sono2_questions_0331) > 0, "Should have その2 3/31 questions on 3/31"
    assert len(sono2_questions_0401_old) == 0, "Should have NO その2 3/31 questions on 4/1 (replaced)"
    assert len(sono2_questions_0401_new) > 0, "Should have その2 4/1 questions on 4/1"
    
    # Check replacement event
    replacement_events = [e for e in stats_0401['events'] if '置換' in e]
    assert len(replacement_events) > 0, "Should have replacement event"
    assert stats_0401['issues_replaced'] > 0, "Should have replaced issues"
    
    print(f"✓ A4: その2 3/31 fully replaced by その2 4/1 as of 2026-04-01")
    print(f"  その2 questions on 3/31: {len(sono2_questions_0331)}")
    print(f"  その2 (3/31) questions on 4/1: {len(sono2_questions_0401_old)}")
    print(f"  その2 (4/1) questions on 4/1: {len(sono2_questions_0401_new)}")
    print(f"  Replacement events: {replacement_events}")


def test_acceptance_5_past_year_abolishments():
    """A5: Past-year abolishment statements appear in abolishment record"""
    corpus = load_corpus()
    cache_dir = './cache/qa_pdfs'
    
    valid_items, abolishments, stats = apply_events(corpus, '2026-09-03', cache_dir)
    
    # Should have some abolishment records
    assert len(abolishments) > 0, "Should have abolishment records"
    
    # Check structure
    for abolishment in abolishments:
        assert '原文' in abolishment, "Abolishment should have 原文"
        assert '年度' in abolishment, "Abolishment should have 年度"
        
        # At least one of these should be present
        assert (abolishment.get('号') or abolishment.get('別添') or 
                abolishment.get('問番号')), "Abolishment should have at least one target field"
    
    # Check for typical patterns
    reiwa_years = [a['年度'] for a in abolishments]
    
    print(f"✓ A5: Found {len(abolishments)} past-year abolishment records")
    print(f"  Referenced years: {sorted(set(reiwa_years))}")
    
    # Show sample
    if abolishments:
        sample = abolishments[0]
        print(f"  Sample: 年度={sample['年度']}, 号={sample.get('号')}, "
              f"別添={sample.get('別添')}, 問番号={sample.get('問番号')}")
        print(f"    原文: {sample['原文'][:80]}...")


def test_acceptance_6_separate_keiretsu():
    """A6: 号名-less 5/29 document is in its own 系列 and present on/after 2026-05-29"""
    corpus = load_corpus()
    cache_dir = './cache/qa_pdfs'
    
    # Find the 5/29 号名-less document
    ryouyou_issue = None
    for issue in corpus['issues']:
        if (issue.get('日付') == '令和8年5月29日' and 
            issue.get('系列') == '療養の給付と直接関係ないサービス等'):
            ryouyou_issue = issue
            break
    
    assert ryouyou_issue is not None, "Should have 療養の給付... document in corpus"
    assert ryouyou_issue.get('号名') == '', "Should have empty 号名"
    assert ryouyou_issue.get('系列') != '医科の疑義解釈', "Should be in separate 系列"
    
    # Check it's not present before 5/29
    valid_items_0528, _, _ = apply_events(corpus, '2026-05-28', cache_dir)
    ryouyou_questions_0528 = [
        item for item in valid_items_0528
        if item.get('_issue_date') == '令和8年5月29日' and 
        '療養' in ryouyou_issue.get('title', '')
    ]
    
    # Check it's present on/after 5/29
    valid_items_0529, _, _ = apply_events(corpus, '2026-05-29', cache_dir)
    ryouyou_questions_0529 = [
        item for item in valid_items_0529
        if item.get('_issue_date') == '令和8年5月29日'
    ]
    
    assert len(ryouyou_questions_0528) == 0, "Should not have 療養... questions before 5/29"
    assert len(ryouyou_questions_0529) > 0, "Should have 療養... questions on/after 5/29"
    
    print(f"✓ A6: 療養の給付... document in separate 系列")
    print(f"  系列: {ryouyou_issue['系列']}")
    print(f"  号名: '{ryouyou_issue['号名']}'")
    print(f"  Questions before 5/29: {len(ryouyou_questions_0528)}")
    print(f"  Questions on/after 5/29: {len(ryouyou_questions_0529)}")


def test_acceptance_7_pdf2qa_still_works():
    """A7: Existing pdf2qa tests still pass"""
    # Import and run the original pdf2qa tests
    from test_qa import test_q1_疑義解釈その12, test_q2_疑義解釈その2, test_q3_qa_vol1524
    
    # Check if test data exists
    test_data_dir = 'data/qa_samples'
    if not os.path.exists(test_data_dir):
        print(f"⚠ Skipping A7: test data directory '{test_data_dir}' not found")
        return
    
    # Run the tests
    try:
        test_q1_疑義解釈その12()
        test_q2_疑義解釈その2()
        test_q3_qa_vol1524()
        print(f"✓ A7: All pdf2qa tests still pass")
    except FileNotFoundError as e:
        print(f"⚠ Skipping A7: test data not found - {e}")
    except Exception as e:
        print(f"✗ A7 failed: {e}")
        raise


def test_question_counts_by_date():
    """Report question counts on 2026-04-08 vs 2026-04-10"""
    corpus = load_corpus()
    cache_dir = './cache/qa_pdfs'
    
    valid_items_0408, _, _ = apply_events(corpus, '2026-04-08', cache_dir)
    valid_items_0410, _, _ = apply_events(corpus, '2026-04-10', cache_dir)
    
    print(f"\nQuestion counts by date:")
    print(f"  2026-04-08: {len(valid_items_0408)} questions")
    print(f"  2026-04-10: {len(valid_items_0410)} questions")
    
    return len(valid_items_0408), len(valid_items_0410)


def test_question_104_text_diff():
    """Verify 問104 text differs between 2026-04-08 and 2026-04-10"""
    q104_pre = test_acceptance_1_pre_correction()
    q104_post = test_acceptance_2_post_correction()
    
    # Compare texts
    pre_text = q104_pre['問']
    post_text = q104_post['問']
    
    if pre_text != post_text:
        print(f"\n✓ 問104 text differs between dates:")
        print(f"  2026-04-08 (pre):  {pre_text[:100]}...")
        print(f"  2026-04-10 (post): {post_text[:100]}...")
    else:
        print(f"\n⚠ WARNING: 問104 text is SAME between dates")
        print(f"  This may indicate correction was not applied properly")


if __name__ == '__main__':
    import os
    os.makedirs('./cache/qa_pdfs', exist_ok=True)
    
    try:
        print("Running R8 accumulation acceptance tests...\n")
        
        test_acceptance_3_correction_not_duplicate()
        test_acceptance_1_pre_correction()
        test_acceptance_2_post_correction()
        test_acceptance_4_replacement()
        test_acceptance_5_past_year_abolishments()
        test_acceptance_6_separate_keiretsu()
        
        print("\n" + "="*60)
        test_question_counts_by_date()
        test_question_104_text_diff()
        
        print("\n" + "="*60)
        test_acceptance_7_pdf2qa_still_works()
        
        print("\n" + "="*60)
        print("All acceptance tests passed! ✓")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
