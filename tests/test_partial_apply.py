#!/usr/bin/env python3
"""部分改正モードのテスト

対照表に出てこない項目（第１、第２の３、第３）が原本のまま残ることを確認する。
"""
import subprocess, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tsuchi import load, dump

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

SHINKYU = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shinkyu.py")

# 1) --partial なしでは失敗することを確認
print("=== テスト1: --partial なしでは失敗する ===")
p = subprocess.run([sys.executable, SHINKYU, "apply",
                    f"{FIXTURES}/partial_base.tsuchi.txt",
                    f"{FIXTURES}/partial_amendment.shinkyu.txt",
                    "-o", f"{OUT}/partial_result_fail.tsuchi.txt"],
                   capture_output=True, text=True)
if p.returncode != 0:
    print("✓ 期待通り失敗した")
    print("エラーメッセージ:")
    print(p.stdout)
else:
    print("✗ 失敗すべきなのに成功した")
    sys.exit(1)

# 2) --partial ありで成功することを確認
print("\n=== テスト2: --partial ありで成功する ===")
p = subprocess.run([sys.executable, SHINKYU, "apply",
                    f"{FIXTURES}/partial_base.tsuchi.txt",
                    f"{FIXTURES}/partial_amendment.shinkyu.txt",
                    "-o", f"{OUT}/partial_result.tsuchi.txt",
                    "--partial"],
                   capture_output=True, text=True)
if p.returncode != 0:
    print("✗ 失敗した")
    print(p.stdout)
    sys.exit(1)
print("✓ 成功した")
print(p.stdout)

# 3) 結果の検証
print("\n=== テスト3: 結果の検証 ===")
meta, root = load(f"{OUT}/partial_result.tsuchi.txt")

# 第１が残っているか
dai1 = next((n for n in root.children if n.label == "第１"), None)
if not dai1:
    print("✗ 第１が消えている")
    sys.exit(1)
print("✓ 第１が残っている")

# 第２の１の①が改正されているか
dai2 = next((n for n in root.children if n.label == "第２"), None)
s1 = next((n for n in dai2.children if n.label == "１"), None)
item1 = next((n for n in s1.children if n.label == "①"), None)
if "基準第１号" not in item1.text:
    print(f"✗ 第２の１の①が改正されていない: {item1.text}")
    sys.exit(1)
print("✓ 第２の１の①が改正されている")

# 第２の１の③が新設されているか
item3 = next((n for n in s1.children if n.label == "③"), None)
if not item3 or "加算Ｃ" not in item3.text:
    print("✗ 第２の１の③が新設されていない")
    sys.exit(1)
print("✓ 第２の１の③が新設されている")

# 第２の２の①が改正されているか
s2 = next((n for n in dai2.children if n.label == "２"), None)
item1_s2 = next((n for n in s2.children if n.label == "①"), None)
if "参照すること" not in item1_s2.text:
    print(f"✗ 第２の２の①が改正されていない: {item1_s2.text}")
    sys.exit(1)
print("✓ 第２の２の①が改正されている")

# 第２の３が残っているか
s3 = next((n for n in dai2.children if n.label == "３"), None)
if not s3 or "独自の基準" not in s3.children[0].text:
    print("✗ 第２の３が残っていないか変更されている")
    sys.exit(1)
print("✓ 第２の３が残っている")

# 第３が残っているか
dai3 = next((n for n in root.children if n.label == "第３"), None)
if not dai3 or "経過措置" not in dai3.text:
    print("✗ 第３が残っていない")
    sys.exit(1)
print("✓ 第３が残っている")

# バージョンが更新されているか
if meta.get("version") != "R2":
    print(f"✗ バージョンが更新されていない: {meta.get('version')}")
    sys.exit(1)
print("✓ バージョンが更新されている")

print("\n=== すべてのテストに合格 ===")
