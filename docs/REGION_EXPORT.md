# 完成後 volume の領域分割出力

```bash
mcblueprint build blueprints/house.json --region-size 32 16 32 -o output/house-regions
mcblueprint build blueprints/house.json --region-size 32 16 32 --format litematic -o output/house-litematic
```

`--region-size X Y Z` は各軸の正整数。指定時だけ全生成後の volume を非重複の矩形へ分割し、領域別ファイルと `manifest.json` を新規ディレクトリに出力する。既定先は `output/<入力ファイル名>-regions/`。`-o` は拡張子を含め常にディレクトリ名であり、出力形式は `--format`（既定 `schem`）で決まる。指定しない build のファイル名・形式・挙動は従来どおり。

対象は完成 volume の bounds（両端を含む）。最小コーナーから X/Y/Z 寸法で区切り、端の領域は残り寸法になる。未配置セルも既知の air として出力し、全 air の領域も省略しない。terrain がある場合は施工矩形全体を対象にし、施工外・未取得・保護範囲は成功扱いしない。ブロック状態は一括出力と同じで、地形の省略プロパティを補完しない。

生成・支持検査は全体に対して先に一度行う。これは生成メモリを減らす方式ではなく、並列生成・部分再生成も行わない。分割時は同じ完成 volume を保持し、領域ごとの exporter の作業領域を順番に解放する。

既存ディレクトリは上書きしない。一時ディレクトリを出力先の親に作り、全ファイルと manifest が揃ってから出力先を確定する。通常の出力例外では今回の一時成果だけを片付け、完成ディレクトリを残さない。プロセス強制終了や停電では親ディレクトリに `.出力名-*` の一時成果が残る場合がある。

## manifest v1

正本は `src/mcblueprint/schema/region-manifest.schema.json`、エディタ用コピーは `schema/region-manifest.schema.json`。これは出力のSchemaであり、Blueprint JSON の入力形式は変わらない。

| フィールド | 契約 |
| --- | --- |
| `formatVersion` | `1` |
| `format` / `minecraftVersion` | 全領域の形式 / 有効な Minecraft 版（CLI の上書き後） |
| `seed` | 生成に用いた有効な seed |
| `inputSha256` | 読み込んだ入力 JSON 生バイトの SHA-256（改行も含む） |
| `terrainSha256` | 保持する元地形 snapshot の入力ファイル全体 SHA-256。terrain なしは null |
| `origin` | 全領域で共通の Blueprint origin `[x,y,z]` |
| `bounds` | Blueprint 座標による全体の `min` / `max`（両端を含む） |
| `regionSize` | 指定した最大領域寸法 `[x,y,z]` |
| `regions` | Y、Z、X の順に最小座標を進めた領域配列 |
| `regions[].file` | manifest と同じディレクトリ内の相対ファイル名 |
| `regions[].bounds` | 各領域の Blueprint 座標範囲（両端を含む）。全体を重複・抜けなく被覆 |
| `regions[].offset` | `領域の min - 共通 origin`。各ファイル内の Offset / Position と一致 |
| `regions[].sha256` | 圧縮を含む成果ファイル全体の SHA-256 |

入力 hash は Blueprint 内で参照する部品ファイルの内容まで含む hash ではない。元地形はロード時の snapshot を再利用し、出力時に元ファイルを再読込しない。API `mcblueprint.region_export.export_regions` に完成 volume を渡す場合、呼出側が入力 JSON の SHA-256 と実際に生成した seed を渡す。

## 手動配置と再結合

全ファイルが共通の貼付基準を持つ。WorldEdit では同じ貼付基準を保って各ファイルをロード・貼付する。Litematica では全 schematic の配置 origin を同じワールド位置に設定する。ファイルが保持する offset が各領域を正しい位置に置くため、offset を重ねて手動加算しない。origin 自体は絶対ワールド座標とは限らない。

air による掘削を反映するには air を無視せず貼り付ける。manifest は自動適用コマンドを含まない。適用前に入力と成果の hash、各ファイルの宣言寸法と offset を確認する。

再結合の検証では、各ファイル内のローカル座標に `regions[].bounds.min` を加えた位置を使い、宣言寸法内の air を含む全セルを復元する。重複がないこと、全体 bounds を被覆すること、一括出力と全セルの状態が一致することを確認する。

## 実機確認手順

Minecraft Java 1.21.11 の新規ワールドで、同じ入力の一括出力と分割出力を離れた基準位置に配置する。屋根・地形の分割境界と端数領域、air による掘削箇所を撮影して比較する。貼付前に掘削位置へ確認用の固体ブロックを置き、air が反映されることも確認する。通路・入口を実際に歩いて境界で段差や障害が増えていないか確認する。自動テストの再結合成功だけで実機確認済みとは扱わない。


## 出力段階の比較測定

#96 の確定 commit `1d9cfafa3c4d2703894ad7a06bd309adcb0aeb1d` の fixture を外部から読み、同じ完成 volume を一括/分割出力した。Python 3.14.4 / Windows、schem、分割寸法 `[16,8,16]`。#96 の output 段階と同じく、各試行は別プロセスで全生成を終えてから測定し、時間は3回中央値、Python の追加確保量は別試行の tracemalloc peak を使う。生成時間・完成 volume 自体の保持量・プロセス全体 RSS は含まない。元記録と各 fixture の生バイト hash は [region-output.json](../benchmarks/region-output.json)。

| fixture | 一括 秒 | 分割 秒 | 一括 Python peak bytes | 分割 Python peak bytes |
| --- | ---: | ---: | ---: | ---: |
| sparse-256 | 0.02408 | 0.08757 | 2,533,629 | 2,539,237 |
| terrain-24 | 0.03200 | 0.06264 | 2,547,845 | 2,547,613 |
| air-24 | 0.04925 | 0.15204 | 2,566,328 | 2,551,659 |
| repeat-64 | 0.02305 | 0.11136 | 2,539,919 | 2,549,844 |

この規模では追加メモリの明確な削減は見られず、分割ファイル・hash・manifest の書込みで時間が増えている。生成全体のメモリが減ったことを示す測定ではない。条件を変えて再測定する場合は、#96 の fixture の絶対パスを次のスクリプトへ渡す。

```bash
python scripts/benchmark_regions.py <issue-96-worktree>/benchmarks/fixtures/terrain-24.json --region-size 16 8 16 --output output/region-measurement.json
```

#99 の確定 commit `9205679f9a119d1d38e975d8a509e98c269e26a9` で丘の元地形を別プロセス生成し、#102 で境界をまたぐ屋根と air 掘削を合成した確認も行った。全体 `[17,12,15]` を `[6,5,6]` で27領域へ分割し、schem / litematic の両方で、一括出力の3,060セルと air を含め全セル一致した。これはファイル検証であり、実機配置・撮影・通行確認は未実施。


## 後続の代表領域のユーザー確認（2026-10-20）

Minecraft Java Edition 1.21.11の確認用ワールドで、配布した `manual-review-20261020` のcross-002代表領域 `region-000020`／`region-000021` の同一anchorへの隣接配置と境界一致、`region-000047` の全air領域による消去、配置座標・offsetは正常とのユーザー報告を受けた。一括結果との比較・airを無視しない貼付の手順は配布READMEに従う。

比較画像ファイルは未提出で、AIによる新規撮影・提出画像の照合ではない。この確認は配布した代表領域に限られ、上記3,060セルfixtureの実機配置・撮影・通行未確認という記録を更新しない。
