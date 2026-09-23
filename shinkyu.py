#!/usr/bin/env python3
"""新旧対照表テキストの適用・生成・描画

  python shinkyu.py apply  BASE.tsuchi.txt PATCH.shinkyu.txt -o NEW.tsuchi.txt [--force]
      改正（新旧対照表テキスト）を原本に機械的に反映。文脈・現行文が原本と一字でも違えば止まる
  python shinkyu.py diff   OLD.tsuchi.txt NEW.tsuchi.txt -o PATCH.shinkyu.txt
      2つの版から新旧対照表テキストを作る（全文を直接直した場合でも同じ形式になる）
  python shinkyu.py render PATCH.shinkyu.txt -o table.html
      新旧対照表（改正後｜現行、傍線つき）を HTML で出力
"""
import argparse, copy, difflib, html, re, sys
import yaml
from tsuchi import Node, load, save, norm, expand_range, kind_num
import refs as R


# =================================================================== apply
def body(n):
    return [norm(n.text)] + [norm(p) for p in n.paras] + [norm(p) for p in n.tail]


def apply_children(base, patch, path, errs, strict=True):
    """base: 原本の子リスト, patch: 対照表テキストの子リスト → 新しい子リスト"""
    out, i, k = [], 0, 0

    def err(msg):
        errs.append(f"{path or '/'}: {msg}")

    def at(i):
        return base[i].label if i < len(base) else "（なし）"

    while k < len(patch):
        p = patch[k]
        here = f"{path}/{p.label}"
        if p.mark == " " and p.text == "（略）":               # 範囲の（略）… 原本の並びと一致するか検証して写す
            news = expand_range(p.label)
            olds = expand_range(p.old_label) if p.old_label else news
            if len(news) != len(olds):
                err(f"繰下げ範囲の個数が合わない {p.label}←{p.old_label}")
            for j, ol in enumerate(olds):
                if at(i) != ol:
                    err(f"（略）とされた「{ol}」が原本の該当位置にない（原本側は「{at(i)}」）")
                    break
                n = copy.deepcopy(base[i])
                n.label = news[j] if j < len(news) else ol
                out.append(n); i += 1
            k += 1
        elif p.mark == " ":                                        # 見出し（文脈）
            if at(i) != p.label:
                err(f"見出し「{p.label}」が原本の該当位置にない（原本側は「{at(i)}」）")
                k += 1; continue
            b = base[i]
            if norm(b.text) != norm(p.text) or (p.paras and [norm(x) for x in p.paras] != [norm(x) for x in b.paras]):
                err(f"見出し・本文が原本と違う\n      原本: {b.text[:60]}\n      表　: {p.text[:60]}")
            n = copy.deepcopy(b)
            n.children = apply_children(b.children, p.children, here, errs, strict)
            out.append(n); i += 1; k += 1
        elif p.mark == "-":                                        # 現行（削る／改める）
            if at(i) != p.label:
                err(f"削る・改める「{p.label}」が原本の該当位置にない（原本側は「{at(i)}」）")
                k += 1; continue
            b = base[i]
            if body(b)[:1 + len(p.paras)] != body(p)[:1 + len(p.paras)]:
                x, y = "".join(body(b)), "".join(body(p))
                err(f"「{p.label}」の現行の文が原本と一致しない（一致率 {difflib.SequenceMatcher(None, x, y).ratio():.1%}）\n"
                    f"      原本: {x[:70]}\n      表　: {y[:70]}")
            i += 1
            if k + 1 < len(patch) and patch[k + 1].mark == "+":    # 直後が '+' → 改める
                q = patch[k + 1]
                n = Node(q.label, q.text, list(q.paras), tail=list(b.tail))
                n.uid, n.authored = b.uid, True        # 同じ項目の書き換え（参照先としては同一）
                if any(c.mark == " " for c in q.children):
                    n.children = apply_children(b.children, q.children, here, errs, strict)
                else:
                    n.children = build_new(q.children) if q.children else copy.deepcopy(b.children)
                out.append(n); k += 2
            else:
                k += 1                                             # （削る）
        elif p.mark == "+":                                        # （新設）
            n = Node(p.label, p.text, list(p.paras))
            n.children = build_new(p.children)
            out.append(n); k += 1
        else:
            err(f"未知の印 {p.mark!r}"); k += 1
    if i < len(base):
        if strict:
            err(f"対照表に出てこない項目が原本に残っている: {'・'.join(b.label for b in base[i:])}")
        out += copy.deepcopy(base[i:])
    return out


