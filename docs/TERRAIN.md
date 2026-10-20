# オフライン地形スナップショット

`importers.read_terrain(path) -> TerrainSnapshot` は `.schem`（Sponge v1 / v2 / v3）と単一領域 `.litematic` を地形として読み取る。Minecraft への接続、Blueprint との合成、回転・自動保護判定は行わない。入力ファイルは変更しない。

既存の `read_schematic()` は建築用 import の API で、従来どおり air を省いた可変の `BlockVolume` を返す。地形の取得範囲をその非 air セルの bounds から求めてはいけない。

## 保持する情報

`terrain.TerrainSnapshot` は frozen dataclass。`Vec3`・`AABB`・`BlockState` も不変で、`blocks` は渡された表のコピーを読み取り専用にして保持する。

| 項目 | 契約 |
|---|---|
| `bounds: AABB` | ファイルが宣言する全領域。最小コーナーは `[0, 0, 0]`、最大コーナーを含む。全 air や air の余白も含む |
| `blocks: Mapping[Vec3, BlockState]` | ローカル座標の元ブロック状態。通常の `minecraft:air` は省略する。`cave_air` / `void_air` とブロックの元プロパティは保持し、デフォルト補完や版変換は行わない |
| `offset: Vec3` | ファイルの貼り付け基準に対する宣言領域の最小コーナー |
| `source_bounds: AABB` | 貼り付け基準で表した取得領域。`bounds` の両端に offset を加えた値 |
| `data_version: int | None` | 入力の DataVersion（`.litematic` は MinecraftDataVersion）。未記載は `None` |
| `minecraft_version: str | None` | DataVersion が同梱版と完全一致するときの Minecraft 版。未知の版や未記載を近似しない |
| `input_sha256: str` | 読み取った入力ファイル全体（gzip 圧縮を含む）の SHA-256、小文字 16 進文字列 |

`.schem` の宣言寸法は `Width` / `Height` / `Length`、offset は `Offset`（未記載時はゼロ）を使う。`.litematic` の寸法は `abs(Size)`。負の Size を持つ軸では最小コーナーを `Position + Size + 1`、正の軸では `Position` とする。セルの格納順は両形式とも x → z → y。

offset は絶対ワールド座標を保証しない。ファイルの貼り付け基準に対する変換として扱い、実際にどこへ配置するかは呼び出し元が決める。

## 既知の air と未取得の照会

```python
from mcblueprint.importers import read_terrain
from mcblueprint.model.vec import Vec3

terrain = read_terrain("terrain.schem")
local = Vec3(0, 0, 0)
state = terrain.get(local)
# None は未取得。air を含む取得済みセルには BlockState が返る。
assert state is not None
assert terrain.to_local(terrain.to_source(local)) == local
```

`get(pos)` の引数はローカル座標。`bounds` 内で表に存在しない位置には `minecraft:air` を返し、領域外には `None` を返す。`blocks.get()` だけではこの区別ができないので、照会には `TerrainSnapshot.get()` を使う。

`to_source(local_pos)` は offset を加え、`to_local(source_pos)` は offset を引く。どちらも領域外の位置を変換でき、往復して元位置へ戻る。全 air の入力も取得済み領域として読み取れる。

## 拒否条件

不正な NBT、整数項目（寸法・座標・版・palette index）の小数や文字列、非正の宣言寸法、セル数や packed 配列長の不一致、ByteArray 以外の BlockData / Blocks.Data、途中で切れた・32 bit を超える varint、空・重複 index・負 index・構文不正の palette、palette にないセル index は `BlueprintError` とする。`.litematic` の複数領域は拒否する。

ブロック状態だけで保持できない非空の `BlockEntities` / `TileEntities` / `Entities` / `PendingBlockTicks` / `PendingFluidTicks` / `BlockTicks` / `FluidTicks` があるときも `BlueprintError` とし、対象（ルート、Schematic.Blocks、リージョン名など）と種類をメッセージに含める。空のリストは許容する。これらを通常の建築用 import に合わせて黙って省略してはいけない。

地形を読み取る API だけの追加であり、Blueprint JSON、Schema、CLI の既存形式は変更しない。
