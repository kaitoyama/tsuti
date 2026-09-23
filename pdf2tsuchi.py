#!/usr/bin/env python3
"""通知PDF（1段組）→ 通知テキスト。初回の取り込み専用（結果は人が確認する前提）

  python pdf2tsuchi.py 001227974.pdf -o R6.tsuchi.txt

判定の手がかり（pdfplumber の行の x 座標）：
  - ラベル（第１／２／①／⑴／・）で始まり、番号が「前の兄弟＋1」か「1」の行 → 新ノード
  - ラベル位置より約1字下がった行 → 同じ段落の続き
  - 約2字下がった行 → 字下げされた新段落
"""
import argparse, re
import pdfplumber
from tsuchi import Node, LABEL_RE, kind_num, norm, save

CH = 12.0  # 1字の幅（pt）
WARN = []


def lines_of(pdf):
    for pno, page in enumerate(pdf.pages, 1):
        for l in page.extract_text_lines():
            t = l["text"].strip()
            if re.fullmatch(r"[-－ ]*[0-9０-９]+[-－ ]*", t) and l["top"] > page.height * 0.85:
                continue  # ページ番号
            yield pno, l["x0"], t


def accept(parent, label):
    """番号が連続しているときだけラベルとして認める（本文中の「12 年」等の誤認を防ぐ）"""
    if re.search("[～・]", label):
        return False
    kind, num = kind_num(label)
    if kind in ("special", "dot"):
        return True
    if kind == "beshi":
        return False
    same = [c for c in parent.children if c.kind == kind]
    if same and num == same[-1].num and kind in ("maru", "paren", "kana"):
        return "dup"                 # 原本側の番号重複（誤植）→ ノードとして残し、警告する
    return (num == same[-1].num + 1) if same else num == 1


def parse(pdf_path):
    pdf = pdfplumber.open(pdf_path)
    root = Node("ROOT")
    stack = [(-1e9, root)]          # (ラベルのx, node)
    started = False
    pre = Node("前文")
    cur_para = None                  # (node, 'text'|'paras'|'tail', index)

    def append(node, where, idx, s):
        if where == "text":
            node.text += s
        else:
            getattr(node, where)[idx] += s

    for pno, x, t in lines_of(pdf):
        if not started:
            # 鑑（あて先・発信者・件名）は meta へ。件名の次の行から前文
            if t == "記":
                started = True
                root.children.append(pre)
                continue
            if pno == 1 and not pre.paras and not t.startswith("「"):
                continue
            if t.startswith("「") and x > 100 and not pre.paras:
                pre.paras.append(t); continue
            if pre.paras:
                if x > 100 and pre.paras[-1].endswith("。"):
                    pre.paras.append(t)
                else:
                    pre.paras[-1] += t
            continue

        m = LABEL_RE.match(t)
        if m:
            label = m.group("label")
            # 親 = ラベルより左にラベルがある最も深いノード
            while len(stack) > 1 and stack[-1][0] >= x - 3:
                stack.pop()
            parent = stack[-1][1]
            ok = accept(parent, label)
            if ok == "dup":
                WARN.append(f"p.{pno}: 番号「{label}」が重複している（原本の誤植と思われる）: {t[:30]}")
            if ok:
                n = Node(label, t[m.end():].lstrip(" 　"))
                parent.children.append(n)
                stack.append((x, n))
                cur_para = (n, "text", 0)
                continue
            if not re.search("[～・]", label):
                sib = [c for c in parent.children if c.kind == kind_num(label)[0]]
                if sib and kind_num(label)[0] in ("maru", "paren", "kana"):
                    WARN.append(f"p.{pno}: 番号「{label}」が並びに合わない（直前は「{sib[-1].label}」）→ 本文として扱った: {t[:30]}")
        # 本文の行：所有ノード = ラベル位置が x より左で最も深いもの
        k = len(stack) - 1
        while k > 1 and stack[k][0] > x - 6:
            k -= 1
        lx, owner = stack[k]
        indent = (x - lx) / CH
        if indent >= 1.6 or cur_para is None or cur_para[0] is not owner:
            where = "tail" if owner.children else "paras"
            getattr(owner, where).append(t)
            cur_para = (owner, where, len(getattr(owner, where)) - 1)
        else:
            append(*cur_para, t)

    # 空白の正規化
    def walk(n):
        n.text = norm(n.text)
        n.paras = [norm(p) for p in n.paras]
        n.tail = [norm(p) for p in n.tail]
        for c in n.children:
            walk(c)
    walk(root)
    return root


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("-o", required=True)
    ap.add_argument("--number", required=True, help="通知番号（例: 老発0315第1号）")
    ap.add_argument("--date", required=True, help="日付（例: 2024-03-15）")
    ap.add_argument("--version", required=True, help="版の名前（例: R6.3.15）")
    ap.add_argument("--title", default="")
    ap.add_argument("--issuer", default="")
    ap.add_argument("--to", default="")
    x = ap.parse_args()
    root = parse(x.pdf)
    meta = {
        "title": x.title,
        "issuer": x.issuer,
        "to": x.to,
        "version": x.version,
        "history": [{"kind": "制定", "number": x.number, "date": x.date}],
    }
    if WARN:
        meta["notes"] = WARN
    save(x.o, meta, root)
    for w in WARN:
        print("注意:", w)
