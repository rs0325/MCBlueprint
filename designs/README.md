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

## 既存の建築からプリセットを作る

ゲーム内で作った（または他の人の）建築を `.schem` / `.litematic` で保存し、`mcblueprint design` に渡すと、その様式を推定したプリセットが `designs/local/<name>.md` にできる。パーツ（窓枠、門、街灯など）を `--part` で一緒に渡すと `components/` の部品にも変換し、md から参照される。

```bash
mcblueprint design my_house.schem --name my_house --part my_window=window.schem --reference
```

- `## Palette` は役割（壁・柱・床・屋根・妻壁・土台）ごとの出現比率、`## 構造ルール` は壁の厚さ・階高・屋根の形（`roof` の指定）・窓の寸法と間隔・入口・照明の実測値。文章はひな形なので、用途と禁止事項を書き足し、間違った推定は直す。
- 円形や L 字の外形、ドーム・円錐・段積みの屋根（階段ブロック以外の屋根）も読み取り、`## 概要` と `## 構造ルール` に `tower` / `cylinder` / `sphere` / `circle` での作り方を書く。`## 参考図` は各階の平面図（間取り）と屋根の平面図、南・東の立面図。
- 壁の帯（階の境の別ブロックの列）、壁の外に張り出すトラップドアやハーフブロックの飾り、柱の間隔、木組みの梁は `## 構造ルール` の「壁の装飾」に、単発の飾りは `## 装飾` に書かれる。
- 窓や入口の周りに枠・窓台・アーチなどの装飾があれば、自動で `components/<name>_window.json` / `<name>_door.json` に切り出され、md の `## 部品` と `## 構造ルール` から参照される（外側が北を向くよう正規化。他の面は `rotation` 90 / 180 / 270）。
- `--reference` を付けると建物全体が `components/<name>_reference.json` になり、AI がそのまま配置したり `mcblueprint preview` で作りを確かめたりできる。
- 生成物は `mcblueprint check designs/` を通るが、推定なので必ず一度目を通す。

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
