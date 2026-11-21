"""content/*.md（記事）と pages/*.md（固定ページ）から静的サイト docs/ を作る。標準ライブラリだけで動く。

使い方:
  python build.py                      本番ビルド（下書き・未来日付・未記入の記事は除外）
  $env:INCLUDE_DRAFTS=1; python build.py   下書きも含めて確認用にビルド

記事の先頭のメタ情報:
---
title: タイトル
date: 2026-11-21          （未来の日付は、その日まで公開されない＝予約公開）
description: 一行説明（検索結果やSNSに出る）
emoji: 🍰                 （一覧カードのアイコン。任意）
pr: true                  （アフィリエイトリンクを含むとき。冒頭にPR表記が出る）
draft: true               （true の間は公開されない）
---
"""
import html
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).parent
POSTS_SRC = ROOT / "content"
PAGES_SRC = ROOT / "pages"
OUT = ROOT / "docs"

SITE_URL = "https://pocketlog-note.github.io/pocket-log"  # 独自ドメインにしたらここを変える
SITE_NAME = "ポケットログ"
SITE_TAGLINE = "1000円以下で、今日がちょっと良くなる。"
SITE_DESC = "物価高でも、小さな出費でちゃんと満たされたい。試してみた本音と、損しない選び方を書いています。"
AUTHOR = "ポケ田"
AUTHOR_BIO = "我慢の節約は続かない派。小さなご褒美を試しては、正直な感想を書いています。"
PLACEHOLDER = re.compile(r"【(体験メモ|要確認)")
JST = timezone(timedelta(hours=9))
INCLUDE_DRAFTS = bool(os.environ.get("INCLUDE_DRAFTS"))


