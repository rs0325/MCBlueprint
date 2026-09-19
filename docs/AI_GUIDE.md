# AI エージェント向けガイド

Codex、Claude Code などのコーディングエージェントから MCBlueprint を使って Minecraft の建築を生成する手順。
エージェントに依存しない共通の流れをここに書き、各エージェント固有の設定は Skill / 設定ファイルに置く。

## 役割分担

```text
自然言語の依頼
      ↓
AI エージェント        …… 建築を考え、Blueprint JSON を書く
      ↓
blueprints/<name>.json
      ↓
mcblueprint validate   …… Schema・ブロック ID・範囲を検証し、全エラーを報告
      ↓
mcblueprint build      …… Operation を実行し .schem を書き出す
      ↓
output/<name>.schem    …… WorldEdit / Litematica で Minecraft へ貼り付け
```

AI は Minecraft のバイナリ形式（NBT / Schematic）を扱わない。`.schem` を直接生成・編集させない。

## 基本ワークフロー

1. 要求を整理する（用途、寸法、階数、材質、必須要素）。
2. `blueprints/<name>.json` に Blueprint を書く。仕様は [FORMAT.md](FORMAT.md) と [OPERATIONS.md](OPERATIONS.md)。
3. `mcblueprint validate blueprints/<name>.json` を実行する。
4. エラーがあれば Blueprint を修正して 3 に戻る。
5. `mcblueprint inspect blueprints/<name>.json` で範囲・サイズが要求と合うか確認する（必要なら `mcblueprint stats` でブロック構成も見る）。画像を読めるエージェントは `mcblueprint preview blueprints/<name>.json` で `preview/<name>-isometric.png` などを生成して形を確認し、内部は `--layers all --grid 5` の水平断面で確認する。合わなければ 2 に戻る。
6. `mcblueprint build blueprints/<name>.json` を実行し、`output/<name>.schem` を得る。
7. 出力パス、サイズ、主な構成、貼り付け方（`//schem load <name>` → `//paste`）を報告する。

## エラー出力の読み方

```text
ERROR operations[4] (cylinder)
  'radius' must be >= 1.
  Current value: -5

ERROR operations[7].operations[1].block (set)
  Unknown block id.
  Current value: minecraft:stone_brick

2 errors found.
```

- 1 行目: JSON パス（`operations` 配列の index。ネストは `operations[7].operations[1]`）と Operation の `type`
- 2 行目: 原因（英語 1 文）
- 3 行目: 問題の値（あれば）

検証は「Schema → 意味（ブロック ID・Palette 参照など）→ 範囲（size・最大寸法）」の順に行い、ある段階でエラーがあると後の段階は省略する。1 回の修正で全部直らないことがあるので、`Blueprint is valid.` になるまで繰り返す。

終了コードは `0` 正常 / `1` 検証エラー / `2` 引数・入出力エラー（ファイル未存在、JSON 構文エラー）。

### 警告（支持チェック）

`validate` と `build` は、生成結果の中でランタン・松明・壁付けブロック・ドア・草花などが支持のない位置にあると **警告** を出す（貼り付け時に落ちて消えるため）。

```text
Blueprint is valid.

WARNING [3, 5, 2] minecraft:lantern[hanging=true]
  Needs a solid block above; found minecraft:oak_slab[type=top].

1 warning found.
```

- 座標は Blueprint 座標。`found` は支持先にあったブロック。
- 警告があっても終了コードは `0` で `.schem` は書き出されるが、AI は警告をすべて解消してから報告する。`--strict` を付けると警告で終了コード `1` になり、`build` は書き出さない。
- チェック対象は代表的なブロックに限られる。警告がないことは物理的に正しいことの保証ではない。

## デザインプリセット

`designs/` には様式ごとの Palette・構造ルール・寸法・装飾をまとめたプリセット（`medieval`, `japanese`, `modern`）がある。依頼にプリセット名や様式名を入れると、AI はそのファイルを読んでから Blueprint を書くため、毎回長い指示を書かずに済み、複数の建物で様式をそろえられる。

```text
medieval で直径 15、高さ 30 の塔を作って
```

- 使ったプリセットは Blueprint の `metadata.design` に記録される。
- 自分のプリセットは `designs/<name>.md` に置く（書き方は `designs/README.md`）。リポジトリで共有しない個人用は `designs/local/`（git 管理外）。
- `tests/test_designs.py` が同梱プリセットの Palette を検証する。

## 既存の建物を元にする・修正を比較する

- 依頼者が `.schem` / `.litematic` を持っている場合は `mcblueprint import <file>` で `blueprints/<name>.json`（`fill` / `set` の列）に変換してから編集する。高レベル Operation には復元されないので、大きく作り替えるなら新しく書いたほうが早い。
- 修正の前後で意図しない変更がないかは `mcblueprint diff old.json new.json` で確認する（`origin` 基準で比較し、air の有無やプロパティの省略は無視される）。

## Skill の配置

| エージェント | 場所 | 備考 |
|---|---|---|
| Codex | `.agents/skills/minecraft-blueprint/` | 正本 |
| Claude Code | `.claude/skills/minecraft-blueprint/` | `.agents` 側の複製。`tests/test_skill_sync.py` が一致を検証 |

Skill の内容は共通で、`SKILL.md`（ワークフローと守ること）と `references/`（Blueprint JSON 早見表、Operation 早見表、建築のコツ）からなる。Skill を更新するときは `.agents` 側を編集し、`.claude` 側へコピーする。

```bash
cp -r .agents/skills/minecraft-blueprint/. .claude/skills/minecraft-blueprint/
```

`AGENTS.md`（Codex）と `CLAUDE.md`（Claude Code。`AGENTS.md` に準じる旨のみ）には全体ルールだけを書き、仕様は複製しない。

## 他のエージェントで使う

Gemini CLI、Cursor、ローカル LLM などでも、次を守れば同じ Core を使える。

1. `docs/FORMAT.md` と `docs/OPERATIONS.md`（または Skill の `references/`）をコンテキストに渡す。
2. Blueprint JSON を `blueprints/` に書かせる。
3. `mcblueprint validate` → `mcblueprint build` を実行させ、エラー出力を読ませて修正させる。

## セキュリティ

- Blueprint は宣言的なデータであり、コマンドやスクリプトを実行する手段を持たない。未知のキーは検証で拒否される。
- エージェントが実行するコマンドは `mcblueprint validate` / `inspect` / `stats` / `preview` / `build`（既存 Schematic を元にするときは `import`、修正前後の比較は `diff`）で足りる。Blueprint に任意のコマンド文字列を書かせない。
