"""新しい記事の雛形を content/ に作る。

使い方:  python new_post.py <英数字のスラッグ> "<タイトル>" [公開日 YYYY-MM-DD]
例:      python new_post.py convenience-sweets "コンビニの300円スイーツ、5つ食べ比べて本気で選んだ"
"""
import re
import sys
from datetime import datetime, timedelta, timezone

from build import POSTS_SRC

TEMPLATE = """---
title: {title}
date: {date}
description: 【要確認：検索結果やSNSに出る一行説明（60〜90字）】
emoji: 📝
pr: false
draft: true
---
【要確認：読者の「あるある」から入る1〜2行】

【要確認：この記事で何が分かるかを言い切る1行】

## 【要確認：見出しは「答え」にする】

【要確認：本文。1段落3行まで】

## やってみた結果

【体験メモ：いつ・何を・いくらで・どうだったか。良かった点と微妙だった点】

## 明日やること

【要確認：明日できることを1つだけ】
"""


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    slug, title = sys.argv[1], sys.argv[2]
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        sys.exit("スラッグは半角英小文字・数字・ハイフンのみ")
    date = sys.argv[3] if len(sys.argv) > 3 else (datetime.now(timezone(timedelta(hours=9)))).strftime("%Y-%m-%d")
    nums = [int(m.group(1)) for p in POSTS_SRC.glob("*.md") if (m := re.match(r"(\d{3})-", p.name))]
    path = POSTS_SRC / f"{max(nums, default=0) + 1:03d}-{slug}.md"
    path.write_text(TEMPLATE.format(title=title, date=date), encoding="utf-8")
    print(f"作成しました: {path}")


if __name__ == "__main__":
    main()
