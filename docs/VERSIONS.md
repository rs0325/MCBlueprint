# 対応 Minecraft バージョン

`mcblueprint versions` で同梱ブロックデータの一覧を表示できる。`minecraftVersion` にはこの一覧のバージョンだけを指定できる（それ以外はエラー）。Blueprint を書き換えずに別のバージョンで検証・出力するには `--minecraft-version` を使う。

```bash
mcblueprint versions
mcblueprint validate examples/house.json --minecraft-version 26.3
mcblueprint build examples/house.json --minecraft-version 26.3
```

| バージョン | DataVersion | ブロック数 | 備考 |
|---|---|---|---|
| `1.21.11` | 4671 | 1166 | 2025-12 リリース。1.21 系の最終 |
| `26.1.2` | 4790 | 1168 | 2026-04。年ベース採番（`26.x`）の最初のライン |
| `26.2` | 4903 | 1196 | 2026-06 |
| `26.3` | 5023 | 1286 | 2026-09。現時点の最新 |

DataVersion は `.schem` / `.litematic` に書き込まれる値で、`import` 時にファイルのバージョンを判定するのにも使う。同梱データにない DataVersion のファイルは、それより新しくない最も近いバージョン（どれより古ければ最も古いバージョン）で読み込み、その旨を表示する。

## バージョン間の差分

ブロックの削除はなく、新しいバージョンは古いバージョンのブロックをすべて含む（`tests/test_blockdata.py` で検証）。古いバージョン向けに書いた Blueprint は、そのまま新しいバージョンでも検証が通る。

### 1.21.11 → 26.1.2

- 追加: `golden_dandelion`, `potted_golden_dandelion`
- 変更: 看板（`*_sign`, `*_hanging_sign`）と旗（`*_banner`）の `rotation` のデフォルトが `0` から `8` に変わった（`rotation` を書かないと向きが変わる。明示すれば影響なし）

### 26.1.2 → 26.2

- 追加: 辰砂（`cinnabar`）と硫黄（`sulfur`）系のブロック 28 種（`*_bricks`, `polished_*`, それぞれの `_slab` / `_stairs` / `_wall`、`sulfur_spike`, `potent_sulfur`）

### 26.2 → 26.3

- 追加: 羊毛とコンクリートの `_slab` / `_stairs`（16 色 × 2 × 2 = 64 種）、ポプラ（`poplar_*`: 原木・板材・ドア・フェンス・看板・葉（`orange` / `red` / `yellow_poplar_leaves`）など）、`red_shrub`, `shelf_mushroom`, `straw_bed`, `poplar_shelf`

## バージョンの追加

[DEVELOPMENT.md](DEVELOPMENT.md#ブロックデータの再生成) の手順で `scripts/generate_block_data.py` を実行し、生成された `src/mcblueprint/data/blocks/<version>.json` と `versions.json` をコミットする。`26.x` のサーバーは Java 25 が必要なので `--java` で実行ファイルを指定する。追加したら本書の表と差分を更新する。
