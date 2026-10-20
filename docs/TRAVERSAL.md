# 明示対象の通行検査

`traverse` は生成済み建築の明示した対象だけを `walk-straight-v1` モデルで検査する。既存 `validate` の成功は通行成功を意味せず、本検査の成功もMinecraftの完全な動作保証ではない。入力Blueprintと生成volumeは変更しない。

## CLI

```text
mcblueprint traverse FILE --building INDEX [--json] [--seed N] [--minecraft-version V]
mcblueprint traverse FILE --start X Y Z --end X Y Z [--json] [--seed N] [--minecraft-version V]
```

既存の `--max-dimension` も使える。最初に通常のSchema/意味検証を行い、指定seedで生成した最終volumeを検査する。後続操作で入口や階段が上書きされた場合も、元buildingの配置情報と最終volumeの差を検出する。

`--building INDEX` はトップレベル `operations` の0始まりindex。指定したbuildingの入口→一階到着点→次階到着点を順に検査する。translate / rotate / component等の内側を暗黙に探して選ばない。ネストされた対象は、変換後の足元座標を `--start` / `--end` で明示する。

終了コードは、全経路reachableが0、1経路以上blocked/unsupportedまたはBlueprint検証失敗が1、引数の組合せ・対象index・入出力エラーが2。`--start` / `--end` は対で指定し、building選択と併用しない。

## Python API

```python
from mcblueprint.model.vec import Vec3
from mcblueprint.traversal import check_route, check_building

result = check_route(volume, Vec3(3, 1, 1), Vec3(1, 5, 6), "1.21.11")
results = check_building(volume, building.layout, "1.21.11")
```

入力位置は立位の足元セルを表す整数 `Vec3`。床ブロックYが0なら足元Yは1。`building.layout.arrivals` と同じ規則。layoutとvolumeは同じ座標系で渡す。buildingの外側にあるネスト変換は、呼出し元が明示位置に反映する。

戻り値 `TraversalResult` は不変で、start / end / status / path / issuesを持つ。`path` は床・階段上端の足元セル列であり、階段セル内の半段位置は含まない。失敗時のpathは空。`issues` は座標・reason・元ブロック文字列（未設定はnull）を持つ不変の診断列。階段の進行を妨げる探索境界の原因を優先し、同じ優先度では終了点に近い順で返し、最小の修正箇所を保証しない。入力の未対応Minecraft版は `BlueprintError`。

## 移動モデル

- 四近傍の歩行、bottom / straight / 非waterloggedの既知階段、手で開閉できる既知の木・銅ドアを扱う。鉄ドア、装置制御、泳ぎ・飛行・ジャンプ・落下移動・はしご・這い/しゃがみ移動は扱わない。
- 足場の上面から2セル分の立位空間を要求する。完全ブロック間の高さ1段差をジャンプで越えない。階段への上昇は階段のfacingに沿うとき、階段からの下降はfacingと逆に進むときだけ許す。階段を横断しない。
- 階段の低い半段から高い半段までのセル内の連続昇降を、階段上端の足元セル一つで表す。各階段の真上2セルに加え、昇降時は低い側の足元Y+2のセルも確認する（半段へ移る途中も身体が低い列に残るため）。上階の開口が閉じていれば通行可能としない。
- 通常ドアは必要に応じて手動で開閉できると仮定する。lower / upperのid・facing・hinge・openの整合が必要。レッドストーン回路やドア開閉の時系列はシミュレーションしない。
- 完全ブロックは実装の `FULL_BLOCKS` の明示集合だけを扱う。基本石材、土・草、glass、鉄/金/diamond/emeraldブロック、同梱された13樹種のplanks等。`*_slab[type=double]` は完全ブロック扱い。名前が未確認のブロックを立方体と推測しない。
- half slab、逆さ/曲がり階段、waterlogged階段、フェンス・ガラス板・植物・液体など、対応集合外の衝突形状はunsupported。空気だけは未設定セルとair / cave_air / void_airを同一に扱う。
- 探索する足元位置は、volume.boundsのmin/maxへそれぞれ `[0,1,0]` を加えた有限AABB内に限定する（支持セルが元bounds内）。その外の開始/終了点はblocked。Blueprintの未設定セルをairとして扱うモデルであり、未取得の実ワールド地形を探索するAPIではない。

## 判定と原因

| status | 意味 |
|---|---|
| reachable | 既知形状だけからなる経路が見つかった。別の場所の未知形状は成功を妨げない |
| blocked | 対応モデル内で、足場/立位空間/階段方向等が成立しない |
| unsupported | 開始/終了または到達できる探索境界に未知形状があり、既知経路は見つからなかった。実機で不通と断定しない |

主なreasonは `missing_floor`（足場欠落）、`body_or_head_blocked`（足元/頭上の障害）、`stairs_direction_or_step`（対応階段方向なし・ジャンプが必要な段差）、`outside_search_bounds`（探索範囲外）、`unsupported_shape` / `unsupported_support`（未対応の身体空間/足場）、`unsupported_door_pair`（ドア上下の不整合）。探索境界の報告には、経路と無関係な壁や地面端も含まれる。

`--json` は `{ "movementModel": "walk-straight-v1", "results": [...] }` を出力する。resultsの各項目はstart/end（整数3要素）、status、path（整数3要素の配列）、issues（position/reason/block）の形式。Blueprintの入力項目やmetadataへ検査対象を保存しないため、Blueprint Schemaの変更はない。

代表fixtureと実機照合手順は `evaluation/artifacts/issue-106/` に保存する。実機照合の未実施を検査成功と扱わない。
