# 座標範囲のプレビュー

接合部、入口、階段などを詳しく見るとき、全体画像のあとに必要な範囲だけを描く。Blueprint 自体と生成処理は変更しない。自動検出・自動カメラ選択・部分生成は行わない。

## 指定と出力

```bash
mcblueprint preview blueprints/house.json --from 3 0 -1 --to 7 4 2 --views isometric,north --grid 1
mcblueprint preview blueprints/house.json --from 3 0 -1 --to 7 4 2 --layers all --grid 1
```

`--from X Y Z` と `--to X Y Z` は両方必要。整数の最小・最大座標を指定し、両端のブロックを含む。負座標もそのまま使える。座標は元の Blueprint に書く座標であり、`origin` を引いた座標や Minecraft に貼り付けた先の座標ではない。`origin` は従来どおり赤い印の位置だけに使う。

先に全 Blueprint を検証・生成してから、生成済み volume の範囲と要求範囲の交差を描く。要求範囲のうち元範囲の外側はクリップされる。交差内の空セルは余白として維持し、元座標を移動しない。同じ scale/grid なら各 view の画像寸法は全体画像以下となり、巨大な範囲指定で新たな無制限の余白を確保しない。

- 通常 view: `<stem>-region-top.png`、`-region-north.png`、`-region-isometric.png` など。
- 水平断面: `<stem>-region-y<NN>.png`。`--layers all` は実描画範囲の Y 全段。`--layer` と `--layers` の明示値は同範囲内のみ許可する。
- 座標記録: `<stem>-region.json`。PNG の `mcblueprint` 情報にも同じ各画像の記録を保存する。

指定なしのファイル名・ビュー・描画は従来どおり。全体画像は部分画像に上書きされない。別の選択を同じ出力先へ連続して出す場合、`-region-` の同名画像は上書きされるので、比較を保全するなら `-o` を分ける。空の選択や範囲エラーでは新しい画像・JSON を作らず終了コード 2 となる。以前の出力先にあるファイルは削除しない。

`--from` が `--to` より大きい軸、完全に範囲外の選択、選択内に可視ブロックがない場合はエラー。空気しかない選択も同じ。選択全体に可視ブロックがあっても、特定の断面に何もない段は通常の空の断面として描く。

## 切口の意味

全体図と同じ入力・seed・view と併せて確認する。範囲外を外してから投影するため、全体 PNG を単にトリミングした画像とは異なる。

| view | 部分図で見えるもの |
|---|---|
| top | 選択 Y 内で最上段のブロック。選択より上の屋根や天井は遮蔽しない。明暗の高さ基準も実描画 Y 範囲 |
| north/south/east/west | 選択内でその方向に最も近いブロック。範囲外の外壁は遮蔽せず、切口の内部が見える |
| isometric | 選択内の形状の上面・+x面・+z面。隣接ブロックが範囲外なら面を露出させる。stairs/slab の形状は #100 と同じ |
| 水平断面 | 選択 X/Z と指定 Y。直下段の ghost はその段も選択 Y 内にある場合だけ表示 |

切断面専用の材質や斜線は付けず、残ったブロックの形状の露出面として描く。削除された外側の遮蔽を再現しない。図で内部が見えることは、実物に開口がある・通行できることの証拠にはならない。`--grid` は元座標を表示し、北/東立面の左右反転と isometric の origin 印も既存どおり。isometric は座標罫線を持たないため JSON の範囲と併用する。

## API と座標記録

```python
from mcblueprint.model import AABB, Vec3
from mcblueprint.preview import Options, render, write_previews

options = Options(
    scale=16, grid=1, origin=Vec3(5, 1, 4),
    region=AABB(Vec3(3, 0, -1), Vec3(7, 4, 2)),
    source="blueprints/house.json",
)
image = render(volume, "isometric", options=options)
paths = write_previews(volume, out_dir, "house", views=["isometric"], options=options)
```

`render` / `render_layer` は元 volume を変更せず、Pillow Image を返す。`Options.source` は呼出元が分かる元入力の参照文字列で、CLI は入力の絶対パスを設定する。API で未指定なら `null`。選択情報は `image.info["mcblueprint"]` の JSON 文字列に入る。`write_previews` が PNG 情報と JSON ファイルに保存し、PNG 群のあとに JSON のパスを返す。画像を API から直接保存する場合、Pillow の通常の `save` だけではこの PNG 情報の保存を保証しないため、記録が必要なら `write_previews` を使う。

JSON は画像ごとのレコードの配列。各レコードの契約は次のとおり。

| キー | 内容 |
|---|---|
| image | 画像のファイル名（JSON ファイルだけに付く） |
| sourceBlueprint | 元入力の参照文字列、API で未指定なら null |
| coordinateSystem | `blueprint`。全座標は元 Blueprint 座標 |
| origin | Blueprint 原点の印の座標、未指定なら null |
| sourceBounds | 生成済み全体の両端包含 `min` / `max` 配列 |
| requestedBounds | 要求した両端包含 `min` / `max` 配列 |
| renderedBounds | 生成範囲との交差。実際の画枠の両端包含 `min` / `max` 配列 |
| view / layer | view 名。断面は view=`layer`、layer=Y。他の view は layer=null |
| outsideOcclusion | `removed`。外側の遮蔽を外す |
| cutFaces | `exposed-block-geometry`。残ったブロックの露出面 |
| layerGhost | `within-selection`。ghost も選択内のみ |

## 固定した確認課題

`tests/data/preview_regions.json` の入口・接合部・室内階段にある金ブロックを修正箇所として、同じ入力の全体図と部分図を比較する。入口は `--from -5 0 5 --to -2 3 7`、接合部は `--from -1 0 1 --to 1 3 4`、階段は `--from 1 0 0 --to 4 5 5`。全体図と部分図の生成では seed=0、view=isometric、scale=16、grid=1 を共通にし、必要な立面・水平断面を追加する。

画像の寸法・ファイル容量・コマンド呼出数・処理時間は計測可能だが、モデルの画像込み token 消費や修正品質をそこから推定しない。Issue #97 の固定記録に連携する際は入力/画像 hash、比較条件、実測値、未取得値の理由を残す。実機比較・人間の修正品質評価・モデル usage は未実施または未取得であり、生成画像の確認で代替しない。
