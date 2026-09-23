#!/usr/bin/env python3
"""Priority A' (診療報酬階層つき通知本体) の番号パターンカバレッジテスト

このテストは、診療報酬通知が使用する階層的な番号パターンが
既存のコアライブラリ（tsuchi.py）で正しく処理できることを検証します。

検証項目：
1. 診療報酬通知のフィクスチャが正常にパース可能
2. 階層構造（第N → 数字 → ⑴ → ① → ア → ・）が正しく認識される
3. ラベルの種類判定（kind_num）が正常に機能する
4. 参照パターン（「１⑵②を準用」など）が解決可能（refs.py との連携）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tsuchi import load, dump, kind_num, expand_range

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "shinryou_sample.tsuchi.txt")

def test_parse_aprime_fixture():
    """診療報酬フィクスチャが正常にパース可能"""
    meta, root = load(FIXTURE)
    assert meta["title"].startswith("基本診療料")
    assert len(root.children) == 4  # 前文、第１、第２、第３
    print("✓ 診療報酬フィクスチャのパース成功")

def test_hierarchical_structure():
    """階層構造が正しく認識される"""
    meta, root = load(FIXTURE)
    dai1 = root.children[1]  # 第１
    assert dai1.label == "第１"
    assert dai1.kind == "dai"
    assert dai1.num == 1
    
    sec1 = dai1.children[0]  # １
    assert sec1.label == "１"
    assert sec1.kind == "num"
    assert sec1.num == 1
    
    subsec1 = sec1.children[0]  # ⑴
    assert subsec1.label == "⑴"
    assert subsec1.kind == "paren"
    assert subsec1.num == 1
    
    item1 = subsec1.children[0]  # ①
    assert item1.label == "①"
    assert item1.kind == "maru"
    assert item1.num == 1
    
    # ア（kana）の検証
    dai2 = root.children[2]  # 第２
    subsec1_2 = dai2.children[0].children[0]  # １ → ⑴
    item2 = subsec1_2.children[1]  # ②
    assert len(item2.children) == 2  # ア、イ
    kana_a = item2.children[0]
    assert kana_a.label == "ア"
    assert kana_a.kind == "kana"
    assert kana_a.num == 1
    
    # ・（dot）の検証
    kana_i = item2.children[1]
    assert len(kana_i.children) == 2  # ・、・
    dot1 = kana_i.children[0]
    assert dot1.label == "・"
    assert dot1.kind == "dot"
    
    print("✓ 階層構造（第N → 数字 → ⑴ → ① → ア → ・）の認識成功")

def test_label_patterns():
    """診療報酬特有のラベルパターンが処理可能"""
    meta, root = load(FIXTURE)
    
    # 「第１」「第２」「第３」
    assert all(c.label.startswith("第") for c in root.children[1:])
    
    # 数字ラベル（1桁は全角、2桁は半角の混在にも対応）
    dai2 = root.children[2]
    assert dai2.children[0].label == "１"
    assert dai2.children[1].label == "２"
    
    # 丸括弧数字 ⑴⑵
    sec1 = dai2.children[0]
    assert sec1.children[0].label == "⑴"
    assert sec1.children[1].label == "⑵"
    
    print("✓ 診療報酬ラベルパターンの処理成功")

def test_reference_patterns():
    """参照パターン（「１⑴②を準用」）の解析準備"""
    # 実際の参照解決は refs.py で行うが、パターンが存在することを確認
    meta, root = load(FIXTURE)
    
    # 「１⑴②を準用」パターンの検出
    dai2 = root.children[2]
    sec2 = dai2.children[1]  # ２
    item1 = sec2.children[0].children[1]  # ⑴ → ②
    assert "１⑴②を準用" in item1.text
    
    # 「１⑵②を準用」パターンの検出
    item2 = sec2.children[1].children[1]  # ⑵ → ②
    assert "１⑵②を準用" in item2.text
    
    print("✓ 参照パターンの存在確認成功")

def test_roundtrip():
    """パース→ダンプ→再パースの往復一致"""
    meta, root = load(FIXTURE)
    dumped = dump(root.children)
    
    # 一時ファイルに書き出して再パース
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsuchi.txt", delete=False) as f:
        import yaml
        f.write("---\n")
        f.write(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False))
        f.write("---\n")
        f.write("\n".join(dumped) + "\n")
        temp_path = f.name
    
    try:
        meta2, root2 = load(temp_path)
        dumped2 = dump(root2.children)
        assert dumped == dumped2
        print("✓ 往復一致テスト成功")
    finally:
        os.unlink(temp_path)

def test_label_coverage():
    """使用されている全ラベル種別の網羅確認"""
    meta, root = load(FIXTURE)
    
    used_kinds = set()
    def collect_kinds(nodes):
        for n in nodes:
            used_kinds.add(n.kind)
            collect_kinds(n.children)
    
    collect_kinds(root.children)
    
    # 診療報酬通知で使用される主要な種別が全てカバーされているか
    expected = {"special", "dai", "num", "paren", "maru", "kana", "dot"}
    assert expected.issubset(used_kinds), f"不足: {expected - used_kinds}"
    
    print(f"✓ 使用種別カバレッジ: {sorted(used_kinds)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Priority A' (診療報酬) 番号パターンカバレッジテスト")
    print("=" * 60)
    
    test_parse_aprime_fixture()
    test_hierarchical_structure()
    test_label_patterns()
    test_reference_patterns()
    test_roundtrip()
    test_label_coverage()
    
    print("\n" + "=" * 60)
    print("全テスト成功: 既存コアは診療報酬通知（A'）をカバーしています")
    print("=" * 60)
    print("\n次のステップ:")
    print("- 実際の診療報酬PDF（例：保医発0304第1号）を scripts/fetch_data.sh で取得")
    print("- pdf2tsuchi.py で変換し、実データでの動作を検証")
    print("- refs.py の参照追従機能が診療報酬の参照パターンでも動作するか確認")
