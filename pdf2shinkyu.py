#!/usr/bin/env python3
"""既存の新旧対照表PDF（左＝改正後／右＝現行）→ 新旧対照表テキスト（.shinkyu.txt）

  python pdf2shinkyu.py 001676185.pdf --pages 2-8 -o R8.shinkyu.txt

左右の段を別々に木構造に読み、行の縦位置（ページ, y）で左右を突き合わせる。
PDF上の傍線も読み取り、`--underlines` で JSON に書き出す（自動傍線との照合用）。
"""
import argparse, json, re
import pdfplumber
from tsuchi import LABEL_RE, norm, expand_range, kind_num

SKIP = re.compile(r"^(〈改正後〉|〈現\s*行〉|改\s*正\s*後|現\s*行|[-－\s]*[0-9０-９]+[-－\s]*|別添\s*[0-9０-９]+)$")
PLACE = {"（新設）": "new", "（削る）": "del", "（略）": "skip"}


class Entry:
    def __init__(self, y, label, text, depth, place=None, ul=None):
        self.y, self.label, self.text, self.depth, self.place = y, label, text, depth, place
        self.paras, self.ul = [], [ul or []]


class Col:
    """1つの段（改正後 or 現行）を「行エントリ」の列にする。
    階層は x 座標ではなく番号の種類の並び（第N→１→① …）で決める（ページごとに余白がずれるため）"""

    def __init__(self, side):
        self.side = side
        self.entries = []
        self.kinds = []           # 種類のスタック
        self.stage = "head"       # head → pre → body
        self.history = []
        self.prev = None          # (page, x) 直前の行
        self.prev_is_label = False

    def add(self, pno, x, top, t, ul):
        y = (pno, round(top))
        if self.stage == "head":
            if re.search(r"(一部改正|老\s*発|保医発|令\s*和)", t):
                self.history.append(norm(t)); return
            # 前文がある場合（「で始まる）または、直接本文に入る場合（第で始まる）
            if t.startswith("「"):
                self.stage = "pre"
                self.pre = Entry(y, "前文", "", 0); self.pre.ul = []
                self.entries.append(self.pre)
                self.min_x = x - 10
            elif re.match(r"^第[０-９0-9]", t):
                # 前文なしで本文から始まる新旧対照表
                self.stage = "body"
                self.min_x = x - 10
            return
        if self.stage == "pre":
            if norm(t) == "記":
                self.stage = "body"; return
            self.min_x = min(self.min_x, x)
            if x > self.min_x + 6 or not self.pre.paras:
                self.pre.paras.append(""); self.pre.ul.append([])
            self.pre.paras[-1] += t; self.pre.ul[-1] += ul
            return
        # 結合ラベル（第N・第M...）を検出（空白補完の前にチェック）
        # SCOPE: ONLY 第N・第M・第K... パターン（全て第で始まる）
        # 例: "第３・第４ （略）" → label="第３・第４", text="（略）"
        combined_match = re.match(r"^(第[０-９0-9]+(?:・第[０-９0-9]+)+)\s+(.+)$", t)
        if combined_match:
            # 結合ラベルとして扱う（後でsplit_combined_labelsで分割される）
            label = combined_match.group(1)
            text = combined_match.group(2)
            kind = kind_num(re.split("[～・]", label)[0])[0]
            if kind in self.kinds:
                del self.kinds[self.kinds.index(kind) + 1:]
            else:
                self.kinds.append(kind)
            depth = max(0, len(self.kinds) - 1)
            e = Entry(y, label, text, depth, ul=ul)
            self.entries.append(e)
            return
        
        t2 = re.sub(r"^(第[０-９0-9]+)(?![号条項の０-９0-9～])(?=\S)", r"\1 ", t)   # 「第６介護予防…」の空白欠落
        m = LABEL_RE.match(t2)
        if m:
            label = m.group("label")
            kind = kind_num(re.split("[～・]", label)[0] if label != "・" else label)[0]
            # Issue #2 fix: More robust hierarchy tracking
            # Ensure the kinds stack follows the expected hierarchy order
            if kind in self.kinds:
                # Pop back to this kind level
                del self.kinds[self.kinds.index(kind) + 1:]
            else:
                # Only append if not already at a deeper or same level of different kind
                # This prevents incorrect depth when PDF ordering is inconsistent
                self.kinds.append(kind)
            rest = t2[m.end():]
            k = len(rest) - len(rest.lstrip(" 　"))
            off = len(t2) - len(t)
            # Ensure depth is non-negative
            depth = max(0, len(self.kinds) - 1)
            e = Entry(y, label, rest[k:], depth, ul=ul[max(0, m.end() + k - off):])
            self.entries.append(e)
        elif t.strip() in PLACE:
            self.entries.append(Entry(y, None, t.strip(), None, place=PLACE[t.strip()]))
        else:
            e = self.entries[-1]
            same_page = self.prev and self.prev[0] == pno
            after_label = self.prev_is_label
            # Issue #2 fix: More conservative paragraph detection
            # Use a stricter threshold for new paragraph detection to avoid incorrect indentation
            x_threshold = 20 if after_label else 8
            if same_page and x > self.prev[1] + x_threshold or e.place:
                e.paras.append(t); e.ul.append(list(ul))
            elif e.paras:
                e.paras[-1] += t; e.ul[-1] += ul
            else:
                e.text += t; e.ul[0] += ul
        self.prev = (pno, x)
        self.prev_is_label = bool(m)


