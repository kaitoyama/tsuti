#!/usr/bin/env python3
"""往復テスト：R6原本を機械的に改変 → diff で対照表テキスト → apply で原本に反映 → 改変版と一字一句一致するか"""
import copy, subprocess, sys, os

if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "R6.tsuchi.txt")):
    sys.exit("data/ がありません。先に scripts/fetch_data.sh を実行してください（厚生労働省のPDFを取得して変換します）")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tsuchi import load, save, Node, dump, make_label, kind_num

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"); os.makedirs(T, exist_ok=True)
meta, root = load(f"{D}/R6.tsuchi.txt")
new = copy.deepcopy(root)
get = lambda nodes, lab: next(n for n in nodes if n.label == lab)
dai5, dai6 = get(new.children, "第５"), get(new.children, "第６")

# 1) 文言の改正
n = get(get(dai5.children, "２").children, "⑪")
n.text = n.text.replace("大臣基準告示第四号イ", "大臣基準告示第４号イ")
# 2) 末尾に新設
kango = get(dai5.children, "４")
kango.children.append(Node("⑬", "「介護職員等処遇改善加算」については、大臣基準告示第10号の２に該当する場合に「あり」と記載させること。"))
# 3) 途中に新設 → 後ろを繰下げ
yobo = get(dai5.children, "22")
yobo.children.insert(5, Node("⑥", "「介護職員等処遇改善加算」については、訪問看護と同様であるため、４⑬を準用すること。"))
for i, c in enumerate(yobo.children[6:], start=7):
    c.label = make_label("maru", i)
# 4) 削る
kyotsu = get(dai5.children, "１")
kyotsu.children = [c for c in kyotsu.children if c.label != "⑦"]
# 5) 見出しごと新設（段落つき）
s3 = get(dai6.children, "⑶")
s3.children.append(Node("４", "介護予防ケアマネジメント", ["「介護職員等処遇改善加算」については、訪問看護と同様であるため、第５の４⑬を準用すること。"]))
# 6) 前文の読点
pre = get(new.children, "前文")
pre.paras[1] = pre.paras[1].replace("なお、「", "なお「", 1)

m2 = dict(meta, version="R6.test",
          history=meta["history"] + [{"kind": "一部改正", "number": "老発テスト第1号", "date": "2026-09-23"}])
save(f"{T}/test_R6x.tsuchi.txt", m2, new)

run = lambda *a: subprocess.run([sys.executable, os.path.join(os.path.dirname(D), "shinkyu.py"), *a], check=True, capture_output=True, text=True).stdout
run("diff", f"{D}/R6.tsuchi.txt", f"{T}/test_R6x.tsuchi.txt", "-o", f"{T}/test.shinkyu.txt")
run("apply", f"{D}/R6.tsuchi.txt", f"{T}/test.shinkyu.txt", "-o", f"{T}/test_R6y.tsuchi.txt")
run("render", f"{T}/test.shinkyu.txt", "-o", f"{T}/test_新旧対照表.html")

_, x = load(f"{T}/test_R6x.tsuchi.txt")
_, y = load(f"{T}/test_R6y.tsuchi.txt")
ok = dump(x.children) == dump(y.children)
print("改変版 == 対照表テキストから復元した版 :", "一致" if ok else "不一致")
# 対照表テキストの再生成が安定か（diff → apply → diff で同じものが出るか）
run("diff", f"{D}/R6.tsuchi.txt", f"{T}/test_R6y.tsuchi.txt", "-o", f"{T}/test2.shinkyu.txt")
a = open(f"{T}/test.shinkyu.txt").read().split("---", 2)[2]
b = open(f"{T}/test2.shinkyu.txt").read().split("---", 2)[2]
print("対照表テキストの再生成                 :", "一致" if a == b else "不一致")
# 改ざん検知：原本を1字変えると適用が止まるか
_, r = load(f"{D}/R6.tsuchi.txt")
t = get(get(get(r.children, "第５").children, "２").children, "⑪")
t.text = t.text.replace("該当", "該挡", 1)
save(f"{T}/test_R6_tampered.tsuchi.txt", meta, r)
p = subprocess.run([sys.executable, os.path.join(os.path.dirname(D), "shinkyu.py"), "apply", f"{T}/test_R6_tampered.tsuchi.txt",
                    f"{T}/test.shinkyu.txt", "-o", "/dev/null"], capture_output=True, text=True)
print("原本を1字改ざんすると適用が止まるか     :", "止まる" if p.returncode else "止まらない")
print(p.stdout.strip().splitlines()[1] if p.stdout else "")
sys.exit(0 if ok and a == b and p.returncode else 1)
