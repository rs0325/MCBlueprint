# デザインプリセット

建築の様式・材質・寸法規則をファイルにまとめたもの。AI に「`medieval` で塔を作って」のようにプリセット名で依頼すると、AI は該当ファイルを読んでから Blueprint を書く。毎回長い指示を書かずに済み、複数の建物で様式をそろえられる。

## 同梱プリセット

| 名前 | ファイル | 様式 |
|---|---|---|
| `medieval` | [medieval.md](medieval.md) | 中世ヨーロッパ風（石と木、切妻屋根、塔） |
| `japanese` | [japanese.md](japanese.md) | 和風（漆喰と濃い木、瓦屋根、縁側） |
| `modern` | [modern.md](modern.md) | モダン（コンクリート・ガラス、陸屋根） |

## 使い方

依頼文にプリセット名または様式名を入れる。

```text
medieval で直径 15、高さ 30 の塔を作って
和風の平屋を 13 × 9 で作って（japanese プリセット）
```

AI は `designs/<name>.md` を読み、Palette をそのまま `palettes` に貼り、構造ルールに従って Operation を書く。使ったプリセット名は Blueprint の `metadata.design` に記録する。

## 自分のプリセットを作る

1. `designs/<name>.md` を作る（英小文字とアンダースコア）。リポジトリを共有しない個人用は `designs/local/` に置くと git 管理外になる。
   書いたら `mcblueprint check designs/` で Palette と Operation の例のブロック ID・プロパティを検証する（```json ブロックのうち `palettes` を持つもの、`type` を持つ Operation、`operations` を持つ抜粋が対象。既定では最も古い同梱バージョンで検証するので、新しいバージョンのブロックを使うなら `--minecraft-version` を付ける）。
2. 次の見出しを使う（順序は自由。不要な節は省略してよい）。

```markdown
# <名前>

## 概要
様式の説明と向いている建物。

## Palette
そのまま `palettes` に貼れる JSON。壁・床・屋根・土台・アクセントを分ける。

## 構造ルール
壁の厚さ、階高、屋根の形（`roof` の style）、窓・入口の作り方、柱の有無。

## 寸法の目安
建物種別ごとの幅・奥行き・高さ。

## 装飾
ランタン・鉢植え・旗など、置く場所と支持先。

## 禁止事項
使わないブロック、崩れやすい構成。
```

3. Palette のブロック ID は `mcblueprint validate` が通るものだけを使う（`tests/test_designs.py` が同梱プリセットの JSON を検証する）。
4. 迷ったら [medieval.md](medieval.md) を写して書き換える。
