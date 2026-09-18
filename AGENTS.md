# MCBlueprint

このリポジトリは、AI コーディングエージェントが Minecraft の建築設計データ（Blueprint JSON）を作成し、`.schem` へ変換するためのツールキットです。

このファイルには全体ルールだけを書き、詳細仕様は `docs/` に置く。仕様を本ファイルや Skill へ複製しない。

## 建築を依頼されたとき（ツールキットの利用）

- 建築は必ず Blueprint JSON（`blueprints/<name>.json`）で作成する。`.schem` や `.litematic` を直接生成・編集しない。
- `minecraft-blueprint` skill（Codex: `.agents/skills/`、Claude Code: `.claude/skills/`）に従い、Blueprint 作成 → `mcblueprint validate` → エラー修正 → `mcblueprint build` の順で進める。手順の全体は `docs/AI_GUIDE.md`。
- 検証エラーが残った状態で build しない。
- Blueprint はブロック配置を宣言するデータであり、コマンドやスクリプトを埋め込まない。
- 仕様は `docs/FORMAT.md` と `docs/OPERATIONS.md` を正とする。

## 開発を依頼されたとき（ツールキット自体の変更）

- Issue 駆動で進める。Issue に書かれた範囲を超える変更をしない。
- ブランチは `feature/issue-<番号>`、`main` へ Pull Request を作る。
- コミットメッセージと PR は日本語で `type: 概要` 形式にする。
- 変更後は `ruff check .` と `pytest` を実行し、結果を報告する。実行していない検証を成功したと書かない。
- 仕様変更を伴う場合は `docs/` と `schema/`、Skill の references を同じ変更で更新する。
- 詳細は `docs/DEVELOPMENT.md` を参照する。
