#!/usr/bin/env python3
"""番号参照の追従テスト"""
import os, subprocess, sys

if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "R6.tsuchi.txt")):
    sys.exit("data/ がありません。先に scripts/fetch_data.sh を実行してください（厚生労働省のPDFを取得して変換します）")
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(H, "tests", "out"); os.makedirs(T, exist_ok=True)
sys.path.insert(0, H)
from tsuchi import load

def run(patch_body, name):
    p = f"{T}/{name}.shinkyu.txt"
    open(p, "w", encoding="utf-8").write(
        "---\namendment: {kind: 一部改正, number: テスト, date: '2026-09-23'}\nbase_version: R6.3.15\nnew_version: T\n---\n" + patch_body)
    r = subprocess.run([sys.executable, f"{H}/shinkyu.py", "apply", f"{H}/data/R6.tsuchi.txt", p, "-o", f"{T}/{name}.tsuchi.txt"],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr

ok = True
def check(label, cond):
    global ok
    ok &= bool(cond)
    print(("OK  " if cond else "NG  ") + label)

# 1) 範囲参照「②から⑥まで」の途中に新設 → 端点は追従、範囲の確認を促す
code, out = run(""" 前文　（略）
 第１～第４　（略）
 第５　体制状況一覧表の記載要領について
   １～８　（略）
   ９　短期入所生活介護
     ①～③　（略）
+    ④　（テスト用の新設）
     ⑤～㉖←④～㉕　（略）
   10～51　（略）
 第６　（略）
""", "range")
_, d = load(f"{T}/range.tsuchi.txt")
t = [n for n in d.children if n.label == "第５"][0].children[8].children[-1].text
check("9㉕→㉖ の中の「②から⑥まで」が「②から⑦まで」になる", "②から⑦まで" in t)
check("同じ文の「⑨、⑩、⑫」も「⑩、⑪、⑬」になる", "⑩、⑪、⑬" in t)
check("範囲の途中に新設があることを知らせる", "範囲「②から⑥まで」の途中に新設 ④" in out)
check("他サービスからの「９㉑」参照（28⑮）が「９㉒」になる", "９㉑ → ９㉒" in out)

# 2) 参照先を削る → 手で直すよう知らせる
code, out = run(""" 前文　（略）
 第１～第４　（略）
 第５　体制状況一覧表の記載要領について
   １　（略）
   ２　訪問介護
     ①～⑥　（略）
-    ⑦　「特別地域加算」については、事業所の所在する地域が厚生労働大臣が定める地域（平成24年厚生労働省告示第120号）及び厚生労働大臣が定める地域第六号の規定に基づき厚生労働大臣が定める地域（令和３年厚生労働省告示第74号）に該当する場合に、「あり」と記載させること。
     ⑦～⑩←⑧～⑪　（略）
   ３～51　（略）
 第６　（略）
""", "delete")
check("削った２⑦を参照している箇所を知らせる", out.count("参照先が削られた") >= 10)
check("繰上げに追従（２⑧→２⑦）", "２⑧ → ２⑦" in out)

# 3) 改正で書いた本文の参照先が存在しない → 反映しない
code, out = run(""" 前文　（略）
 第１～第４　（略）
 第５　体制状況一覧表の記載要領について
   １　（略）
   ２　訪問介護
     ①～⑪　（略）
+    ⑫　「テスト」については、４⑳を準用すること。
   ３～51　（略）
 第６　（略）
""", "badref")
check("新しく書いた本文の「４⑳」（存在しない）を誤りとして止める", code != 0 and "４⑳" in out)
sys.exit(0 if ok else 1)
