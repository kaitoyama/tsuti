#!/usr/bin/env python3
"""Test pdf2kihatsu on K1-K3 sample 基発 documents"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf2kihatsu import parse


def test_k1_metadata():
    """K1: 基発0731第7号 / 2026-07-31 (short, correction notice)"""
    meta, body = parse("data/kihatsu_samples/K1.pdf")
    
    assert meta["種別"] == "基発"
    assert meta["番号"] == "基発0731第7号"
    assert meta["日付"] == "令和８年７月31日"
    assert meta["発出元"] == "厚生労働省労働基準局長"
    assert "定期健康診断等における診断項目の取扱い等について" in meta["件名"]
    assert "一部訂正について" in meta["件名"]
    assert len(body) > 0, "Body should have paragraphs"
    print("✓ K1 metadata complete")


def test_k2_metadata():
    """K2: 基発0919第1号 / 2025-09-19 (short, regulation enforcement)"""
    meta, body = parse("data/kihatsu_samples/K2.pdf")
    
    assert meta["種別"] == "基発"
    assert meta["番号"] == "基発0919第1号"
    assert meta["日付"] == "令和７年９月19日"
    assert meta["発出元"] == "厚生労働省労働基準局長"
    assert "労働安全衛生規則の一部を改正する省令等の施行について" in meta["件名"]
    assert len(body) > 0, "Body should have paragraphs"
    print("✓ K2 metadata complete")


def test_k3_metadata():
    """K3: 基発0526第1号 / 2026-05-26 (longer ~29pp, 記 section)"""
    meta, body = parse("data/kihatsu_samples/K3.pdf")
    
    assert meta["種別"] == "基発"
    assert meta["番号"] == "基発0526第1号"
    assert meta["日付"] == "令和８年５月26日"
    assert meta["発出元"] == "厚生労働省労働基準局長"
    assert "労働安全衛生法及び作業環境測定法の一部を改正する法律の一部の施行に伴う" in meta["件名"]
    assert "個人事業者等の安全衛生対策の推進に係る規定関係" in meta["件名"]
    assert len(body) > 0, "Body should have paragraphs"
    # K3 is ~29 pages, should have substantial body content
    assert len(body) > 500, "K3 should have many paragraphs"
    print("✓ K3 metadata complete")


def test_all_samples_have_body_text():
    """All samples should have non-empty body paragraphs"""
    for sample in ["K1", "K2", "K3"]:
        meta, body = parse(f"data/kihatsu_samples/{sample}.pdf")
        assert len(body) > 0, f"{sample} should have body paragraphs"
        # Body should contain some actual content
        total_text = "".join(body)
        assert len(total_text) > 100, f"{sample} body should be substantial"
    print("✓ All samples have body text")


def test_spaced_number_normalization():
    """Test that spaced 基発 numbers are properly normalized"""
    samples_and_expected = [
        ("K1", "基発0731第7号"),    # "基発 0731 第 7 号"
        ("K2", "基発0919第1号"),    # "基 発 0919第 １ 号" (with full-width numbers)
        ("K3", "基発0526第1号"),    # "基 発 0526第 １ 号"
    ]
    
    for sample, expected in samples_and_expected:
        meta, _ = parse(f"data/kihatsu_samples/{sample}.pdf")
        assert meta["番号"] == expected, f"{sample} number should be normalized to {expected}, got {meta['番号']}"
    
    print("✓ Spaced numbers normalized correctly")


if __name__ == "__main__":
    test_k1_metadata()
    test_k2_metadata()
    test_k3_metadata()
    test_all_samples_have_body_text()
    test_spaced_number_normalization()
    print("\nAll tests passed! ✓")
