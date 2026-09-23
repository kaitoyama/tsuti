#!/usr/bin/env python3
"""通知内の番号参照（「２⑫を準用」「第五の34⑫」「③から⑩まで、⑫」など）の解析と、繰下げへの追従

考え方（Lawtext の条項参照解析と同じ）：
  1. 改正前の版で、各参照が「どの項目（ノード）を指しているか」を解決しておく
  2. 改正を反映した後、指している項目の新しい番号で参照を書き直す
番号ではなく「指している項目そのもの」を追うので、繰下げ・繰上げ・途中の新設があっても正しく追従する。

参照の書き方（丸数字＝この通知の中の項目。告示などの外部参照は ⑴ ㈠ イ 等で丸数字を使わない）
  ２⑫        … 同じ「第」の中のサービス２の⑫（サービスの一覧を持つ最も近い祖先から探す）
  第五の34⑫  … 第５のサービス34の⑫（漢数字・全角・半角のどれでもよい）
  第二の②    … 第２の直下の②
  ③から⑩まで、⑫、⑬ … 前の参照の続き（接続語でつながっている間は前の参照の「第」「サービス」を引き継ぐ）
  （単独の）③ … 同じサービス内の③（兄弟の項目）
"""
import re
from tsuchi import MARU, kind_num, make_label, HAN2ZEN

KAN = "〇一二三四五六七八九"
REF_RE = re.compile(
    r"(?P<top>第(?P<topn>[一二三四五六七八九十]+|[０-９0-9]+)の)?"
    r"(?P<svc>[０-９0-9]{1,2})?"
    rf"(?P<item>[{MARU}])")
CHAIN_GAP = re.compile(r"^(まで)?(から|、|及び|又は|並びに|・)$")


def kan2int(s):
    if re.fullmatch(r"[０-９0-9]+", s):
        return int(s.translate(str.maketrans("０１２３４５６７８９", "0123456789")))
    n, cur = 0, 0
    for ch in s:
        if ch == "十":
            n += (cur or 1) * 10; cur = 0
        else:
            cur = KAN.index(ch)
    return n + cur


def int2like(n, like):
    """元の書き方（漢数字／全角／半角）に合わせて数字を書く"""
    if re.fullmatch(r"[一二三四五六七八九十]+", like):
        if n <= 10:
            return "十" if n == 10 else KAN[n]
        t, o = divmod(n, 10)
        return ("" if t == 1 else KAN[t]) + "十" + (KAN[o] if o else "")
    if re.fullmatch(r"[０-９]+", like):
        return str(n).translate(HAN2ZEN)
    return str(n)


# ------------------------------------------------------------------ 木の索引
def walk(nodes, anc=()):
    for n in nodes:
        yield n, anc
        yield from walk(n.children, anc + (n,))


def child_by_num(nodes, kind, num):
    for c in nodes:
        k, v = kind_num(c.label)
        if k == kind and v == num:
            return c
    return None


def texts(n):
    return [("text", 0, n.text)] + [("paras", i, p) for i, p in enumerate(n.paras)] + [("tail", i, p) for i, p in enumerate(n.tail)]


# ------------------------------------------------------------------ 参照の抽出と解決
def find_refs(text):
    """テキスト中の参照を、つながり（チェーン）を考慮して列挙"""
    out, prev = [], None
    for m in REF_RE.finditer(text):
        gap = text[prev["end"]:m.start()] if prev else None
        chained = prev is not None and CHAIN_GAP.match(gap or "") is not None
        r = {"start": m.start(), "end": m.end(), "top": m.group("topn"), "svc": m.group("svc"),
             "item": m.group("item"), "range_from": prev if chained and gap.endswith("から") else None,
             "raw": m.group(0)}
        if not r["top"] and not r["svc"] and chained:        # 前の参照の続き → 「第」「サービス」を引き継ぐ
            r["inh_top"], r["inh_svc"], r["inh_sib"] = prev.get("top") or prev.get("inh_top"), \
                prev.get("svc") or prev.get("inh_svc"), prev.get("sib") or prev.get("inh_sib")
        elif not r["top"] and not r["svc"]:
            r["sib"] = True
        out.append(r); prev = r
    return out


def resolve(root_children, anc, r):
    """参照 → 指しているノード（見つからなければ None）"""
    top = r.get("top") or r.get("inh_top")
    svc = r.get("svc") or r.get("inh_svc")
    item = MARU.index(r["item"]) + 1
    if top:
        base = child_by_num(root_children, "dai", kan2int(top))
        if base is None:
            return None
        if svc:
            base = child_by_num(base.children, "num", kan2int(svc))
            if base is None:
                return None
        return child_by_num(base.children, "maru", item)
    if svc:
        # サービスの一覧（数字ラベルの子）を持つ最も近い祖先
        for a in reversed(anc):
            s = child_by_num(a.children, "num", kan2int(svc))
            if s is not None and any(kind_num(c.label)[0] == "num" for c in a.children):
                return child_by_num(s.children, "maru", item)
        return None
    # 兄弟（同じ親の中の項目）
    parent = anc[-1] if anc else None
    return child_by_num(parent.children, "maru", item) if parent else None


