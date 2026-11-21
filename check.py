"""記事の品質チェック（plan/article-guide.md の機械で見られる部分）。

使い方:  python check.py            全記事をチェック
        python check.py 003        ファイル名に 003 を含む記事だけ

公開対象（draft でない）記事に「エラー」があると終了コード 1。下書きは警告のみ。
自動デプロイの前にも実行され、エラーがあると公開を止める。
"""
import re
import sys
from datetime import datetime

from build import AFFILIATE_HOSTS, PLACEHOLDER, POSTS_SRC, is_true, parse

BANNED = ["いかがでしたか", "と言えるでしょう", "が重要です", "について解説します", "してみてはいかがでしょうか",
          "まとめると", "結論から言うと"]
SENSITIVE = [r"[\w.+-]+@[\w-]+\.[\w.]+", r"\d{2,4}-\d{2,4}-\d{3,4}"]  # メールアドレス・電話番号らしきもの


def check(path):
    meta, body = parse(path)
    errors, warns = [], []
    title = meta.get("title", "")
    draft = is_true(meta.get("draft"))

    if not title:
        errors.append("title がない")
    elif not (20 <= len(title) <= 40):
        warns.append(f"タイトルが {len(title)} 文字（目安 20〜40）")
    if title and not re.search(r"[0-9０-９一二三四五六七八九十百千万]", title):
        warns.append("タイトルに数字がない（具体的な数字があると目を引きやすい）")
    if not meta.get("description"):
        errors.append("description がない（検索結果・SNSに出る説明文）")
    try:
        datetime.strptime(meta.get("date", ""), "%Y-%m-%d")
    except ValueError:
        errors.append("date が YYYY-MM-DD 形式でない")

    if body.count("\n## ") + body.startswith("## ") < 2:
        warns.append("見出し（## ）が2つ未満")
    head = "".join(p for p in body.strip().split("\n\n")[:3])
    if len(head) > 220:
        warns.append("書き出し3段落が長い（最初の3行で何が得られるかを伝える）")
    for para in body.split("\n\n"):
        text = para.strip()
        if text and not text.startswith(("-", "#", ">", "1.")) and len(text) > 150:
            warns.append(f"長い段落（{len(text)}字）: {text[:20]}…")
    for w in BANNED:
        if w in body:
            warns.append(f"定型句「{w}」がある（AIっぽく見える）")
    if body.count("**") // 2 > 12:
        warns.append("太字が多すぎる")

    links = re.findall(r"\]\((https?://[^)\s]+)\)", body)
    if any(h in u for u in links for h in AFFILIATE_HOSTS) and not is_true(meta.get("pr")):
        errors.append("アフィリエイトリンクがあるのに pr: true がない（PR表記が必要）")
    if PLACEHOLDER.search(body):
        (warns if draft else errors).append("未記入の【体験メモ】【要確認】がある")
    if "体験" not in body and "やってみ" not in body and "試し" not in body:
        warns.append("体験の記述が見当たらない")
    for pat in SENSITIVE:
        if re.search(pat, body):
            errors.append("メールアドレスや電話番号らしき文字列がある（匿名性）")

    if draft:  # 下書きのエラーは警告扱い
        warns = [f"(公開時エラー) {e}" for e in errors] + warns
        errors = []
    return draft, errors, warns


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    failed = False
    for path in sorted(POSTS_SRC.glob("*.md")):
        if key not in path.name:
            continue
        draft, errors, warns = check(path)
        state = "下書き" if draft else "公開対象"
        mark = "NG" if errors else ("要確認" if warns else "OK")
        print(f"[{mark}] {path.name}（{state}）")
        for e in errors:
            print(f"   エラー: {e}")
        for w in warns:
            print(f"   警告  : {w}")
        failed |= bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
