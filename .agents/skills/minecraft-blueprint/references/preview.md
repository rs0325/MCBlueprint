# 部分プレビュー

正本は `docs/PREVIEW_REGIONS.md`。全体図で位置を確認してから、接合・入口・階段など必要な部分だけを描く。

```bash
mcblueprint preview blueprints/house.json --from 3 0 -1 --to 7 4 2 --views isometric,north --grid 1
```

両端を含む元の Blueprint 座標を指定する。`--layer` / `--layers` は選択 Y 範囲内だけ。全生成後の描画限定であり、生成使用量の削減を意味しない。`-region-` 画像と `-region.json` の要求/実描画範囲・元入力参照を全体画像と照合する。範囲外の壁や天井は遮蔽しないため、切口を実際の外観や通行可能性と混同しない。可視ブロックのない範囲はエラーになる。