def build_new(children):
    res = []
    for c in children:
        n = Node(c.label, c.text, list(c.paras))
        n.children = build_new(c.children)
        res.append(n)
    return res


def check_numbering(nodes, path, errs):
    """同じ種類の番号が 1,2,3… と連続しているか（繰下げ漏れの検出）"""
    by = {}
    for n in nodes:
        k, v = kind_num(n.label)
        if k in ("num", "maru", "paren", "kana", "dai"):
            by.setdefault(k, []).append((v, n.label))
    for k, vs in by.items():
        nums = [v for v, _ in vs]
        if nums != list(range(nums[0], nums[0] + len(nums))):
            errs.append(f"{path or '/'}: 番号が連続していない {'・'.join(l for _, l in vs)}")
    for n in nodes:
        check_numbering(n.children, f"{path}/{n.label}", errs)


def cmd_apply(a):
    bmeta, broot = load(a.base)
    pmeta, proot = load(a.patch, marks=True)
    errs = []
    want = pmeta.get("base_version")
    if want and bmeta.get("version") != want:
        msg = f"版が違う: 原本は {bmeta.get('version')}、この改正は {want} を前提としている"
        if not a.force:
            sys.exit("エラー: " + msg + "（--force で差異の一覧を出す）")
        errs.append(msg)
    R.mark_uids(broot)
    snap = R.snapshot(broot)                                 # 改正前の版で参照先を解決しておく
    new = Node("ROOT")
    new.children = apply_children(broot.children, proot.children, "", errs, strict=not a.lenient)
    changes, warns = ([], []) if a.no_follow else R.follow(broot, new, snap)
    for path, old, rep in changes:
        print(f"参照を追従: {path}  {old} → {rep}")
    for w in warns:
        print("注意:", w)
    for b in R.check_refs(new, only=lambda n: not hasattr(n, "uid") or getattr(n, "authored", False)):
        errs.append("改正で書かれた本文の" + b)
    before, after = [], []
    check_numbering(broot.children, "", before)
    check_numbering(new.children, "", after)
    errs += [e for e in after if e not in before]          # 改正で新たに生じた番号の乱れだけを誤りとする
    for e in before:
        print("参考（原本からある番号の乱れ）:", e)
    if errs:
        print(f"適用できない箇所 {len(errs)} 件:")
        for e in errs:
            print(" -", e)
        if not a.force:
            sys.exit(1)
    am = pmeta["amendment"]
    meta = dict(bmeta)
    meta["version"] = pmeta.get("new_version", am["number"])
    meta["history"] = list(bmeta.get("history", [])) + [{"kind": am["kind"], "number": am["number"], "date": str(am["date"])}]
    if pmeta.get("forms"):
        meta["forms"] = pmeta["forms"]
    save(a.o, meta, new)
    print(f"→ {a.o}（{meta['version']}）")
    if a.patch_out:
        # 参照の追従で本文が変わった項目も含めた「完成版」の新旧対照表テキスト
        out = []
        diff_children(broot.children, new.children, 0, out)
        pm = dict(pmeta)
        if changes:
            pm["auto_ref_updates"] = [f"{p}: {o} → {r}" for p, o, r in changes]
        fm = yaml.safe_dump(pm, allow_unicode=True, sort_keys=False, width=200)
        open(a.patch_out, "w", encoding="utf-8").write("---\n" + fm + "---\n" + "\n".join(out) + "\n")
        print(f"→ {a.patch_out}（参照の追従 {len(changes)} 件を含む対照表テキスト）")


# =================================================================== diff
def same(a, b):
    return body(a) == body(b) and len(a.children) == len(b.children) and all(same(x, y) for x, y in zip(a.children, b.children))


def range_label(labels):
    if len(labels) == 1:
        return labels[0]
    return f"{labels[0]}{'・' if len(labels) == 2 else '～'}{labels[-1]}"


