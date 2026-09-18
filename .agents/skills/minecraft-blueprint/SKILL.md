---
name: minecraft-blueprint
description: Minecraft の建築を Blueprint JSON で設計し、mcblueprint CLI で検証して .schem を生成する。家・塔・城・壁・部屋など Minecraft の構造物を作る／直す依頼、または .schem / schematic / Blueprint に関する依頼で使う。
---

# Minecraft Blueprint

Minecraft の建築は **Blueprint JSON** で記述し、`mcblueprint` CLI で `.schem` に変換する。
`.schem` や `.litematic` を直接生成・編集してはならない。

## ワークフロー

1. **要求を整理する**: 用途、寸法（幅・奥行き・高さ）、階数、材質、雰囲気、必ず入れる要素（入口・窓・屋根・階段など）を確認する。不明な点は常識的な既定値を置き、Blueprint の `description` に書く。
2. **Blueprint を書く**: `blueprints/<name>.json` に作成する（`name` は英小文字とアンダースコア）。書き方は [references/format.md](references/format.md) と [references/operations.md](references/operations.md)、建築のコツは [references/building-guidelines.md](references/building-guidelines.md) を読む。完全な仕様は `docs/FORMAT.md` と `docs/OPERATIONS.md`。
3. **検証する**:
   ```bash
   mcblueprint validate blueprints/<name>.json
   ```
   `ERROR` が出たら、表示された JSON パス（例 `operations[4].radius`）の箇所を直して再実行する。`Blueprint is valid.` になるまで build に進まない。
4. **生成する**:
   ```bash
   mcblueprint build blueprints/<name>.json
   ```
   `output/<name>.schem` が生成される。表示される `Bounds` と `Blocks` が要求どおりか確認し、ずれていれば Blueprint を直して再度 validate → build する。
5. **報告する**: 出力パス、サイズ（`Bounds`）、ブロック数、主な構成（階数・材質など）、貼り付け方（WorldEdit で `//schem load <name>` → `//paste`。`origin` の座標がプレイヤー位置に一致する）を伝える。

## 守ること

- Blueprint はブロック配置を宣言するデータである。コマンド、スクリプト、シェル文字列を埋め込まない。
- 1 ブロックずつ `set` を並べるのではなく、`fill` / `wall` / `box` / `cylinder` / `repeat` / `mirror` などの高レベルな Operation で表現する。
- Operation は配列順に適用され、後のものが前を上書きする。「大きく作ってから `minecraft:air` でくり抜く」「壁を作ってから窓を空ける」の順で書く。
- ブロック ID とプロパティは対象 Minecraft バージョンに存在するものだけを使う。validate が `Unknown block id.` や `Invalid value` を出したら修正する。
- 向きを持つブロック（階段・ドア・原木など）はプロパティで向きを指定する。ガラス板・フェンス・壁は接続プロパティ（`east=true` など）を明示する。
- 既存の Blueprint を修正する依頼では、該当する Operation だけを変更し、`seed` を変えない（他の部分の Palette の見た目が変わる）。
- `mcblueprint` が見つからない場合は `pip install -e .` を案内する。自分で `.schem` を書こうとしない。
