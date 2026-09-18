# MCBlueprint

Codex や Claude Code などの AI コーディングエージェントに Minecraft の建築を設計させ、WorldEdit 等で読み込める `.schem` を生成するツールキットです。

AI に NBT や Schematic 形式を直接書かせるのではなく、人間も編集できる中間形式 **Blueprint JSON** を定義し、検証と変換はツール側が担当します。

```text
ユーザーの自然言語
        ↓
Codex / Claude Code
        ↓
Blueprint JSON  (blueprints/*.json)
        ↓
mcblueprint validate
        ↓
mcblueprint build
        ↓
.schem  (output/*.schem)
```

## 状態

開発中（v0.1 に向けて実装中）。進捗は [Issues](https://github.com/rs0325/MCBlueprint/issues) を参照してください。

## 要件

- Python 3.11 以上

## 対応 Minecraft バージョン

- Java Edition 1.21.11（ブロックデータを同梱）

Minecraft は 2026 年から `26.3` のような年ベースのバージョン採番に移行しています。他のバージョンを対象にする場合は、[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) の手順でブロックデータを追加してください。

## ドキュメント

- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 開発手順とルール
- [docs/FORMAT.md](docs/FORMAT.md) — Blueprint JSON の仕様
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — Operation の仕様
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 内部構成
- [docs/AI_GUIDE.md](docs/AI_GUIDE.md) — AI エージェントからの利用手順
- [AGENTS.md](AGENTS.md) — AI エージェント向けのルール

## ライセンス

[MIT](LICENSE)
