#!/usr/bin/env python3
"""通知テキスト（Lawtext風プレーンテキスト）の共通ライブラリ

対応範囲：階層的な番号体系を持つ通知の本体（介護保険・診療報酬等の局長通知・留意事項）
範囲外：Q&A/疑義解釈、事務連絡（異なる構造のため別パーサーが必要）

■ 通知テキスト（.tsuchi.txt）
    ---                      ← YAMLフロントマター（通知番号・版・改正履歴）
    ...
    ---
    前文
      　「指定居宅サービス…」…期されたい。      ← ラベルなし段落は「　」で始める
    第１　届出項目について                       ← 「ラベル＋全角空白＋本文」
      　居宅サービス事業所、…
      ①　事前に都道府県知事…                    ← 2半角空白 = 1階層（Lawtextと同じ）
        ・　介護支援専門員が…

■ 新旧対照表テキスト（.shinkyu.txt）＝ 通知テキストの各行の先頭に1文字の印を付けたもの
    ' '  文脈（見出し、または「①～⑪　（略）」）   … 適用時に原本と一致するか検証
    '-'  現行（削る / 改正前の文）
    '+'  改正後（新設 / 改正後の文）
    ラベル「⑬←⑫」 = 現行⑫を⑬に繰り下げ（対照表の「⑬（略）｜⑫（略）」）
"""
import re, unicodedata, difflib, html
from dataclasses import dataclass, field

MARU = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"
PAREN = "⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿⒀⒁⒂⒃⒄⒅⒆⒇"
ZEN = str.maketrans("０１２３４５６７８９", "0123456789")
HAN2ZEN = str.maketrans("0123456789", "０１２３４５６７８９")
IROHA = "アイウエオカキクケコサシスセソタチツテト"

LABEL_RE = re.compile(
    r"^(?P<label>"
    r"(?:前文|記|（様式）)(?=[\s　]|$)"
    r"|第[０-９0-9]+(?:の[０-９0-9]+)?(?:～第?[０-９0-9]+)?(?=[\s　←]|$)"
    r"|[０-９0-9]{1,2}(?:[～・][０-９0-9]{1,2})?(?=[\s　←]|$)"
    rf"|[{MARU}](?:[～・][{MARU}])?"
    rf"|[{PAREN}](?:[～・][{PAREN}])?"
    r"|・"
    rf"|[{IROHA}](?:[～・][{IROHA}])?(?=[\s　←]|$)"
    r"|別紙[０-９0-9]+(?:[―－-][０-９0-9]+)*(?=[\s　]|$)"
    r")(?:←(?P<old>[^\s　]+))?")


def kind_num(label):
    """ラベル → (種類, 数値)"""
    if label in ("前文", "記", "（様式）"):
        return ("special", 0)
    if label.startswith("別紙"):
        return ("beshi", 0)
    if label.startswith("第"):
        return ("dai", int(re.match(r"第([0-9]+)", label.translate(ZEN)).group(1)))
    c = label[0]
    if c in MARU:
        return ("maru", MARU.index(c) + 1)
    if c in PAREN:
        return ("paren", PAREN.index(c) + 1)
    if c == "・":
        return ("dot", 0)
    if c in IROHA:
        return ("kana", IROHA.index(c) + 1)
    return ("num", int(label.translate(ZEN)))


def make_label(kind, n, like=None):
    if kind == "maru":
        return MARU[n - 1]
    if kind == "paren":
        return PAREN[n - 1]
    if kind == "kana":
        return IROHA[n - 1]
    if kind == "dai":
        return "第" + str(n).translate(HAN2ZEN)
    if kind == "num":
        # 原本の書き方に合わせる（1桁は全角、2桁は半角 … 本通知の慣行）
        return str(n).translate(HAN2ZEN) if n < 10 else str(n)
    raise ValueError(kind)


def expand_range(label):
    """「①～⑪」「１・２」→ ['①',…,'⑪'] / ['１','２']"""
    m = re.match(r"^(.+?)([～・])(.+)$", label)
    if not m or label.startswith("第") and "～" not in label:
        return [label]
    a, sep, b = m.groups()
    if a.startswith("第") and not b.startswith("第"):
        b = "第" + b
    ka, na = kind_num(a)
    kb, nb = kind_num(b)
    if sep == "・":
        return [a, b]
    return [make_label(ka, i) for i in range(na, nb + 1)]


def norm(s):
    """比較用の正規化：空白の除去（ASCII英数字どうしの間は残す）、NFKC は掛けない"""
    s = re.sub(r"(?<=[A-Za-z0-9])[ 　]+(?=[A-Za-z0-9])", "\x00", s)
    s = re.sub(r"[ 　\t]+", "", s)
    return s.replace("\x00", " ")


@dataclass
class Node:
    label: str
    text: str = ""                      # 見出し or 本文1段落目
    paras: list = field(default_factory=list)   # 追加段落（ラベルなし、子より前）
    children: list = field(default_factory=list)
    tail: list = field(default_factory=list)    # 子の後に続く段落（列挙の後の地の文）
    old_label: str = None               # 繰下げ元（対照表テキストのみ）

    @property
    def kind(self):
        return kind_num(self.label)[0]

    @property
    def num(self):
        return kind_num(self.label)[1]

    def body(self):
        return "\n".join([self.text] + self.paras + self.tail)


# ------------------------------------------------------------------ 読み書き
def parse_lines(lines, marks=False):
    """通知テキスト（または対照表テキスト）の行 → Node の木。
    marks=True のときは各行頭の印（' ','-','+'）を node.mark に入れる"""
    root = Node("ROOT")
    stack = [(-1, root)]
    last = root
    for raw in lines:
        if not raw.strip():
            continue
        mark = " "
        if marks:
            mark, raw = raw[0], raw[1:]
        ind = len(raw) - len(raw.lstrip(" "))
        depth = ind // 2
        s = raw.strip(" ")
        if s.startswith("　"):          # ラベルなし段落 → 直前の同深度-1のノードへ
            while stack[-1][0] >= depth:
                stack.pop()
            owner = stack[-1][1]
            (owner.tail if owner.children else owner.paras).append(s[1:])
            continue
        m = LABEL_RE.match(s)
        if not m:
            raise ValueError(f"ラベルを解釈できない行: {raw!r}")
        n = Node(m.group("label"), s[m.end():].lstrip(" 　"), old_label=m.group("old"))
        if marks:
            n.mark = mark
        while stack[-1][0] >= depth:
            stack.pop()
        stack[-1][1].children.append(n)
        stack.append((depth, n))
    return root


def dump(nodes, depth=0, out=None):
    out = [] if out is None else out
    for n in nodes:
        pad = "  " * depth
        out.append(f"{pad}{n.label}　{n.text}".rstrip("　"))
        for p in n.paras:
            out.append(f"{pad}  　{p}")
        dump(n.children, depth + 1, out)
        for p in n.tail:
            out.append(f"{pad}  　{p}")
    return out


def split_front(text):
    import yaml
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        return yaml.safe_load(fm), body.strip("\n").splitlines()
    return {}, text.splitlines()


def load(path, marks=False):
    meta, lines = split_front(open(path, encoding="utf-8").read())
    return meta, parse_lines(lines, marks=marks)


def save(path, meta, root):
    import yaml
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
    open(path, "w", encoding="utf-8").write("---\n" + fm + "---\n" + "\n".join(dump(root.children)) + "\n")
