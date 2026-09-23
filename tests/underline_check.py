#!/usr/bin/env python3
"""自動傍線と、原典PDFの傍線の文字単位の一致度"""
import json, os, re, sys

if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "R6.tsuchi.txt")):
    sys.exit("data/ がありません。先に scripts/fetch_data.sh を実行してください（厚生労働省のPDFを取得して変換します）")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tsuchi import norm
from shinkyu import underline_pair
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
real = json.load(open(f"{D}/R8_underlines.json"))

def mask_from_html(h):
    out, on = [], False
    for tok in re.split(r'(<span class="u">|</span>)', h):
        if tok == '<span class="u">': on = True
        elif tok == "</span>": on = False
        else:
            import html; t = html.unescape(tok); out += [on] * len(t)
    return out

def mask_from_segments(text, segs):
    m, pos = [False] * len(text), 0
    for s in segs:
        s = norm(s); i = text.find(s, pos)
        if i >= 0:
            for j in range(i, i + len(s)): m[j] = True
            pos = i + len(s)
    return m

# 改正後・現行の対になった本文（行の縦位置で対応）
by = {}
for e in real:
    by.setdefault(tuple(e["y"]), {})[e["side"]] = e
from pdf2shinkyu import parse, pair
L, R, _ = parse(f"{D}/001676185_R8改正.pdf", list(range(2, 9)))
tp = fp = fn = 0
rows = []
for l, r in pair(L.entries, R.entries):
    if not (l and r and l.label and r.label) or l.text.strip() == "（略）" or l.label == "前文":
        continue
    nt, ot = norm(l.text + "".join(l.paras)), norm(r.text + "".join(r.paras))
    if nt == ot:
        continue
    nh, oh = underline_pair(ot, nt)
    for side, text, h, e in (("new", nt, nh, by.get(tuple(l.y), {}).get("new")), ("old", ot, oh, by.get(tuple(r.y), {}).get("old"))):
        if not e: continue
        a = mask_from_html(h)
        b = mask_from_segments(text, [s for seg in e["segments"] for s in seg])
        t = sum(x and y for x, y in zip(a, b)); f1 = sum(x and not y for x, y in zip(a, b)); f2 = sum(y and not x for x, y in zip(a, b))
        tp += t; fp += f1; fn += f2
        rows.append((l.label, side, t, f1, f2))
print(f"比較した本文 {len(rows)} 件")
print(f"傍線の文字単位一致  適合率 {tp/(tp+fp):.1%}  再現率 {tp/(tp+fn):.1%}")
worst = sorted(rows, key=lambda r: -(r[3] + r[4]))[:5]
for w in worst: print("  差の大きい行:", w)
