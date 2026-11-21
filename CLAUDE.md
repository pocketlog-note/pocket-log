# pocket-log（ポケットログ）

## 目的
匿名で運営する試験的な記事サイト。テーマは「ポケット消費」＝「1000円以下で、今日がちょっと良くなる」。方針は [[strategy]]（plan/strategy.md）、記事の基準は [[article-guide]]（plan/article-guide.md）。

## ゴール／期限
- 試験運用。収益化は「公開→アクセスが付くか」を見てから判断（期限なし）。KPIは plan/strategy.md。

## 技術スタック
- Python 3.10（標準ライブラリのみ）。
- `build.py`: `content/*.md`（記事）＋`pages/*.md`（固定ページ）＋`style.css` → `docs/`。sitemap.xml・feed.xml・robots.txt・OGPも出す。
- `docs/` はビルド成果物なので git 管理外。公開は GitHub Actions（`.github/workflows/pages.yml`）が main への push 時と毎朝6時JSTにビルドして GitHub Pages へ。
- 公開URL: https://pocketlog-note.github.io/pocket-log/ （GitHub アカウント `pocketlog-note`、Pages の Source は「GitHub Actions」にする）

## よく使うコマンド
- 新しい記事: `python new_post.py <slug> "<タイトル>" [公開日]`
- 品質チェック: `python check.py`（公開対象にエラーがあると終了コード1。CIでも実行）
- 本番ビルド: `python build.py`
- 下書き込みプレビュー: `$env:INCLUDE_DRAFTS=1; python build.py` → プレビューは `.claude/launch.json` の `site-preview`（http://localhost:8123）
- ※ `python -I` だと check.py が build を import できないので付けない

## 公開されない条件（build.py）
- `draft: true`／`date` が未来（＝予約公開。毎朝のビルドで自動公開）／本文に `【体験メモ` か `【要確認` が残っている

## ルール・注意点
- **記事を書いたり直したりしたら、毎回 yomiyasu スキルで推敲する**（ユーザー指示 2026-11-21）。check.py の前に行う。
- 体験を捏造しない。【体験メモ】は必ず本人が書く。
- 価格・数値・商品名は出典か調べた日付を書く。
- アフィリエイトリンクがあれば `pr: true`（冒頭にPR表記）。check.py が検出する。
- 匿名性: git は `pocketlog-note` と noreply アドレスで設定済み（ローカル設定）。本名・個人メールを出さない。
- アカウント作成・push・公開・ドメイン購入はユーザーの指示があるときだけ。

## メモ・決定事項
- 2026-11-21 トレンド調査: 「ポケット消費」が年間キーワード（出典: https://www.fun-japan.jp/en/articles/14417 ）。テーマに採用。
- 2026-11-21 GitHub ユーザー名を匿名性のため `pocketlog-note` に変更。
- topics.txt が記事ネタのキュー。
- 公開リポジトリの定期実行（schedule）は、60日間リポジトリに動きがないと GitHub に止められる。