def emit(mark, n, depth, out, kids=True):
    pad = "  " * depth
    out.append(f"{mark}{pad}{n.label}　{n.text}".rstrip("　"))
    out += [f"{mark}{pad}  　{p}" for p in n.paras]
    if kids:
        for c in n.children:
            emit(mark, c, depth + 1, out)


def diff_children(old, new, depth, out):
    """兄弟の並びを「本文」で突き合わせる（番号は比べない → 繰下げを検出できる）"""
    pad = "  " * depth
    sm = difflib.SequenceMatcher(None, [tuple(body(n)) for n in old], [tuple(body(n)) for n in new], autojunk=False)
    run = []

    def flush():
        if run:
            nl, ol = [n.label for _, n in run], [o.label for o, _ in run]
            out.append(f" {pad}{range_label(nl)}{'' if nl == ol else '←' + range_label(ol)}　（略）")
            run.clear()

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for o, n in zip(old[i1:i2], new[j1:j2]):
                if same(o, n):
                    if run and ((run[-1][0].label == run[-1][1].label) != (o.label == n.label)
                                or kind_num(run[-1][1].label)[0] != kind_num(n.label)[0]):
                        flush()                      # 繰下げ有無が変わる所で区切る（「⑬（略）｜⑫（略）」）
                    run.append((o, n)); continue
                flush()
                out.append(f" {pad}{n.label}　{n.text}")
                out += [f" {pad}  　{p}" for p in n.paras]
                diff_children(o.children, n.children, depth + 1, out)
            continue
        flush()
        os_, ns = old[i1:i2], new[j1:j2]
        m = min(len(os_), len(ns)) if tag == "replace" else 0
        for o, n in zip(os_[:m], ns[:m]):
            emit("-", o, depth, out, kids=False)
            emit("+", n, depth, out, kids=False)
            if o.children or n.children:
                diff_children(o.children, n.children, depth + 1, out)
        for o in os_[m:]:
            emit("-", o, depth, out)
        for n in ns[m:]:
            emit("+", n, depth, out)
    flush()


def cmd_diff(a):
    om, oroot = load(a.old)
    nm, nroot = load(a.new)
    out = []
    diff_children(oroot.children, nroot.children, 0, out)
    h = nm["history"][-1]
    meta = {"target": nm.get("title"), "amendment": {"kind": h["kind"], "number": h["number"], "date": str(h["date"])},
            "base_version": om.get("version"), "new_version": nm.get("version"),
            "base_history": om.get("history"), "new_history": nm.get("history")}
    if nm.get("forms"):
        meta["forms"] = nm["forms"]
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=200)
    open(a.o, "w", encoding="utf-8").write("---\n" + fm + "---\n" + "\n".join(out) + "\n")
    print(f"→ {a.o}")


# =================================================================== render
# 語句の単位：漢字・カタカナ・数字・英字・ローマ数字・丸数字のまとまり ／ ひらがなのまとまり ／ 記号1字
WORD = re.compile(r"[一-龥々〆ヵヶァ-ヴー0-9０-９A-Za-zＡ-Ｚａ-ｚⅠ-Ⅻ①-⑳㉑-㉟㊱-㊿⑴-⒇]+|[ぁ-ゖ]+|.", re.S)


def esc(s):
    return html.escape(s)


def u(s):
    return f'<span class="u">{esc(s)}</span>' if s else ""


def underline_pair(old, new):
    """語句単位の差分 → (新側HTML, 旧側HTML)。大きく書き換わった文は全体に傍線"""
    ta, tb = WORD.findall(new), WORD.findall(old)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    if not old or not new or sm.ratio() < 0.5:
        return u(new), u(old)
    A, B = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        a, b = "".join(ta[i1:i2]), "".join(tb[j1:j2])
        A.append(esc(a) if tag == "equal" else u(a))
        B.append(esc(b) if tag == "equal" else u(b))
    return "".join(A), "".join(B)


def lab(label, ul=False):
    return (u(label) if ul else esc(label)) + "　" if label and label != "前文" else ""


