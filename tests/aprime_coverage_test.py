#!/usr/bin/env python3
"""Priority A' (診療報酬階層つき通知本体) の番号パターンカバレッジテスト

このテストは、診療報酬通知が使用する階層的な番号パターンが
既存のコアライブラリ（tsuchi.py）で正しく処理できることを検証します。

検証項目：
1. 診療報酬通知のフィクスチャが正常にパース可能
2. 階層構造（第N → 数字 → ⑴ → ① → ア → ・）が正しく認識される
3. ラベルの種類判定（kind_num）が正常に機能する
4. 参照パターン（「１⑵②を準用」など）が解決可能（refs.py との連携）
5. 参照の実際の追従（refs.py の follow 機能）が診療報酬パターンで動作する

注：これらは合成フィクスチャによる検証であり、実際のPDF（保医発通知など）での
ラウンドトリップテストは別途必要です。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tsuchi import load, dump, kind_num, expand_range, Node, make_label
import refs
import copy

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
    
    # ア（kana）、・（dot）の検証は第２で行う
    dai2 = root.children[2]  # 第２
    sec1_dai2 = dai2.children[0]  # １
    item2 = sec1_dai2.children[1]  # ②
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
    
    # 丸括弧数字 ⑴⑵（第１の下）
    dai1 = root.children[1]
    sec1 = dai1.children[0]
    assert sec1.children[0].label == "⑴"
    assert sec1.children[1].label == "⑵"
    
    # 丸数字 ①②③④⑤（第２の下）
    sec1_dai2 = dai2.children[0]
    assert sec1_dai2.children[0].label == "①"
    assert sec1_dai2.children[4].label == "⑤"
    
    print("✓ 診療報酬ラベルパターンの処理成功")

def test_reference_patterns():
    """参照パターン（「１②を準用」など）の解析準備"""
    # 実際の参照解決は refs.py で行うが、パターンが存在することを確認
    meta, root = load(FIXTURE)
    
    # 「１②を準用」パターンの検出（第２/２/②）
    dai2 = root.children[2]
    sec2 = dai2.children[1]  # ２
    item2 = sec2.children[1]  # ②
    assert "１②を準用" in item2.text
    
    # 「１④を準用」パターンの検出（第２/２/④）
    item4 = sec2.children[3]  # ④
    assert "１④を準用" in item4.text
    
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

def test_reference_follow_through():
    """refs.py による実際の参照追従（繰下げ時の「準用」参照の自動更新）
    
    このテストは、合成フィクスチャで参照追従機能の動作を検証します。
    実際の診療報酬PDFでの検証は別途必要です。
    """
    meta, root = load(FIXTURE)
    
    # オリジナルをディープコピー
    old_root = copy.deepcopy(root)
    refs.mark_uids(old_root)
    
    # 参照の初期スナップショット
    snap = refs.snapshot(old_root)
    
    # 改正をシミュレート：第２/１ の①の前に新しい項目を挿入 → 後続を繰下げ
    new_root = copy.deepcopy(old_root)
    dai2 = new_root.children[2]  # 第２
    sec1 = dai2.children[0]      # １
    
    # ①の前に新設
    new_item = Node("①", "新設：入院患者数の算定方法については別途定める。")
    new_item.authored = True  # 改正で書かれた項目（参照は追従しない）
    sec1.children.insert(0, new_item)
    
    # 後続を繰下げ（元の①が②、元の②が③、...）
    for i, child in enumerate(sec1.children[1:], start=2):
        if child.kind == "maru":
            child.label = make_label("maru", i)
    
    # 参照の追従を実行
    changes, warns = refs.follow(old_root, new_root, snap)
    
    # 検証：第２/２/② に「１②を準用」という参照があり、
    # 元の②が③に繰り下がったので「１③を準用」に更新されるはず
    dai2_new = new_root.children[2]
    sec2_new = dai2_new.children[1]  # ２
    item2_new = sec2_new.children[1]  # ②
    
    # 参照が更新されていることを確認
    assert "１③を準用" in item2_new.text, f"参照が更新されていない: {item2_new.text}"
    assert "１②を準用" not in item2_new.text, f"古い参照が残っている: {item2_new.text}"
    
    # 変更が記録されていることを確認
    ref_changes = [c for c in changes if "１②" in c[1]]
    assert len(ref_changes) > 0, f"参照の変更が記録されていない。changes={changes}"
    
    # 第２/２/④ にも「１④を準用」があり、元の④が⑤に繰り下がったので「１⑤を準用」になる
    item4_new = sec2_new.children[3]  # ④
    assert "１⑤を準用" in item4_new.text, f"④の参照が更新されていない: {item4_new.text}"
    
    print(f"✓ 参照追従テスト成功: {len(changes)} 件の参照を更新")
    print(f"  - 例: '１②' → '１③'、'１④' → '１⑤'（第２/１の①の手前に新設したため）")
    if warns:
        print(f"  - 警告: {len(warns)} 件")

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
    test_reference_follow_through()
    
    print("\n" + "=" * 60)
    print("合成フィクスチャによる検証: 成功")
    print("=" * 60)
    print("\n検証結果:")
    print("- ✅ 番号パターン（第N → 数字 → ⑴ → ① → ア → ・）認識")
    print("- ✅ 参照パターン（「１⑴②を準用」など）の解析・解決")
    print("- ✅ 繰下げ時の参照自動追従（refs.py）")
    print("\n⚠️  重要:")
    print("この検証は合成フィクスチャに基づくものです。")
    print("実際のPDF（保医発0304第1号など）でのラウンドトリップテストが")
    print("成功するまで、A'対応は暫定的（provisional）です。")
    print("\n次のステップ（実データ検証）:")
    print("1. 実際の診療報酬PDF（保医発0304第1号など）を取得")
    print("2. scripts/fetch_data.sh のコメント部分を有効化して変換")
    print("3. pdf2tsuchi.py → shinkyu.py apply → 往復一致を確認")
    print("4. 実データでのエッジケースを検出・対応")
