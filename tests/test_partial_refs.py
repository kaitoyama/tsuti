#!/usr/bin/env python3
"""部分改正モードでの参照追従テスト

サービスＡで②の前に新設→繰下げが起きたとき、
対照表に出てこないサービスＢ・Ｃの参照も追従することを確認する。
"""
import subprocess, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tsuchi import load

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

SHINKYU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shinkyu.py")

print("=== 部分改正モードで参照追従 ===")
p = subprocess.run([sys.executable, SHINKYU, "apply",
                    f"{FIXTURES}/partial_with_refs_base.tsuchi.txt",
                    f"{FIXTURES}/partial_with_refs_amendment.shinkyu.txt",
                    "-o", f"{OUT}/partial_refs_result.tsuchi.txt",
                    "--partial",
                    "--patch-out", f"{OUT}/partial_refs_完成版.shinkyu.txt"],
                   capture_output=True, text=True)
if p.returncode != 0:
    print("✗ 失敗した")
    print(p.stdout)
    sys.exit(1)
print("✓ 成功した")
print(p.stdout)

# 参照が追従されたかを確認
meta, root = load(f"{OUT}/partial_refs_result.tsuchi.txt")

dai1 = next((n for n in root.children if n.label == "第１"), None)
s1 = next((n for n in dai1.children if n.label == "１"), None)

# ②が新設、③が繰下げ、④が繰下げ
items = {n.label: n for n in s1.children}
if "②" not in items or "新設項目" not in items["②"].text:
    print("✗ ②が新設されていない")
    sys.exit(1)
if "③" not in items or "特例加算" not in items["③"].text:
    print("✗ ③が正しく繰り下がっていない")
    sys.exit(1)
if "④" not in items or "減算規定" not in items["④"].text:
    print("✗ ④が正しく繰り下がっていない")
    sys.exit(1)
print("✓ サービス種別Ａの繰下げが正しい")

# サービスＢの参照が③に追従したか（元は②）
s2 = next((n for n in dai1.children if n.label == "２"), None)
b1 = next((n for n in s2.children if n.label == "①"), None)
if "１③" not in b1.text:  # １②→１③に追従
    print(f"✗ サービスＢの参照が追従していない: {b1.text}")
    sys.exit(1)
print("✓ サービスＢの参照が追従（１②→１③）")

# サービスＣの参照が④に追従したか（元は③）
s3 = next((n for n in dai1.children if n.label == "３"), None)
c1 = next((n for n in s3.children if n.label == "①"), None)
if "１④" not in c1.text:  # １③→１④に追従
    print(f"✗ サービスＣの参照が追従していない: {c1.text}")
    sys.exit(1)
print("✓ サービスＣの参照が追従（１③→１④）")

# 第２が残っているか
dai2 = next((n for n in root.children if n.label == "第２"), None)
if not dai2 or "その他の規定" not in dai2.text:
    print("✗ 第２が残っていない")
    sys.exit(1)
print("✓ 第２が残っている")

print("\n=== すべてのテストに合格 ===")