def render_rows(nodes, depth, rows):
    k = 0
    while k < len(nodes):
        p = nodes[k]
        if p.mark == " " and p.text == "（略）":
            ren = p.old_label and p.old_label != p.label
            rows.append((depth, f"{lab(p.label, ren)}（略）", f"{lab(p.old_label or p.label, ren)}（略）"))
            k += 1
        elif p.mark == " ":
            c = lab(p.label) + esc(p.text)
            rows.append((depth, c, c))
            rows += [(depth, "\x01" + esc(x), "\x01" + esc(x)) for x in p.paras]
            render_rows(p.children, depth + 1, rows)
            k += 1
        elif p.mark == "-" and k + 1 < len(nodes) and nodes[k + 1].mark == "+":   # 改める
            q = nodes[k + 1]
            olds, news = [p.text] + p.paras, [q.text] + q.paras
            if p.label == "前文":
                olds, news = p.paras, q.paras
            for j in range(max(len(olds), len(news))):
                o = olds[j] if j < len(olds) else ""
                n = news[j] if j < len(news) else ""
                nh, oh = underline_pair(o, n)
                if j == 0 and p.label != "前文":
                    ren = p.label != q.label
                    rows.append((depth, lab(q.label, ren) + nh, lab(p.label, ren) + oh))
                else:
                    rows.append((depth, "\x01" + nh, "\x01" + oh))
            render_rows(q.children, depth + 1, rows)
            k += 2
        else:                                                                     # 新設 / 削る
            new = p.mark == "+"
            first = [True]

            def walk(n, d):
                if n.mark == " " and n.text == "（略）":
                    c = f"{lab(n.label)}（略）"
                else:
                    c = lab(n.label, True) + u(n.text)
                other = ("（新設）" if new else "（削る）") if first[0] else ""
                first[0] = False
                rows.append((d, c, other) if new else (d, other, c))
                for x in n.paras:
                    rows.append((d, "\x01" + u(x), "\x01") if new else (d, "\x01", "\x01" + u(x)))
                for c2 in n.children:
                    walk(c2, d + 1)
            walk(p, depth)
            k += 1


def history_block(hist, new_from=None):
    lines = []
    for i, e in enumerate(hist or []):
        a = ("一部改正　" if e.get("kind") != "制定" else "") + esc(str(e["number"]))
        b = esc(str(e["date"]))
        if new_from is not None and i >= new_from:
            a, b = f'<span class="u">{a}</span>', f'<span class="u">{b}</span>'
        lines += [a, b]
    return '<div class="kan">' + "<br>".join(lines) + "</div>"


def cmd_render(a):
    meta, root = load(a.patch, marks=True)
    rows = []
    bh, nh = meta.get("base_history"), meta.get("new_history")
    if bh and isinstance(bh[0], dict):
        rows.append((0, history_block(nh, len(bh)), history_block(bh)))
    t = f'<div class="ttl">{esc(meta.get("target", ""))}</div>'
    rows.append((0, t, t))
    pre = [n for n in root.children if n.label == "前文"]
    rest = [n for n in root.children if n.label != "前文"]
    render_rows(pre, 0, rows)
    rows.append((0, '<div class="ki">記</div>', '<div class="ki">記</div>'))
    render_rows(rest, 0, rows)
    if meta.get("forms"):
        rows.append((0, "（様式）", "（様式）"))
        rows += [(1, f'{esc(f["label"])}　（{esc(f["change"])}）', "") for f in meta["forms"]]
    def td(d, c):
        if c.startswith("\x01"):          # 字下げ段落
            return f'<td style="padding-left:{0.5 + d + 1}em;text-indent:1em">{c[1:]}</td>'
        if c.startswith("<div"):
            return f"<td>{c}</td>"
        return f'<td style="padding-left:{0.5 + d + 1}em;text-indent:-1em">{c}</td>'   # ぶら下げ
    trs = "\n".join(f"<tr>{td(d, l)}{td(d, r)}</tr>" for d, l, r in rows)
    am = meta.get("amendment", {})
    notes = meta.get("notes") or []
    note_html = (f'<details><summary>原典PDFから取り込んだ際の注意 {len(notes)} 件</summary><ul>'
                 + "".join(f"<li>{esc(x)}</li>" for x in notes) + "</ul></details>") if notes else ""
    open(a.o, "w", encoding="utf-8").write(TEMPLATE.format(
        title=esc(meta.get("target", "")), sub=esc(meta.get("target_ref", "")), trs=trs,
        amend=esc(f'{am.get("number", "")}（{am.get("date", "")}）'), notes=note_html))
    print(f"→ {a.o}")


