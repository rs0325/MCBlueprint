# Issue #103 固定課題の使用量比較（2026-10-20）

片側機械品質不合格。token差が小さくても品質同等の効率改善とは解釈できない。

## 再現対象

`initial.json`、`reference.md`と同一Schemaを埋め込んだ`before.md`/`after.md`が実送信全文。候補は`before-candidate.json`/`after-candidate.json`。104は対応するPNGを実imageとして各1枚添付した。Schemaのcommit/SHA、元manifest、判定scriptの原本SHAは`provenance.json`。完成後の期待値は`private/`に保存し、測定時モデルへ非公開だった。

全群gpt-6-luna/medium、公式CLI read-only、toolなし、新規独立session、候補1round。外側が候補を保存しstrict validate/inspect/build成功後に固定oracleを評価。合法なJSONと完成要求の一致は別判定である。コードを生成実行する比較ではない。

リポジトリrootでPython 3.14.4、`PYTHONPATH=src`を設定してbefore/after両候補について既存CLIを実行できる。

```text
python -m mcblueprint validate evaluation/artifacts/issue-103/usage-20261020/before-candidate.json --strict
python -m mcblueprint inspect evaluation/artifacts/issue-103/usage-20261020/before-candidate.json
python -m mcblueprint build evaluation/artifacts/issue-103/usage-20261020/before-candidate.json -o output/usage-103-before.schem
```

機械照合は`mcblueprint.loader.load_blueprint_dict`→`generator.generate`で候補/期待値を生成し、`blockdata.load_block_data("1.21.11").complete(state).to_string()`でdefaultを補完した全座標/state辞書の完全一致を比較する。101は`private/101-independent.json`とも全864セル一致、103/104は`mismatches.json`に全不一致を保存。正常構造保護は操作列から修正許可blockだけを除いたJSON同一性も検査済み。

## 記録と制約

`usage.json`は#97 schemaVersion1。`aggregation.json`は#97確定scriptによる集計。callsは正式response ID付き完了response数であり、標準retryを含むHTTP試行数はunknown。cached input/reasoningはそれぞれinput/output内数。画像tokenの内訳と実費は未取得、公式credits換算は実請求ではない。`evidence-extract.json`は正式usage/IDと非公開raw原本SHAの安全な射影で、原本本文を含まない。

新生成物の人間/実機品質は未評価で、一般/熟練の同等品質を証明しない。usageのqualityOutcomeはunknown、accepted成果は0。既存ユーザー正常報告を新生成物へ拡張しない。103/104のafterは機械品質不合格のため同品質での削減率を主張しない。103afterの外側出力capture復旧時間は直接比較不可。

各1pair・固定順序・cache差がある狭い埋込JSON生成/修正比較であり、統計的な一般化、自律agentworkflow、診断paging選択や再preview効率は未測定。共有環境失敗68864 tokens/3responsesを消さず`common-accounting.json`へ保持するが、Issue別消費へ加算しない。同じ共通記録が各dirにあるため合算禁止。grandtotalは測定用CLI7session限定で、開発全消費/TCOではない。
