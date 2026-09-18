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

## ドキュメント

- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 開発手順とルール
- [docs/FORMAT.md](docs/FORMAT.md) — Blueprint JSON の仕様
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — Operation の仕様
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 内部構成
- [AGENTS.md](AGENTS.md) — AI エージェント向けのルール

## ライセンス

[MIT](LICENSE)
