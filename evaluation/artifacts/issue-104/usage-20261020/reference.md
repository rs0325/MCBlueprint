# 共通修正・座標仕様
根拠: source104@af6f097のdocs/PREVIEW_REGIONS.mdとSkillのpreview/operations仕様。
setのpositionはBlueprint元座標。床blockの一つ上が足元。階段はdirection/start/heightと周辺の段の並びから意図する向き・高さ・形状を確認する。特定座標/操作番号に対する復元値は与えない。
previewは全生成後に描画。--views isometric --scale 12 --grid 1を共通にする。水平断面/追加viewは今回使わない。isometricは+x/+z面と上面を表示し、色は近似。全体図と選択図は同じview/scale、切口や外側遮蔽の除去はcrop固有。画像pixel一致を品質判定にはしない。
crop指定は--from -11 0 0 --to -5 7 10（両端包含、元Blueprint座標、origin差引き不要）。範囲外の遮蔽は除かれる。初期添付画像は各群の許可された全体/選択isometricを同一入力から生成済み。
変更は金の仮ブロックに対応するblock値だけ。他の正常セル・操作・座標・順序・ヘッダを保護する。全体生成の保存セル/状態も照合するので外側を消して見た目だけを合わせない。
