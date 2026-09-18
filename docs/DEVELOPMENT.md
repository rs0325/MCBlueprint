# 開発ガイド

## セットアップ

Python 3.11 以上が必要です。

```bash
python -m venv .venv
```

```bash
pip install -e ".[dev]"
```

## 日常のコマンド

```bash
ruff check .
```

```bash
pytest
```

```bash
mcblueprint --version
```

## ディレクトリ構成

```text
src/mcblueprint/   パッケージ本体（CLI, Loader, Validator, Generator, Exporter）
schema/            Blueprint JSON Schema
docs/              仕様書・ガイド（仕様の正本）
examples/          サンプル Blueprint
blueprints/        利用者・AI が作成する Blueprint（作業用）
output/            生成された .schem（git 管理外）
tests/             pytest
.agents/skills/    Codex 用 Skill（正本）
.claude/skills/    Claude Code 用 Skill（.agents 側のコピー）
```

## JSON Schema の更新

Blueprint JSON Schema の正本は `src/mcblueprint/schema/blueprint.schema.json`（パッケージに同梱され、実行時に `mcblueprint.schema.load_schema()` で読む）。
リポジトリ直下の `schema/blueprint.schema.json` はエディタや外部ツール向けのコピーで、`tests/test_schema.py` が両者の一致を検証する。変更時は両方を更新する。

## ブロックデータの再生成

ブロック ID・プロパティ・デフォルト状態の検証に使うデータは `src/mcblueprint/data/blocks/<version>.json`、DataVersion は `src/mcblueprint/data/versions.json` にあり、どちらもコミット済み（利用者に Java は不要）。
新しい Minecraft バージョンを追加するときは Java 21 以上を用意し、次を実行して生成物をコミットする。

```bash
python scripts/generate_block_data.py --version 1.21.11 --download
```

対応バージョンの一覧は `src/mcblueprint/data/versions.json` が正となる。Minecraft Java Edition は 2026 年から `26.3` のような年ベースの採番へ移行しているが、スクリプトは Mojang の公式マニフェストに載っているバージョン ID をそのまま受け付けるため、`--version 26.3` のように指定すれば同じ手順で追加できる。

`--download` は Mojang の公式マニフェストから `server.jar` を `generated/` に取得し SHA-1 を検証する。手元の `server.jar` を使う場合は `--server-jar <path>` を指定する。スクリプトは公式データジェネレータ（`--reports`）を実行し、`reports/blocks.json` を圧縮形式へ変換する。`generated/` は git 管理外。

## 開発フロー

1. 対象の Issue を確認し、範囲を把握する。
2. `main` から `feature/issue-<番号>` ブランチを作成する。
3. 実装とテストを追加する。仕様変更を伴う場合は `docs/`、`schema/`、Skill の references も同じ変更に含める。
4. `ruff check .` と `pytest` を通す。
5. `main` へ Pull Request を作成する。

## コミットメッセージ

日本語で、以下の形式にする。

```text
type: 変更内容の概要

- 具体的な変更内容
- 具体的な変更内容
```

`type` は `feat` / `fix` / `refactor` / `docs` / `test` / `build` / `chore` から、変更の主目的に合うものを 1 つ選ぶ。

## Pull Request

タイトルはコミットと同じ `type: 概要` 形式。本文は以下の見出しを使う。

```markdown
## 概要

## 変更内容

## 検証

- [ ] 関連テスト
- [ ] ビルド
- [ ] 必要な実行確認

## 関連Issue

Closes #<番号>
```

検証欄には実際に行った確認だけを `[x]` にする。

## CI

GitHub Actions（`.github/workflows/ci.yml`）が push / PR ごとに Python 3.11 と 3.12 で `ruff check .` と `pytest` を実行する。
