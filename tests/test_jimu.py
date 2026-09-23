#!/usr/bin/env python3
"""Test pdf2jimu on J1-J3 sample 事務連絡 documents"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf2jimu import parse


def test_j1_metadata():
    """J1: Vol 1541, 行方不明者の被保険者資格の喪失手続…"""
    meta, body = parse("data/jimu_samples/J1.pdf")
    
    assert meta["種別"] == "事務連絡"
    assert meta["Vol"] == "1541"
    assert meta["日付"] == "令和８年９月８日"
    assert meta["発出課"] == "厚生労働省老健局介護保険計画課"
    assert "行方不明者の被保険者資格の喪失手続" in meta["件名"]
    assert len(body) > 0, "Body should have paragraphs"
    print("✓ J1 metadata complete")


def test_j2_metadata():
    """J2: Vol 1537, 令和８年度地域支援事業実施要綱等の改正点について"""
    meta, body = parse("data/jimu_samples/J2.pdf")
    
    assert meta["種別"] == "事務連絡"
    assert meta["Vol"] == "1537"
    assert meta["日付"] == "令和８年８月21日"
    assert meta["発出課"] == "厚生労働省老健局認知症施策・地域介護推進課"
    assert "令和８年度地域支援事業実施要綱等の改正点について" in meta["件名"]
    assert len(body) > 0, "Body should have paragraphs"
    print("✓ J2 metadata complete")


def test_j3_metadata():
    """J3: Vol 1543, ケアプランデータ連携システム活用セミナーの開催について"""
    meta, body = parse("data/jimu_samples/J3.pdf")
    
    assert meta["種別"] == "事務連絡"
    assert meta["Vol"] == "1543"
    assert meta["日付"] == "令和８年９月11日"
    assert meta["発出課"] == "厚生労働省老健局高齢者支援課"
    assert "ケアプランデータ連携システム活用セミナー" in meta["件名"]
    assert len(body) > 0, "Body should have paragraphs"
    print("✓ J3 metadata complete")


def test_all_samples_have_body_text():
    """All samples should have non-empty body paragraphs"""
    for sample in ["J1", "J2", "J3"]:
        meta, body = parse(f"data/jimu_samples/{sample}.pdf")
        assert len(body) > 0, f"{sample} should have body paragraphs"
        # Body should contain some actual content
        total_text = "".join(body)
        assert len(total_text) > 100, f"{sample} body should be substantial"
    print("✓ All samples have body text")


if __name__ == "__main__":
    test_j1_metadata()
    test_j2_metadata()
    test_j3_metadata()
    test_all_samples_have_body_text()
    print("\nAll tests passed! ✓")