def path_of(node, index):
    """ノード → (祖先タプル)"""
    return index.get(id(node))


# ------------------------------------------------------------------ 追従（apply から呼ぶ）
def mark_uids(root):
    for i, (n, _) in enumerate(walk(root.children)):
        n.uid = i


def snapshot(old_root):
    """改正前の版で、全ての参照を解決しておく： {(uid, where, idx): [(ref, target_uid), …]}"""
    snap = {}
    for n, anc in walk(old_root.children):
        for where, idx, t in texts(n):
            res = []
            for r in find_refs(t):
                tgt = resolve(old_root.children, anc, r)
                res.append((r, getattr(tgt, "uid", None)))
            if res:
                snap[(n.uid, where, idx)] = res
    return snap


def follow(old_root, new_root, snap):
    """改正後の版で、改正前から引き継いだ本文の参照を新しい番号に書き直す。
    返り値: (変更一覧, 注意一覧)"""
    loc = {}                          # uid → (node, 祖先)
    for n, anc in walk(new_root.children):
        if hasattr(n, "uid"):
            loc.setdefault(n.uid, (n, anc))
    changes, warns = [], []
    for n, anc in walk(new_root.children):
        if not hasattr(n, "uid") or getattr(n, "authored", False):
            continue                  # 改正で書かれた本文は、すでに改正後の番号で書かれている
        where_path = "/" + "/".join(a.label for a in anc + (n,))
        for where, idx, t in texts(n):
            refs = snap.get((n.uid, where, idx))
            if not refs:
                continue
            new_t, shift = t, 0
            for r, tuid in refs:
                if tuid is None:
                    warns.append(f"{where_path}: 参照「{r['raw']}」の参照先が改正前の版で見つからない")
                    continue
                if tuid not in loc:
                    warns.append(f"{where_path}: 参照「{r['raw']}」の参照先が削られた（手で直す必要あり）")
                    continue
                tgt, tanc = loc[tuid]
                rep = render_ref(r, tgt, tanc)
                if rep != r["raw"]:
                    s, e = r["start"] + shift, r["end"] + shift
                    new_t = new_t[:s] + rep + new_t[e:]
                    shift += len(rep) - len(r["raw"])
                    changes.append((where_path, r["raw"], rep))
                if r["range_from"] is not None:
                    check_range(r, refs, loc, where_path, warns)
            if new_t != t:
                if where == "text":
                    n.text = new_t
                else:
                    getattr(n, where)[idx] = new_t
                n.refs_updated = True
    return changes, warns


def render_ref(r, tgt, tanc):
    """参照を、指している項目の新しい番号で書き直す（書式は元の書き方に合わせる）"""
    s = ""
    if r["top"]:
        dai = next(a for a in tanc if kind_num(a.label)[0] == "dai")
        s += f"第{int2like(kind_num(dai.label)[1], r['top'])}の"
    if r["svc"]:
        svc = tanc[-1]
        s += int2like(kind_num(svc.label)[1], r["svc"])
    return s + tgt.label


def check_range(r, refs, loc, where_path, warns):
    """「③から⑩まで」の途中に新設・削除があれば、範囲の意味が変わるので知らせる"""
    a = next((x for x in refs if x[0] is r["range_from"]), None)
    b = next((x for x in refs if x[0] is r), None)
    if not a or a[1] not in loc or b[1] not in loc:
        return
    (na, anc_a), (nb, anc_b) = loc[a[1]], loc[b[1]]
    if anc_a[-1] is not anc_b[-1]:
        return
    sib = anc_a[-1].children
    ia, ib = sib.index(na), sib.index(nb)
    inside = sib[ia + 1:ib]
    new_inside = [x.label for x in inside if not hasattr(x, "uid")]
    if new_inside:
        warns.append(f"{where_path}: 範囲「{a[0]['raw']}から{b[0]['raw']}まで」の途中に新設 {'・'.join(new_inside)} がある（範囲に含めるか確認）")


def check_refs(root, only=None):
    """全ての参照が解決できるか（改正で書かれた本文の参照先の確認用）"""
    bad = []
    for n, anc in walk(root.children):
        if only and not only(n):
            continue
        for where, idx, t in texts(n):
            for r in find_refs(t):
                if resolve(root.children, anc, r) is None:
                    bad.append(f"/{'/'.join(a.label for a in anc + (n,))}: 参照「{r['raw']}」の参照先がない")
    return bad
