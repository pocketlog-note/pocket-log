"""content/*.md から静的サイト (docs/) を作る。標準ライブラリだけで動く。

使い方:  python build.py
記事の先頭には次の形式のメタ情報を書く:
---
title: タイトル
date: 2026-11-21
description: 一行説明
draft: true   (true の記事は公開物に含めない)
---
"""
import html
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "content"
OUT = ROOT / "docs"
SITE_NAME = "ポケットログ"
SITE_DESC = "小さな出費で満足する「ポケット消費」のヒントを、短くまとめるメモ帳。"

CSS = """
body{font-family:system-ui,"Yu Gothic",sans-serif;max-width:42rem;margin:0 auto;padding:1rem;line-height:1.9;color:#222}
a{color:#0a5}header,footer{margin:1.5rem 0}h1{font-size:1.6rem}h2{margin-top:2rem;border-left:4px solid #0a5;padding-left:.5rem}
.meta{color:#666;font-size:.9rem}li{margin:.3rem 0}
"""


def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[(.+?)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', s)
    return s


def md_to_html(body):
    out, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")
            items = []

    for line in body.splitlines():
        if not line.strip():
            flush()
        elif line.startswith("## "):
            flush()
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("- "):
            if para:
                flush()
            items.append(line[2:])
        else:
            if items:
                flush()
            para.append(line.strip())
    flush()
    return "\n".join(out)


def page(title, desc, inner, depth_prefix=""):
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="stylesheet" href="{depth_prefix}style.css"></head>
<body><header><a href="{depth_prefix}index.html"><strong>{SITE_NAME}</strong></a></header>
<main>{inner}</main>
<footer class="meta">{SITE_NAME} / 個人の覚え書きです。内容の正確さは保証できません。</footer>
</body></html>"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    posts = []
    for p in sorted(SRC.glob("*.md")):
        meta, body = parse(p)
        if meta.get("draft", "false").lower() == "true" and not os.environ.get("INCLUDE_DRAFTS"):
            print("skip(draft):", p.name)
            continue
        title = meta.get("title", p.stem)
        date = meta.get("date", "")
        desc = meta.get("description", "")
        inner = f"<h1>{html.escape(title)}</h1><p class='meta'>{date}</p>{md_to_html(body)}"
        (OUT / "posts" / f"{p.stem}.html").write_text(page(title, desc, inner, "../"), encoding="utf-8")
        posts.append((date, title, desc, p.stem))
    posts.sort(reverse=True)
    lis = "".join(
        f"<li><a href='posts/{s}.html'>{html.escape(t)}</a> <span class='meta'>{d}</span><br>"
        f"<span class='meta'>{html.escape(ds)}</span></li>"
        for d, t, ds, s in posts
    )
    (OUT / "index.html").write_text(
        page(SITE_NAME, SITE_DESC, f"<h1>{SITE_NAME}</h1><p>{SITE_DESC}</p><ul>{lis}</ul>"), encoding="utf-8")
    print(f"{len(posts)} 記事を docs/ に出力しました")


if __name__ == "__main__":
    main()