# ---------- 読み込み ----------
def parse(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    meta, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body


def is_true(v):
    return str(v).lower() == "true"


def publish_status(meta, body):
    """公開してよければ None、ダメなら理由を返す。"""
    if INCLUDE_DRAFTS:
        return None
    if is_true(meta.get("draft")):
        return "下書き"
    try:
        d = datetime.strptime(meta.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        return "date の形式が不正"
    if d > datetime.now(JST).date():
        return f"予約（{d} 公開）"
    if PLACEHOLDER.search(body):
        return "未記入の【体験メモ】【要確認】が残っている"
    return None


# ---------- Markdown（必要な分だけ） ----------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    def link(m):
        text, url = m.group(1), html.unescape(m.group(2))
        ext = url.startswith("http")
        attrs = ' target="_blank" rel="noopener sponsored"' if ext and is_affiliate(url) else (
            ' target="_blank" rel="noopener"' if ext else "")
        return f'<a href="{html.escape(url)}"{attrs}>{text}</a>'

    s = re.sub(r"\[(.+?)\]\((https?://[^)\s]+|[\w./#-]+\.html(?:#[\w-]+)?)\)", link, s)
    s = re.sub(r"(【(?:体験メモ|要確認).*?】)", r'<mark class="todo">\1</mark>', s)
    return s


AFFILIATE_HOSTS = ("amzn.to", "amazon.co.jp", "rakuten", "moshimo", "a8.net", "valuecommerce", "afl.")


def is_affiliate(url):
    return any(h in url for h in AFFILIATE_HOSTS)


def md_to_html(body):
    out, para, items, kind, quote = [], [], [], None, []
    headings = []

    def flush():
        nonlocal para, items, kind, quote
        if para:
            out.append("<p>" + "".join(inline(p) for p in para) + "</p>")
            para = []
        if items:
            lis = []
            for i in items:
                box = re.match(r"\[( |x)\] (.*)", i)
                if box:
                    mark = "☑" if box.group(1) == "x" else "☐"
                    lis.append(f'<li class="check">{mark} {inline(box.group(2))}</li>')
                else:
                    lis.append(f"<li>{inline(i)}</li>")
            out.append(f"<{kind}>" + "".join(lis) + f"</{kind}>")
            items, kind = [], None
        if quote:
            out.append('<div class="note">' + "<br>".join(inline(q) for q in quote) + "</div>")
            quote = []

    for line in body.splitlines():
        s = line.rstrip()
        if not s.strip():
            flush()
            continue
        m_ol = re.match(r"\d+\. (.*)", s)
        if s.startswith("## ") or s.startswith("### "):
            flush()
            level = 2 if s.startswith("## ") else 3
            text = s[level + 1:]
            hid = f"h{len(headings) + 1}"
            if level == 2:
                headings.append((hid, text))
            out.append(f'<h{level} id="{hid}">{inline(text)}</h{level}>')
        elif s.startswith("- "):
            if kind != "ul":
                flush()
                kind = "ul"
            items.append(s[2:])
        elif m_ol:
            if kind != "ol":
                flush()
                kind = "ol"
            items.append(m_ol.group(1))
        elif s.startswith("> ") or s == ">":
            if para or items:
                flush()
            quote.append(s[2:])
        else:
            if items or quote:
                flush()
            para.append(s.strip())
    flush()
    return "\n".join(out), headings


# ---------- HTML ----------
def esc(s):
    return html.escape(s, quote=True)


def layout(*, title, desc, inner, prefix, url, og_type="website", full_title=None):
    full = full_title or f"{title}｜{SITE_NAME}"
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(full)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{prefix}feed.xml">
<link rel="stylesheet" href="{prefix}style.css"></head>
<body>
<header class="site"><div class="wrap">
<a class="logo" href="{prefix}index.html">{SITE_NAME}</a>
<nav><a href="{prefix}about.html">運営者</a></nav>
</div></header>
<main class="wrap">{inner}</main>
<footer class="site"><div class="wrap">
<p class="logo-s">{SITE_NAME}</p><p>{SITE_TAGLINE}</p>
<nav><a href="{prefix}about.html">運営者情報</a><a href="{prefix}privacy.html">プライバシーポリシー・免責事項</a><a href="{prefix}contact.html">お問い合わせ</a><a href="{prefix}feed.xml">RSS</a></nav>
<p class="small">© {datetime.now(JST).year} {SITE_NAME}</p>
</div></footer>
</body></html>"""


def card(p, prefix):
    return (f'<a class="card" href="{prefix}posts/{p["slug"]}.html">'
            f'<span class="emoji">{esc(p["emoji"])}</span>'
            f'<span class="body"><span class="t">{esc(p["title"])}</span>'
            f'<span class="d">{esc(p["desc"])}</span>'
            f'<span class="meta">{p["date"]}・{p["minutes"]}分で読める</span></span></a>')


def build_post(p, all_posts):
    toc = ""
    if len(p["headings"]) >= 3:
        toc = '<nav class="toc"><p>この記事でわかること</p><ol>' + "".join(
            f'<li><a href="#{hid}">{inline(t)}</a></li>' for hid, t in p["headings"]) + "</ol></nav>"
    pr = '<p class="pr">この記事にはPR（広告）を含みます。</p>' if p["pr"] else ""
    draft = '<p class="draft">下書きプレビュー（公開されていません）</p>' if p["status_note"] else ""
    others = [o for o in all_posts if o["slug"] != p["slug"]][:3]
    related = ""
    if others:
        related = '<section class="related"><h2>次に読むなら</h2>' + "".join(card(o, "../") for o in others) + "</section>"
    inner = f"""{draft}<article>
<p class="meta">{p["date"]}・{p["minutes"]}分で読める</p>
<h1>{esc(p["title"])}</h1>{pr}{toc}
<div class="content">{p["html"]}</div>
</article>
<aside class="author"><span class="avatar">ポ</span><div><p class="name">{AUTHOR}</p><p>{AUTHOR_BIO}</p></div></aside>
{related}"""
    return layout(title=p["title"], desc=p["desc"], inner=inner, prefix="../",
                  url=f"{SITE_URL}/posts/{p['slug']}.html", og_type="article")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    shutil.copy(ROOT / "style.css", OUT / "style.css")    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    posts = []
    for path in sorted(POSTS_SRC.glob("*.md")):
        meta, body = parse(path)
        reason = publish_status(meta, body)
        if reason:
            print(f"  非公開: {path.name}（{reason}）")
            continue
        content_html, headings = md_to_html(body)
        plain = re.sub(r"<[^>]+>", "", content_html)
        posts.append({
            "slug": path.stem,
            "title": meta.get("title", path.stem),
            "date": meta.get("date", ""),
            "desc": meta.get("description", ""),
            "emoji": meta.get("emoji", "📝"),
            "pr": is_true(meta.get("pr")),
            "status_note": is_true(meta.get("draft")),
            "html": content_html,
            "headings": headings,
            "minutes": max(1, round(len(plain) / 500)),
        })
    posts.sort(key=lambda p: p["date"], reverse=True)

    for p in posts:
        (OUT / "posts" / f"{p['slug']}.html").write_text(build_post(p, posts), encoding="utf-8")

    cards = "".join(card(p, "") for p in posts) or '<p class="empty">最初の記事を準備中です。もう少しお待ちください。</p>'
    hero = f"""<section class="hero"><p class="kicker">ポケット消費の、ゆるい実験ノート</p>
<h1>{SITE_TAGLINE}</h1><p>{SITE_DESC}</p></section>
<h2 class="section">新着の記事</h2><div class="cards">{cards}</div>"""
    (OUT / "index.html").write_text(
        layout(title=SITE_NAME, desc=SITE_DESC, inner=hero, prefix="", url=f"{SITE_URL}/",
               full_title=f"{SITE_NAME}｜{SITE_TAGLINE}"), encoding="utf-8")

    pages = []
    for path in sorted(PAGES_SRC.glob("*.md")):
        meta, body = parse(path)
        content_html, _ = md_to_html(body)
        title = meta.get("title", path.stem)
        inner = f'<article><h1>{esc(title)}</h1><div class="content">{content_html}</div></article>'
        (OUT / f"{path.stem}.html").write_text(
            layout(title=title, desc=meta.get("description", SITE_DESC), inner=inner, prefix="",
                   url=f"{SITE_URL}/{path.stem}.html"), encoding="utf-8")
        pages.append(path.stem)

    nf = '<article><h1>ページが見つかりません</h1><p>URLが変わったか、削除された可能性があります。</p><p><a href="/pocket-log/index.html">トップへ戻る</a></p></article>'
    (OUT / "404.html").write_text(layout(title="ページが見つかりません", desc=SITE_DESC, inner=nf,
                                         prefix="/pocket-log/", url=f"{SITE_URL}/404.html"), encoding="utf-8")

    # sitemap / RSS / robots
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/posts/{p['slug']}.html" for p in posts] + [f"{SITE_URL}/{s}.html" for s in pages]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    items = ""
    for p in posts[:20]:
        d = datetime.strptime(p["date"], "%Y-%m-%d").replace(hour=6, tzinfo=JST)
        u = f"{SITE_URL}/posts/{p['slug']}.html"
        items += (f"<item><title>{esc(p['title'])}</title><link>{u}</link><guid>{u}</guid>"
                  f"<pubDate>{format_datetime(d)}</pubDate><description>{esc(p['desc'])}</description></item>\n")
    (OUT / "feed.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{SITE_NAME}</title>'
        f"<link>{SITE_URL}/</link><description>{esc(SITE_DESC)}</description><language>ja</language>\n{items}</channel></rss>\n",
        encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")

    print(f"記事 {len(posts)} 本・固定ページ {len(pages)} 枚を docs/ に出力しました"
          + ("（下書き込みプレビュー）" if INCLUDE_DRAFTS else ""))


if __name__ == "__main__":
    main()
