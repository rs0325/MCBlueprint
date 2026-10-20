# 共通修正仕様
根拠: source103@8c335f4のdocs/AI_GUIDE.md/FORMAT.md。
setはpositionとblockで一セル、fillはfrom/to両端を含む矩形。block文字列はid[property=value,...]、namespace minecraft:は省略可。
validateはSchema→意味→範囲の順。strictは支持警告も失敗。終了0のみ成功、表示件数や種類/パスの制限は検査全体の成功条件を変えない。
JSON対応群は--json/--kind schema|semantic|support/--path/--limit/--offsetが使用可能。JSONはcounts(total/errors/warnings/matched/shown/filteredOut/omitted)、groups、diagnostics(path,message,value)、retrieval.nextOffsetを返す。limit0は全件。before群は既定textのみ。
石レンガ面、下半分のハーフ、南へ登る通常階段という完成意図を維持する。操作番号/位置から正解ID/stateへの対応は与えない。正常セルと全操作/座標/seed/origin/ヘッダは維持し、誤ったblock値だけを修正する。初回診断後、必要ならinitial.json/schema.jsonを読める。
