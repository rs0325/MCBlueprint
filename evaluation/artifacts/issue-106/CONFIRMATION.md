# 通行検査と実機の照合

Minecraft Java 1.21.11の新規確認用ワールドへの配置・撮影・歩行が許可されている。実装担当は実機を操作していない。画面取得の復旧後、専任担当が以下を確認する。未実施状態を自動検査の成功で置き換えない。

基本形状は#101の二階建て7×8、階高4、入口足元 `[3,1,0]`、一階到着足元 `[3,1,1]`、二階到着足元 `[1,5,6]`。JSONのトップレベルoperations[1]がbuilding。各fixtureはvalidate→build後、`mcblueprint traverse FILE --building 1 --json` を実行済み。全体validateは通行成功を意味しないことを異常対照でも確認している。

| fixture | 自動検査の期待/結果 | 実機で照合する箇所 |
|---|---|---|
| normal | reachable | ドアを開けて入場し、一階から二階へ登り、同じ階段で降りて退出できる |
| closed-opening | blocked | 上階床の `[1,4,3]` と `[1,4,4]` を塞いだ状態で階段が床にぶつかる |
| low-ceiling | blocked | 最初の段の頭上 `[1,3,2]` に衝突する |
| reverse-stairs | blocked | 階段4段が北向き。南へ向かうと高い側を越す必要があり、ジャンプなしでは登れない |
| missing-floor | blocked | 到着床 `[1,4,6]` がairで、指定到着点に安全に立てない |
| unsupported | unsupported | 到着足元 `[1,5,6]` のフェンスはモデル対象外。不通と断定せず、実機結果と別に記録する |

1. 各schematicを互いに離れた基準点へ配置し、World識別子、Minecraft/mod/WorldEdit版、基準点の座標を記録する。originは `[0,0,0]`。貼付基準点のYが地面block層になる。
2. 通常歩行・手動ドア開閉で、入口→一階到着→二階到着と逆方向を試す。ジャンプ、飛行、泳ぎ、はしご、teleportを通行成功の代替にしない。
3. 各fixtureの入口・階段途中・上階開口・到着床を撮影する。blockedの原因ブロック座標と、実際の立ち位置/向きも記録する。
4. normalは外観と各階内部も撮影する。描画距離、FOV、リソースパックを記録し、限定モデルの結果との一致/不一致と根拠を残す。

各結果の詳細診断と到達pathは `*-result.json`、入力/出力hashと未実施状態は `summary.json`。写真や実機歩行が未取得の間、Issueの実機照合条件は未完了。

#100確定commit `2e10ede67ddd9523214bebed372c742c36938911` の外部previewを別プロセスで利用し、normal/closed-opening/low-ceiling/reverse-stairsのy3/y4断面、normal外観を取得済み。AIはnormalと閉開口のy4対照、normalと低天井のy3対照を確認した。これは実機歩行の照合ではない。画像と検査出力のhashはsummary.jsonに記録する。

## 前提修正後の照合

HEAD `0e0ff92337cbaf155c400012f1ad8509f15e2b90` で、昇降途中に身体が残る低い列の頭上検査と、building階段headroom3の修正が揃った。6fixtureはすべて同じ二階buildingを使うため、入力の意味を変えずschematicを更新した。上階の必要開口 `[1,4,2]` を含め、既存の正常はreachable、閉開口/低天井/逆階段/床欠落はblocked、未知形状はunsupportedを再確認した。検査結果と影響するy4断面も更新済み。修正取り込み後はruffとpytest全1038件が成功した。Minecraft実機歩行の照合は引き続き未実施。
