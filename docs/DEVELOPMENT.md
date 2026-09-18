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
