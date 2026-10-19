"""取得範囲と元座標を保持する、不変のオフライン地形スナップショット。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from mcblueprint.model.block import BlockState
from mcblueprint.model.vec import AABB, Vec3

_AIR = BlockState.parse("minecraft:air")


@dataclass(frozen=True, slots=True)
class TerrainSnapshot:
    """宣言領域と通常 air 以外の元状態を不変に保持する。

    bounds は最小座標が [0, 0, 0] のローカル領域。offset はファイルの
    貼り付け基準に対する最小コーナーであり、絶対ワールド座標とは限らない。
    Minecraft 版は DataVersion が同梱版と完全一致するときだけ設定する。
    input_sha256 は圧縮を含む入力ファイル全体の SHA-256。
    """

    bounds: AABB
    offset: Vec3
    data_version: int | None
    minecraft_version: str | None
    input_sha256: str
    blocks: Mapping[Vec3, BlockState]

    def __post_init__(self) -> None:
        if self.bounds.min != Vec3(0, 0, 0):
            raise ValueError("地形のローカル領域は [0, 0, 0] から始まる必要があります")
        if any(not self.bounds.contains(pos) for pos in self.blocks):
            raise ValueError("地形のセルが宣言領域外にあります")
        object.__setattr__(self, "blocks", MappingProxyType(dict(self.blocks)))

    def get(self, pos: Vec3) -> BlockState | None:
        """ローカル位置の元状態を返す。取得済み air は状態、範囲外は None。"""
        if not self.bounds.contains(pos):
            return None
        return self.blocks.get(pos, _AIR)

    def to_source(self, pos: Vec3) -> Vec3:
        """領域内外を問わず、ローカル位置をファイルの貼り付け基準へ変換する。"""
        return pos + self.offset

    def to_local(self, pos: Vec3) -> Vec3:
        """ファイルの貼り付け基準の位置をローカル位置へ逆変換する。"""
        return pos - self.offset

    @property
    def source_bounds(self) -> AABB:
        """ファイルの貼り付け基準で表した宣言領域（両端を含む）。"""
        return AABB(self.to_source(self.bounds.min), self.to_source(self.bounds.max))
