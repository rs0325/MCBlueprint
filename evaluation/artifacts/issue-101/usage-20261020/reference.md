# 共通仕様抜粋（両群同一）
根拠: source101@6dd0944のdocs/OPERATIONS.mdとSkill references/operations.md。
JSONはformatVersion=1、minecraftVersion=1.21.11、name/seed/origin/operations。位置は整数3要素。
room: from/toは外寸、from.y床・to.y天井。wall/floor/ceilingに単一ブロック。windowsは[{side,sill,height,block}]で自動配置、doorsは[{side,offset,door}]。sideはnorth/east/south/west。thickness既定1、interior既定true。
stairs: startは1段目（床の1つ上）、direction=southなら+zへ登る。height段、headroom=3、blockは階段材、baseは下埋め材。上階の床と最後の段のblockYが等しい。
roof: from/toは軒高の矩形、style=gable、ridge=z、overhang=1、blockは階段材、gableは妻壁材。
translate: {type:translate,offset:[x,y,z],operations:[...]}; rotate:{type:rotate,angle:90,center:[0,0,0],operations:[...]}。回転x'=-z,z'=x、回転後平行移動するなら外側translate内側rotate。
building: position,width,depth,floors,floorHeight,angle,wall,floor,roof,stairs,window,door。angleはposition原点の回転、width/depthは回転前。floorY基準の入口下段Y+1。
標準配置: 回転前local外周x0..width-1,z0..depth-1、各階床Y=level*floorHeight、天井Y=(level+1)*floorHeight、壁厚1。入口は北のoffset floor((width-1)/2)、oak_door。各階東/南窓、二階のみ北窓（sill2,height2、room既定自動位置）、西窓なし。二階の階段はlocal[1,1,2]→+zへfloorHeight段、headroom3、baseはfloor材。屋根はlocal Y=floors*floorHeight、gable/ridgez/overhang1、妻壁はwall材。
ブロックIDのminecraft:接頭辞は省略可能。JSONへ実行コードを入れない。schema.jsonは必要なら参照可。