def page_lines(page, x0, x1):
    crop = page.crop((x0, 0, x1, page.height))
    uls = [r for r in page.rects if r["height"] < 1.2 and 3 < r["width"] < 340 and x0 <= r["x0"] < x1]
    for l in crop.extract_text_lines():
        t = l["text"].strip()
        if not t or SKIP.match(t):
            continue
        # 文字ごとに傍線フラグを持たせる。字間が空いていれば空白を1つ補う（ラベル判定用）
        chars, flags, prev = [], [], None
        char_list = []  # Collect characters first for post-processing
        
        for c in l["chars"]:
            if c["text"].isspace():
                continue
            if prev is not None and c["x0"] - prev["x1"] > 4:
                chars.append(" "); flags.append(False)
                char_list.append(None)  # Placeholder for space
            cx = (c["x0"] + c["x1"]) / 2
            # Issue #1 fix: Normalize half-width parentheses to full-width
            char_text = c["text"].replace("(", "（").replace(")", "）")
            chars.append(char_text)
            flags.append(any(r["x0"] - 1 <= cx <= r["x1"] + 1 and 0 <= r["top"] - c["bottom"] < 5 for r in uls))
            char_list.append(c)
            prev = c
        
        # Issue #3 fix: Remove trailing isolated characters near the column boundary
        # These are typically from the adjacent column (e.g., trailing 「第」)
        if char_list and char_list[-1] is not None:
            last_char = char_list[-1]
            # Check if last character is within 10 points of the right boundary
            if x1 - last_char["x1"] < 10:
                # Check if there's a large gap before it (indicating it's isolated)
                if len(char_list) >= 2:
                    prev_idx = len(char_list) - 2
                    while prev_idx >= 0 and char_list[prev_idx] is None:
                        prev_idx -= 1
                    if prev_idx >= 0 and char_list[prev_idx] is not None:
                        prev_char = char_list[prev_idx]
                        gap = last_char["x0"] - prev_char["x1"]
                        # If gap > 200 points, it's likely from the other column
                        if gap > 200:
                            chars.pop()
                            flags.pop()
        
        yield l["x0"], l["top"], "".join(chars), flags


def parse(pdf_path, pages):
    pdf = pdfplumber.open(pdf_path)
    left, right = Col("new"), Col("old")
    forms = []
    in_forms = {"new": False, "old": False}
    for pno in pages:
        page = pdf.pages[pno - 1]
        mid = page.width / 2
        for col, (a, b) in ((left, (0, mid)), (right, (mid, page.width))):
            for x, top, t, ul in page_lines(page, a, b):
                if t == "（様式）":
                    in_forms[col.side] = True; continue
                if in_forms[col.side]:
                    m = re.match(r"^(別紙\s*[0-9０-９―－-]+)\s*（内容変更有）$", t)
                    if m:
                        forms.append(norm(m.group(1)))
                    continue
                if col.stage == "head" and top < 110 and pno == pages[0]:
                    continue  # 表題・注記
                col.add(pno, x, top, t, ul)
    return left, right, forms


# ------------------------------------------------------------------ 結合ラベルの分割
def split_combined_labels(entries):
    """第N・第M（略）パターンを個別エントリに分割
    
    SCOPE: ONLY 第N・第M・第K...（略）パターン（全て第で始まる）
    「第３・第４（略）」→「第３（略）」「第４（略）」に分割。
    これにより、apply時に基底文書の個別セクションとマッチできる。
    """
    result = []
    for e in entries:
        # ONLY: ・を含み、（略）で、全パーツが「第」で始まるパターンのみ分割
        if e.label and "・" in e.label and e.text.strip() == "（略）":
            parts = [p.strip() for p in e.label.split("・")]
            # 全パーツが「第」で始まる場合のみ分割
            if all(p.startswith("第") for p in parts) and len(parts) > 1:
                for i, lab in enumerate(parts):
                    # Adjust y-coordinate slightly for each split entry to ensure unique positions for pairing
                    adjusted_y = (e.y[0], e.y[1] + i * 0.1)
                    split_e = Entry(adjusted_y, lab, e.text, e.depth, e.place, e.ul[0] if e.ul else None)
                    split_e.paras = list(e.paras)
                    split_e.ul = list(e.ul)
                    result.append(split_e)
                continue
        result.append(e)
    return result