TEMPLATE = """<!doctype html><html lang="ja"><meta charset="utf-8">
<title>新旧対照表</title>
<style>
:root{{--bg:#fff;--fg:#111;--line:#000;--muted:#666}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1b1b1b;--fg:#eee;--line:#bbb;--muted:#aaa}}}}
body{{background:var(--bg);color:var(--fg);font-family:"Hiragino Mincho ProN","Yu Mincho","Noto Serif JP",serif;margin:24px auto;max-width:1200px;padding:0 16px;font-size:14px}}
h1{{font-size:16px;text-align:center;font-weight:normal;margin:0}}
.sub{{text-align:center;margin:.2em 0 1em}}
.note{{text-align:right;font-size:13px;margin:0 0 .3em}}
table{{border-collapse:collapse;width:100%;table-layout:fixed}}
th{{font-weight:normal;letter-spacing:1em;border:1px solid var(--line);padding:.2em}}
td{{border-left:1px solid var(--line);border-right:1px solid var(--line);vertical-align:top;padding:.1em .6em;line-height:1.8;text-indent:0}}
tr:last-child td{{border-bottom:1px solid var(--line)}}
.u{{text-decoration:underline;text-underline-offset:4px;text-decoration-thickness:1px}}
.kan{{text-align:right;padding:.5em 0}} .ttl,.ki{{text-align:center;padding:.6em 0}}
details{{margin-top:1em;color:var(--muted);font-size:13px}}
</style>
<h1>{title}</h1>
<p class="sub">{sub}</p>
<p class="note">（傍線部分は改正部分）</p>
<table><tr><th>改正後</th><th>現行</th></tr>
{trs}
</table>
<p class="note" style="margin-top:.6em">新旧対照表テキスト {amend} から自動生成</p>
{notes}
</html>"""


# =================================================================== lint
def cmd_lint(a):
    """番号参照の点検：参照先がない／「○○については、…を準用」で項目名が参照先と違う"""
    meta, root = load(a.doc)
    bad = R.check_refs(root)
    names = []
    for n, anc in R.walk(root.children):
        m = re.match(r"「([^」]+)」", n.text)
        if not m:
            continue
        for r in R.find_refs(n.text):
            if not n.text[r["end"]:].startswith("を準用"):
                continue
            t = R.resolve(root.children, anc, r)
            tm = re.match(r"「([^」]+)」", t.text) if t else None
            if tm and core(tm.group(1)) != core(m.group(1)):
                names.append(f"/{'/'.join(x.label for x in anc + (n,))}: 「{m.group(1)}」が {r['raw']}「{tm.group(1)}」を準用している")
    print(f"参照先がない: {len(bad)} 件"); [print(" -", b) for b in bad]
    print(f"準用先の項目名が違う（表記揺れを除く）: {len(names)} 件"); [print(" -", b) for b in names]


def core(name):
    """表記揺れ（入居者／入所者／利用者、介護予防、括弧書き、加算／体制）を除いた項目名"""
    name = re.sub(r"（[^）]*）", "", name)
    for a, b in (("入居者", "利用者"), ("入所者", "利用者"), ("介護予防", ""), ("加算", ""), ("体制", "")):
        name = name.replace(a, b)
    return name


# =================================================================== main
def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("apply"); p.add_argument("base"); p.add_argument("patch"); p.add_argument("-o", required=True)
    p.add_argument("--force", action="store_true", help="版違い・不一致があっても最後まで処理して一覧を出す")
    p.add_argument("--lenient", action="store_true", help="対照表に出てこない末尾の項目を不変とみなす")
    p.add_argument("--no-follow", action="store_true", help="番号参照の追従をしない")
    p.add_argument("--patch-out", help="参照の追従を含めた対照表テキストの書き出し先")
    p = sp.add_parser("lint"); p.add_argument("doc")
    p = sp.add_parser("diff"); p.add_argument("old"); p.add_argument("new"); p.add_argument("-o", required=True)
    p = sp.add_parser("render"); p.add_argument("patch"); p.add_argument("-o", required=True)
    a = ap.parse_args()
    {"apply": cmd_apply, "diff": cmd_diff, "render": cmd_render, "lint": cmd_lint}[a.cmd](a)


if __name__ == "__main__":
    main()