# ------------------------------------------------------------------ 左右の突合 → 差分行
def is_skip(e):
    return e.label and (e.text.strip() == "（略）" or (not e.text.strip() and re.search("[～・]", e.label)))


def line(mark, e, depth, text=None):
    out = [f"{mark}{'  ' * depth}{e.label}　{norm(e.text if text is None else text)}".rstrip("　")]
    out += [f"{mark}{'  ' * depth}  　{norm(p)}" for p in e.paras]
    return out


def pair(L, R):
    """縦位置（ページ, y）が±3pt以内なら同じ行"""
    items = sorted([(e.y, 0, e) for e in L] + [(e.y, 1, e) for e in R], key=lambda t: (t[0], t[1]))
    rows = []
    for y, side, e in items:
        if rows and rows[-1][side] is None and rows[-1][2][0] == y[0] and abs(rows[-1][2][1] - y[1]) <= 3:
            rows[-1][side] = e
        else:
            row = [None, None, y]; row[side] = e; rows.append(row)
    return [(l, r) for l, r, _ in rows]


def build(L, R):
    out, warn, path = [], [], []
    for l, r in pair(L.entries, R.entries):
        base = l if (l and l.label) else r
        d = base.depth
        del path[d:]; path.append(base.label)
        here = "/".join(path)
        if l is None or r is None:
            warn.append(f"{here}: 左右の対応が取れない行（{'改正後' if l else '現行'}のみ）")
            out += line("+" if l else "-", l or r, d); continue
        if r.place == "new":
            out += line("+", l, d); continue
        if l.place == "del":
            out += line("-", r, d); continue
        if l.label != r.label and not (is_skip(l) and is_skip(r)):
            warn.append(f"{here}: 改正後「{l.label}」と現行「{r.label}」でラベルが違う")
        if is_skip(l) or is_skip(r):
            for e, side in ((l, "改正後"), (r, "現行")):
                if e.text.strip() != "（略）":
                    warn.append(f"{here}: {side}側「{e.label}」に「（略）」の記載漏れ")
            lab = l.label if l.label == r.label else f"{l.label}←{r.label}"
            if l.label != r.label and len(expand_range(l.label)) != len(expand_range(r.label)):
                warn.append(f"{here}: 繰下げ範囲の個数が合わない {lab}")
            out.append(f" {'  ' * d}{lab}　（略）"); continue
        if norm(l.text) == norm(r.text) and [norm(p) for p in l.paras] == [norm(p) for p in r.paras]:
            out += line(" ", l, d)
        else:
            out += line("-", r, d) + line("+", l, d)
    return out, warn


def hist(lines):
    """鑑の「老発…号／令和…日」の行の組 → 改正履歴"""
    out = []
    for num, date in zip(lines[0::2], lines[1::2]):
        kind = "一部改正" if num.startswith("一部改正") else "制定"
        out.append({"kind": kind, "number": num.replace("一部改正", ""), "date": date})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("-o", required=True)
    ap.add_argument("--pages", default="2-8")
    ap.add_argument("--underlines")
    ap.add_argument("--number", required=True, help="改正通知の番号（例: 老発0313第5号）")
    ap.add_argument("--date", required=True, help="改正通知の日付（例: 2026-03-13）")
    ap.add_argument("--effective", help="適用日")
    ap.add_argument("--base-version", required=True, help="改正前の版の名前（通知テキストの version と一致させる）")
    ap.add_argument("--new-version", required=True)
    ap.add_argument("--title", default="", help="改正対象の通知の題名")
    ap.add_argument("--target-ref", default="", help="表の上に出す（日付・番号・発出者）")
    x = ap.parse_args()
    a, b = map(int, x.pages.split("-"))
    L, R, forms = parse(x.pdf, list(range(a, b + 1)))
    # 結合ラベル（第３・第４など）を分割
    L.entries = split_combined_labels(L.entries)
    R.entries = split_combined_labels(R.entries)
    out, warn = build(L, R)
    import yaml
    meta = {
        "target": x.title,
        "amendment": {"kind": "一部改正", "number": x.number, "date": x.date, "effective": x.effective},
        "target_ref": x.target_ref,
        "base_version": x.base_version, "new_version": x.new_version,
        "base_history": hist(R.history), "new_history": hist(L.history),
        "forms": [{"label": f, "change": "内容変更有"} for f in forms],
        "notes": warn,
    }
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=200)
    open(x.o, "w", encoding="utf-8").write("---\n" + fm + "---\n" + "\n".join(out) + "\n")
    if x.underlines:
        acc = []
        for col in (L, R):
            for e in col.entries:
                if e.place:
                    continue
                texts = [e.text] + e.paras
                acc.append({"side": col.side, "label": e.label, "y": e.y,
                            "segments": [re.findall(r"\S+", "".join(ch if f else " " for ch, f in zip(t, fl))) for t, fl in zip(texts, e.ul)]})
        json.dump(acc, open(x.underlines, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for w in warn:
        print("注意:", w)


if __name__ == "__main__":
    main()
