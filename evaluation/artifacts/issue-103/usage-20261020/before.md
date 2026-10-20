# readonly比較 v3 共通規約
あなたは以下の固定課題の候補Blueprintを生成します。tool、shell、任意ファイルアクセス、コマンド実行、追加モデル呼出、ネットワーク、Git、GUIは不要・禁止です。必要な初期JSON・参照・Schema・診断はこの送信本文へ埋め込み済みです。104では同じ初期入力からの許可されたPNGを実imageとして添付します。
返答は完成Blueprintの単一JSONオブジェクトだけ。Markdown fence、説明、path、実行コード、page要求を含めません。ファイル保存は外側がcandidate.jsonとして行います。外側は事前構造制約→静的な既存CLI validate --strict→成功時inspect/build→非公開の最終品質判定を実施し、モデル生成codeは実行しません。
CLI検証がinvalidの場合だけ、同じ表示方式の本物の診断を返して続行でき、候補は最大3roundです。103beforeはtext、103afterはJSON limit4固定。他caseは共通textです。正解/隠しoracleのヒントは返しません。最終oracleだけの不合格をヒントに再試行しません。ページング要求・自律tool探索・追加画像要求はしません。
6群とも同じgpt-6-luna/medium・標準provider/retry設定・新規独立session、wall600秒/観測response8の監視閾値で、hardcapや不可視HTTP数は保証しません。candidate roundは3以下、失敗/追加response/cached inputを含め全計上します。優位性を得るための条件変更はしません。
reference.md内のCLI/参照ファイル記述は外側検証の仕様資料です。モデルが実行/ファイルアクセスしてよいという指示ではありません。

# 課題
initial.jsonは、確認用床の上に石レンガ面、下半分を占めるハーフ、南へ登る通常の階段を置く意図のBlueprintです。ブロックIDの誤記や無効なstateを、その意図に合う既存ID/stateへ修正して候補Blueprintを返してください。どの操作にどの誤りがあるかは診断と入力から調べます。正常なセル、床、座標、操作順/数、ヘッダは維持し、誤ったblock値だけを修正してください。

次の初回診断は外側が既存CLIで取得したraw stdoutです。text方式です。
CLI終了コード:1
<initial-cli-diagnostic>
ERROR operations[1].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[2].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[3].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[4].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[5].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[6].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[7].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[8].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[9].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[10].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[11].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[12].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[13].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[14].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[15].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[16].block (set)
  Unknown block id.
  Current value: stone_brick

ERROR operations[17].block (set)
  Invalid value 'middle' for property 'type' (valid: top, bottom, double).
  Current value: oak_slab[type=middle]

ERROR operations[18].block (set)
  Invalid value 'middle' for property 'type' (valid: top, bottom, double).
  Current value: oak_slab[type=middle]

ERROR operations[19].block (set)
  Invalid value 'middle' for property 'type' (valid: top, bottom, double).
  Current value: oak_slab[type=middle]

ERROR operations[20].block (set)
  Invalid value 'middle' for property 'type' (valid: top, bottom, double).
  Current value: oak_slab[type=middle]

ERROR operations[21].block (set)
  Invalid value 'up' for property 'facing' (valid: north, south, west, east).
  Current value: oak_stairs[facing=up,half=bottom,shape=straight]

ERROR operations[22].block (set)
  Invalid value 'up' for property 'facing' (valid: north, south, west, east).
  Current value: oak_stairs[facing=up,half=bottom,shape=straight]

ERROR operations[23].block (set)
  Invalid value 'up' for property 'facing' (valid: north, south, west, east).
  Current value: oak_stairs[facing=up,half=bottom,shape=straight]

ERROR operations[24].block (set)
  Invalid value 'up' for property 'facing' (valid: north, south, west, east).
  Current value: oak_stairs[facing=up,half=bottom,shape=straight]

24 errors found.

</initial-cli-diagnostic>

# 初期JSON
<initial-json>
{
  "formatVersion": 1,
  "minecraftVersion": "1.21.11",
  "name": "usage103_repair",
  "seed": 17,
  "origin": [
    -2,
    0,
    -1
  ],
  "operations": [
    {
      "type": "fill",
      "from": [
        0,
        0,
        0
      ],
      "to": [
        5,
        0,
        3
      ],
      "block": "stone"
    },
    {
      "type": "set",
      "position": [
        0,
        1,
        0
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        1,
        1,
        0
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        2,
        1,
        0
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        3,
        1,
        0
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        4,
        1,
        0
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        5,
        1,
        0
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        0,
        1,
        1
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        1,
        1,
        1
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        2,
        1,
        1
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        3,
        1,
        1
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        4,
        1,
        1
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        5,
        1,
        1
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        0,
        1,
        2
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        1,
        1,
        2
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        2,
        1,
        2
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        3,
        1,
        2
      ],
      "block": "stone_brick"
    },
    {
      "type": "set",
      "position": [
        4,
        1,
        2
      ],
      "block": "oak_slab[type=middle]"
    },
    {
      "type": "set",
      "position": [
        5,
        1,
        2
      ],
      "block": "oak_slab[type=middle]"
    },
    {
      "type": "set",
      "position": [
        0,
        1,
        3
      ],
      "block": "oak_slab[type=middle]"
    },
    {
      "type": "set",
      "position": [
        1,
        1,
        3
      ],
      "block": "oak_slab[type=middle]"
    },
    {
      "type": "set",
      "position": [
        2,
        1,
        3
      ],
      "block": "oak_stairs[facing=up,half=bottom,shape=straight]"
    },
    {
      "type": "set",
      "position": [
        3,
        1,
        3
      ],
      "block": "oak_stairs[facing=up,half=bottom,shape=straight]"
    },
    {
      "type": "set",
      "position": [
        4,
        1,
        3
      ],
      "block": "oak_stairs[facing=up,half=bottom,shape=straight]"
    },
    {
      "type": "set",
      "position": [
        5,
        1,
        3
      ],
      "block": "oak_stairs[facing=up,half=bottom,shape=straight]"
    }
  ]
}

</initial-json>
# 共通参照
<reference>
# 共通修正仕様
根拠: source103@8c335f4のdocs/AI_GUIDE.md/FORMAT.md。
setはpositionとblockで一セル、fillはfrom/to両端を含む矩形。block文字列はid[property=value,...]、namespace minecraft:は省略可。
validateはSchema→意味→範囲の順。strictは支持警告も失敗。終了0のみ成功、表示件数や種類/パスの制限は検査全体の成功条件を変えない。
JSON対応群は--json/--kind schema|semantic|support/--path/--limit/--offsetが使用可能。JSONはcounts(total/errors/warnings/matched/shown/filteredOut/omitted)、groups、diagnostics(path,message,value)、retrieval.nextOffsetを返す。limit0は全件。before群は既定textのみ。
石レンガ面、下半分のハーフ、南へ登る通常階段という完成意図を維持する。操作番号/位置から正解ID/stateへの対応は与えない。正常セルと全操作/座標/seed/origin/ヘッダは維持し、誤ったblock値だけを修正する。初回診断後、必要ならinitial.json/schema.jsonを読める。

</reference>
# 共通Schema
<schema>
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/rs0325/MCBlueprint/schema/blueprint.schema.json",
  "title": "MCBlueprint Blueprint",
  "description": "Declarative Minecraft structure description (formatVersion 1). See docs/FORMAT.md and docs/OPERATIONS.md.",
  "type": "object",
  "required": [
    "formatVersion",
    "minecraftVersion",
    "name",
    "operations"
  ],
  "additionalProperties": false,
  "properties": {
    "formatVersion": {
      "const": 1
    },
    "minecraftVersion": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+(\\.[0-9]+)?$"
    },
    "name": {
      "type": "string",
      "minLength": 1
    },
    "description": {
      "type": "string"
    },
    "author": {
      "type": "string"
    },
    "seed": {
      "type": "integer"
    },
    "origin": {
      "$ref": "#/$defs/position"
    },
    "size": {
      "type": "array",
      "items": {
        "type": "integer",
        "minimum": 1
      },
      "minItems": 3,
      "maxItems": 3
    },
    "palettes": {
      "type": "object",
      "propertyNames": {
        "pattern": "^[a-z0-9_]+$"
      },
      "additionalProperties": {
        "$ref": "#/$defs/palette"
      }
    },
    "metadata": {
      "type": "object"
    },
    "operations": {
      "$ref": "#/$defs/operations"
    },
    "terrain": {
      "type": "object",
      "required": [
        "source",
        "region"
      ],
      "additionalProperties": false,
      "properties": {
        "source": {
          "type": "string",
          "minLength": 1
        },
        "region": {
          "$ref": "#/$defs/terrainBox"
        },
        "protected": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/terrainBox"
          }
        }
      }
    },
    "foundation": {
      "type": "object",
      "required": [
        "from",
        "to",
        "scan",
        "maxCut",
        "maxFill",
        "maxSupportDepth",
        "ground",
        "block"
      ],
      "additionalProperties": false,
      "properties": {
        "from": {
          "$ref": "#/$defs/position"
        },
        "to": {
          "$ref": "#/$defs/position"
        },
        "scan": {
          "type": "object",
          "required": [
            "minY",
            "maxY"
          ],
          "additionalProperties": false,
          "properties": {
            "minY": {
              "type": "integer"
            },
            "maxY": {
              "type": "integer"
            }
          }
        },
        "maxCut": {
          "type": "integer",
          "minimum": 0
        },
        "maxFill": {
          "type": "integer",
          "minimum": 0
        },
        "maxSupportDepth": {
          "type": "integer",
          "minimum": 1
        },
        "ground": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {
            "$ref": "#/$defs/block"
          }
        },
        "block": {
          "$ref": "#/$defs/block"
        }
      }
    },
    "surfacePath": {
      "type": "object",
      "required": [
        "points",
        "entrance",
        "width",
        "block",
        "stairs",
        "clearance",
        "scan",
        "ground",
        "maxCut",
        "maxFill",
        "maxSupportDepth"
      ],
      "additionalProperties": false,
      "properties": {
        "points": {
          "type": "array",
          "minItems": 2,
          "items": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {
              "type": "integer"
            }
          }
        },
        "entrance": {
          "$ref": "#/$defs/position"
        },
        "width": {
          "type": "integer",
          "minimum": 1
        },
        "block": {
          "$ref": "#/$defs/block"
        },
        "stairs": {
          "$ref": "#/$defs/block"
        },
        "clearance": {
          "type": "integer",
          "minimum": 2
        },
        "scan": {
          "type": "object",
          "required": [
            "minY",
            "maxY"
          ],
          "additionalProperties": false,
          "properties": {
            "minY": {
              "type": "integer"
            },
            "maxY": {
              "type": "integer"
            }
          }
        },
        "ground": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {
            "$ref": "#/$defs/block"
          }
        },
        "maxCut": {
          "type": "integer",
          "minimum": 0
        },
        "maxFill": {
          "type": "integer",
          "minimum": 0
        },
        "maxSupportDepth": {
          "type": "integer",
          "minimum": 1
        }
      }
    }
  },
  "$defs": {
    "position": {
      "type": "array",
      "items": {
        "type": "integer"
      },
      "minItems": 3,
      "maxItems": 3
    },
    "block": {
      "type": "string",
      "pattern": "^(?:[a-z0-9_.-]+:)?[a-z0-9_./-]+(?:\\[[a-z_]+=[a-z0-9_]+(?:,[a-z_]+=[a-z0-9_]+)*\\])?$"
    },
    "paletteName": {
      "type": "string",
      "pattern": "^[a-z0-9_]+$"
    },
    "palette": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": [
          "block"
        ],
        "additionalProperties": false,
        "properties": {
          "block": {
            "$ref": "#/$defs/block"
          },
          "weight": {
            "type": "number",
            "exclusiveMinimum": 0
          }
        }
      }
    },
    "axis": {
      "enum": [
        "x",
        "y",
        "z"
      ]
    },
    "mode": {
      "enum": [
        "hollow",
        "solid"
      ]
    },
    "operations": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "#/$defs/operation"
      }
    },
    "operation": {
      "type": "object",
      "required": [
        "type"
      ],
      "properties": {
        "type": {
          "enum": [
            "set",
            "fill",
            "box",
            "wall",
            "floor",
            "line",
            "circle",
            "cylinder",
            "sphere",
            "mirror",
            "repeat",
            "replace",
            "translate",
            "copy",
            "rotate",
            "stairs",
            "spiral_stairs",
            "roof",
            "pillar",
            "doorway",
            "window",
            "arch",
            "room",
            "tower",
            "bridge",
            "gate",
            "garden",
            "path",
            "component"
          ]
        }
      },
      "allOf": [
        {
          "if": {
            "properties": {
              "type": {
                "const": "set"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/set"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "fill"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/fill"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "box"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/box"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "wall"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/wall"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "floor"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/floor"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "line"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/line"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "circle"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/circle"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "cylinder"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/cylinder"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "sphere"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/sphere"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "mirror"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/mirror"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "repeat"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/repeat"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "replace"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/replace"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "translate"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/translate"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "copy"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/copy"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "rotate"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/rotate"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "stairs"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/stairs"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "spiral_stairs"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/spiral_stairs"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "roof"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/roof"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "pillar"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/pillar"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "doorway"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/doorway"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "window"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/window"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "arch"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/arch"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "room"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/room"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "tower"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/tower"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "bridge"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/bridge"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "gate"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/gate"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "garden"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/garden"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "path"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/path"
          }
        },
        {
          "if": {
            "properties": {
              "type": {
                "const": "component"
              }
            }
          },
          "then": {
            "$ref": "#/$defs/ops/component"
          }
        }
      ]
    },
    "ops": {
      "set": {
        "type": "object",
        "required": [
          "type",
          "position"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "set"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "fill": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "fill"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "box": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "box"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "mode": {
            "$ref": "#/$defs/mode"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "wall": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to",
          "height"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "wall"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "height": {
            "type": "integer",
            "minimum": 1
          },
          "thickness": {
            "type": "integer",
            "minimum": 1
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "floor": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "floor"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "line": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "line"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "circle": {
        "type": "object",
        "required": [
          "type",
          "center",
          "radius"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "circle"
          },
          "center": {
            "$ref": "#/$defs/position"
          },
          "radius": {
            "type": "integer",
            "minimum": 1
          },
          "axis": {
            "$ref": "#/$defs/axis"
          },
          "mode": {
            "$ref": "#/$defs/mode"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "cylinder": {
        "type": "object",
        "required": [
          "type",
          "center",
          "radius",
          "height"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "cylinder"
          },
          "center": {
            "$ref": "#/$defs/position"
          },
          "radius": {
            "type": "integer",
            "minimum": 1
          },
          "height": {
            "type": "integer",
            "minimum": 1
          },
          "axis": {
            "$ref": "#/$defs/axis"
          },
          "mode": {
            "$ref": "#/$defs/mode"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "sphere": {
        "type": "object",
        "required": [
          "type",
          "center",
          "radius"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "sphere"
          },
          "center": {
            "$ref": "#/$defs/position"
          },
          "radius": {
            "type": "integer",
            "minimum": 1
          },
          "mode": {
            "$ref": "#/$defs/mode"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "mirror": {
        "type": "object",
        "required": [
          "type",
          "axis",
          "at",
          "operations"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "mirror"
          },
          "axis": {
            "$ref": "#/$defs/axis"
          },
          "at": {
            "type": "number",
            "multipleOf": 0.5
          },
          "keepOriginal": {
            "type": "boolean"
          },
          "operations": {
            "$ref": "#/$defs/operations"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "repeat": {
        "type": "object",
        "required": [
          "type",
          "count",
          "offset",
          "operations"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "repeat"
          },
          "count": {
            "type": "integer",
            "minimum": 1,
            "maximum": 512
          },
          "offset": {
            "$ref": "#/$defs/position"
          },
          "operations": {
            "$ref": "#/$defs/operations"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "replace": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to",
          "match"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "replace"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "match": {
            "oneOf": [
              {
                "$ref": "#/$defs/block"
              },
              {
                "type": "array",
                "minItems": 1,
                "items": {
                  "$ref": "#/$defs/block"
                }
              }
            ]
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "translate": {
        "type": "object",
        "required": [
          "type",
          "offset",
          "operations"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "translate"
          },
          "offset": {
            "$ref": "#/$defs/position"
          },
          "operations": {
            "$ref": "#/$defs/operations"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "copy": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to",
          "offset"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "copy"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "offset": {
            "$ref": "#/$defs/position"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "rotate": {
        "type": "object",
        "required": [
          "type",
          "angle",
          "center",
          "operations"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "rotate"
          },
          "angle": {
            "enum": [
              90,
              180,
              270
            ]
          },
          "center": {
            "$ref": "#/$defs/position"
          },
          "operations": {
            "$ref": "#/$defs/operations"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "stairs": {
        "type": "object",
        "required": [
          "type",
          "start",
          "direction",
          "height"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "stairs"
          },
          "start": {
            "$ref": "#/$defs/position"
          },
          "direction": {
            "$ref": "#/$defs/direction"
          },
          "height": {
            "type": "integer",
            "minimum": 1
          },
          "width": {
            "type": "integer",
            "minimum": 1
          },
          "headroom": {
            "type": "integer",
            "minimum": 2
          },
          "base": {
            "$ref": "#/$defs/block"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "spiral_stairs": {
        "type": "object",
        "required": [
          "type",
          "center",
          "radius",
          "height"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "spiral_stairs"
          },
          "center": {
            "$ref": "#/$defs/position"
          },
          "radius": {
            "type": "integer",
            "minimum": 1,
            "maximum": 8
          },
          "height": {
            "type": "integer",
            "minimum": 1
          },
          "turn": {
            "enum": [
              "clockwise",
              "counterclockwise"
            ]
          },
          "headroom": {
            "type": "integer",
            "minimum": 2
          },
          "column": {
            "$ref": "#/$defs/block"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "roof": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "roof"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "style": {
            "enum": [
              "gable",
              "hip"
            ]
          },
          "ridge": {
            "enum": [
              "x",
              "z"
            ]
          },
          "overhang": {
            "type": "integer",
            "minimum": 0
          },
          "gable": {
            "$ref": "#/$defs/block"
          },
          "ridgeBlock": {
            "$ref": "#/$defs/block"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "pillar": {
        "type": "object",
        "required": [
          "type",
          "position",
          "height"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "pillar"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "height": {
            "type": "integer",
            "minimum": 1
          },
          "base": {
            "$ref": "#/$defs/block"
          },
          "cap": {
            "$ref": "#/$defs/block"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "doorway": {
        "type": "object",
        "required": [
          "type",
          "position",
          "facing"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "doorway"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "facing": {
            "$ref": "#/$defs/direction"
          },
          "width": {
            "type": "integer",
            "minimum": 1
          },
          "height": {
            "type": "integer",
            "minimum": 2
          },
          "door": {
            "$ref": "#/$defs/block"
          },
          "arch": {
            "$ref": "#/$defs/archSpec"
          },
          "depth": {
            "type": "integer",
            "minimum": 1
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "window": {
        "type": "object",
        "required": [
          "type",
          "position",
          "axis"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "window"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "axis": {
            "enum": [
              "x",
              "z"
            ]
          },
          "width": {
            "type": "integer",
            "minimum": 1
          },
          "height": {
            "type": "integer",
            "minimum": 1
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "arch": {
            "$ref": "#/$defs/archSpec"
          },
          "depth": {
            "type": "integer",
            "minimum": 1
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "arch": {
        "type": "object",
        "required": [
          "type",
          "position",
          "width",
          "height"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "arch"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "axis": {
            "enum": [
              "x",
              "z"
            ]
          },
          "width": {
            "type": "integer",
            "minimum": 1
          },
          "height": {
            "type": "integer",
            "minimum": 1
          },
          "style": {
            "$ref": "#/$defs/archStyle"
          },
          "depth": {
            "type": "integer",
            "minimum": 1
          },
          "thickness": {
            "type": "integer",
            "minimum": 1
          },
          "trim": {
            "$ref": "#/$defs/block"
          },
          "fill": {
            "$ref": "#/$defs/block"
          },
          "hollow": {
            "type": "boolean"
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "room": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to",
          "wall"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "room"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "wall": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "floor": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "ceiling": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "corners": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "thickness": {
            "type": "integer",
            "minimum": 1
          },
          "interior": {
            "type": "boolean"
          },
          "doors": {
            "type": "array",
            "items": {
              "$ref": "#/$defs/roomDoor"
            }
          },
          "windows": {
            "type": "array",
            "items": {
              "$ref": "#/$defs/roomWindow"
            }
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "tower": {
        "type": "object",
        "required": [
          "type",
          "position",
          "height",
          "wall"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "tower"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "shape": {
            "enum": [
              "round",
              "square"
            ]
          },
          "radius": {
            "type": "integer",
            "minimum": 2
          },
          "size": {
            "type": "integer",
            "minimum": 5
          },
          "height": {
            "type": "integer",
            "minimum": 3
          },
          "wall": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "floor": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "floors": {
            "type": "integer",
            "minimum": 3
          },
          "stairs": {
            "oneOf": [
              {
                "type": "boolean"
              },
              {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "radius": {
                    "type": "integer",
                    "minimum": 1
                  },
                  "block": {
                    "$ref": "#/$defs/blockOrPalette"
                  },
                  "turn": {
                    "enum": [
                      "clockwise",
                      "counterclockwise"
                    ]
                  },
                  "column": {
                    "$ref": "#/$defs/block"
                  }
                }
              }
            ]
          },
          "battlement": {
            "oneOf": [
              {
                "type": "boolean"
              },
              {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "block": {
                    "$ref": "#/$defs/blockOrPalette"
                  },
                  "spacing": {
                    "type": "integer",
                    "minimum": 0
                  }
                }
              }
            ]
          },
          "windows": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "sides": {
                "type": "array",
                "items": {
                  "$ref": "#/$defs/direction"
                }
              },
              "sill": {
                "type": "integer",
                "minimum": 1
              },
              "width": {
                "type": "integer",
                "minimum": 1
              },
              "height": {
                "type": "integer",
                "minimum": 1
              },
              "block": {
                "$ref": "#/$defs/block"
              },
              "arch": {
                "$ref": "#/$defs/archSpec"
              }
            }
          },
          "door": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "side": {
                "$ref": "#/$defs/direction"
              },
              "width": {
                "type": "integer",
                "minimum": 1
              },
              "height": {
                "type": "integer",
                "minimum": 2
              },
              "block": {
                "$ref": "#/$defs/block"
              },
              "arch": {
                "$ref": "#/$defs/archSpec"
              }
            }
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "bridge": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to",
          "deck"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "bridge"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "width": {
            "type": "integer",
            "minimum": 1
          },
          "deck": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "style": {
            "enum": [
              "flat",
              "arch"
            ]
          },
          "rise": {
            "type": "integer",
            "minimum": 0
          },
          "stairs": {
            "$ref": "#/$defs/block"
          },
          "railing": {
            "$ref": "#/$defs/block"
          },
          "railingHeight": {
            "type": "integer",
            "minimum": 1
          },
          "piers": {
            "type": "object",
            "required": [
              "spacing",
              "bottom"
            ],
            "additionalProperties": false,
            "properties": {
              "spacing": {
                "type": "integer",
                "minimum": 1
              },
              "bottom": {
                "type": "integer"
              },
              "block": {
                "$ref": "#/$defs/blockOrPalette"
              }
            }
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "gate": {
        "type": "object",
        "required": [
          "type",
          "position",
          "width",
          "height"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "gate"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "axis": {
            "enum": [
              "x",
              "z"
            ]
          },
          "width": {
            "type": "integer",
            "minimum": 1
          },
          "height": {
            "type": "integer",
            "minimum": 2
          },
          "depth": {
            "type": "integer",
            "minimum": 1
          },
          "jamb": {
            "type": "integer",
            "minimum": 1
          },
          "top": {
            "type": "integer",
            "minimum": 0
          },
          "arch": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "style": {
                "$ref": "#/$defs/archStyle"
              },
              "block": {
                "$ref": "#/$defs/block"
              },
              "palette": {
                "$ref": "#/$defs/paletteName"
              },
              "trim": {
                "$ref": "#/$defs/block"
              },
              "thickness": {
                "type": "integer",
                "minimum": 1
              }
            }
          },
          "battlement": {
            "oneOf": [
              {
                "type": "boolean"
              },
              {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "block": {
                    "$ref": "#/$defs/blockOrPalette"
                  },
                  "spacing": {
                    "type": "integer",
                    "minimum": 0
                  }
                }
              }
            ]
          },
          "portcullis": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "block": {
                "$ref": "#/$defs/block"
              },
              "height": {
                "type": "integer",
                "minimum": 1
              }
            }
          },
          "door": {
            "$ref": "#/$defs/block"
          },
          "towers": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "size": {
                "type": "integer",
                "minimum": 5
              },
              "height": {
                "type": "integer",
                "minimum": 3
              },
              "wall": {
                "$ref": "#/$defs/blockOrPalette"
              },
              "floor": {
                "$ref": "#/$defs/blockOrPalette"
              },
              "floors": {
                "type": "integer",
                "minimum": 3
              },
              "stairs": {
                "oneOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "object",
                    "additionalProperties": false,
                    "properties": {
                      "radius": {
                        "type": "integer",
                        "minimum": 1
                      },
                      "block": {
                        "$ref": "#/$defs/blockOrPalette"
                      },
                      "turn": {
                        "enum": [
                          "clockwise",
                          "counterclockwise"
                        ]
                      },
                      "column": {
                        "$ref": "#/$defs/block"
                      }
                    }
                  }
                ]
              },
              "battlement": {
                "oneOf": [
                  {
                    "type": "boolean"
                  },
                  {
                    "type": "object",
                    "additionalProperties": false,
                    "properties": {
                      "block": {
                        "$ref": "#/$defs/blockOrPalette"
                      },
                      "spacing": {
                        "type": "integer",
                        "minimum": 0
                      }
                    }
                  }
                ]
              },
              "windows": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "sides": {
                    "type": "array",
                    "items": {
                      "$ref": "#/$defs/direction"
                    }
                  },
                  "sill": {
                    "type": "integer",
                    "minimum": 1
                  },
                  "width": {
                    "type": "integer",
                    "minimum": 1
                  },
                  "height": {
                    "type": "integer",
                    "minimum": 1
                  },
                  "block": {
                    "$ref": "#/$defs/block"
                  },
                  "arch": {
                    "$ref": "#/$defs/archSpec"
                  }
                }
              },
              "door": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "side": {
                    "$ref": "#/$defs/direction"
                  },
                  "width": {
                    "type": "integer",
                    "minimum": 1
                  },
                  "height": {
                    "type": "integer",
                    "minimum": 2
                  },
                  "block": {
                    "$ref": "#/$defs/block"
                  },
                  "arch": {
                    "$ref": "#/$defs/archSpec"
                  }
                }
              }
            }
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "garden": {
        "type": "object",
        "required": [
          "type",
          "from",
          "to"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "garden"
          },
          "from": {
            "$ref": "#/$defs/position"
          },
          "to": {
            "$ref": "#/$defs/position"
          },
          "style": {
            "enum": [
              "farm",
              "flowers"
            ]
          },
          "crop": {
            "$ref": "#/$defs/block"
          },
          "water": {
            "type": "integer",
            "minimum": 0
          },
          "rows": {
            "enum": [
              "x",
              "z"
            ]
          },
          "ground": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "plants": {
            "$ref": "#/$defs/blockOrPalette"
          },
          "fence": {
            "$ref": "#/$defs/block"
          },
          "gate": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "side": {
                "$ref": "#/$defs/direction"
              },
              "offset": {
                "type": "integer",
                "minimum": 1
              },
              "block": {
                "$ref": "#/$defs/block"
              }
            }
          },
          "lanterns": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "spacing": {
                "type": "integer",
                "minimum": 1
              },
              "block": {
                "$ref": "#/$defs/block"
              }
            }
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "path": {
        "type": "object",
        "required": [
          "type",
          "points"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "path"
          },
          "points": {
            "type": "array",
            "minItems": 2,
            "items": {
              "$ref": "#/$defs/position"
            }
          },
          "width": {
            "type": "integer",
            "minimum": 1
          },
          "edge": {
            "$ref": "#/$defs/block"
          },
          "stairs": {
            "$ref": "#/$defs/block"
          },
          "clearance": {
            "type": "integer",
            "minimum": 0
          },
          "lights": {
            "type": "object",
            "required": [
              "spacing"
            ],
            "additionalProperties": false,
            "properties": {
              "spacing": {
                "type": "integer",
                "minimum": 1
              },
              "component": {
                "type": "string",
                "pattern": "^[a-z0-9_]+$"
              },
              "block": {
                "$ref": "#/$defs/block"
              }
            }
          },
          "block": {
            "$ref": "#/$defs/block"
          },
          "palette": {
            "$ref": "#/$defs/paletteName"
          },
          "comment": {
            "type": "string"
          }
        }
      },
      "component": {
        "type": "object",
        "required": [
          "type",
          "name",
          "position"
        ],
        "additionalProperties": false,
        "properties": {
          "type": {
            "const": "component"
          },
          "name": {
            "type": "string",
            "pattern": "^[a-z0-9_]+$"
          },
          "position": {
            "$ref": "#/$defs/position"
          },
          "rotation": {
            "enum": [
              0,
              90,
              180,
              270
            ]
          },
          "comment": {
            "type": "string"
          }
        }
      }
    },
    "direction": {
      "enum": [
        "north",
        "south",
        "east",
        "west"
      ]
    },
    "archStyle": {
      "enum": [
        "round",
        "pointed",
        "flat"
      ]
    },
    "archSpec": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "style": {
          "$ref": "#/$defs/archStyle"
        },
        "block": {
          "$ref": "#/$defs/block"
        },
        "palette": {
          "$ref": "#/$defs/paletteName"
        },
        "trim": {
          "$ref": "#/$defs/block"
        },
        "thickness": {
          "type": "integer",
          "minimum": 1
        }
      },
      "oneOf": [
        {
          "required": [
            "block"
          ]
        },
        {
          "required": [
            "palette"
          ]
        }
      ]
    },
    "blockOrPalette": {
      "oneOf": [
        {
          "$ref": "#/$defs/block"
        },
        {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "block": {
              "$ref": "#/$defs/block"
            },
            "palette": {
              "$ref": "#/$defs/paletteName"
            }
          },
          "oneOf": [
            {
              "required": [
                "block"
              ]
            },
            {
              "required": [
                "palette"
              ]
            }
          ]
        }
      ]
    },
    "roomDoor": {
      "type": "object",
      "required": [
        "side"
      ],
      "additionalProperties": false,
      "properties": {
        "side": {
          "$ref": "#/$defs/direction"
        },
        "offset": {
          "type": "integer",
          "minimum": 0
        },
        "width": {
          "type": "integer",
          "minimum": 1
        },
        "height": {
          "type": "integer",
          "minimum": 2
        },
        "door": {
          "$ref": "#/$defs/block"
        },
        "arch": {
          "$ref": "#/$defs/archSpec"
        },
        "comment": {
          "type": "string"
        }
      }
    },
    "roomWindow": {
      "type": "object",
      "required": [
        "side"
      ],
      "additionalProperties": false,
      "properties": {
        "side": {
          "$ref": "#/$defs/direction"
        },
        "offset": {
          "type": "integer",
          "minimum": 0
        },
        "width": {
          "type": "integer",
          "minimum": 1
        },
        "height": {
          "type": "integer",
          "minimum": 1
        },
        "sill": {
          "type": "integer",
          "minimum": 1
        },
        "count": {
          "type": "integer",
          "minimum": 1
        },
        "spacing": {
          "type": "integer",
          "minimum": 0
        },
        "block": {
          "$ref": "#/$defs/block"
        },
        "arch": {
          "$ref": "#/$defs/archSpec"
        },
        "comment": {
          "type": "string"
        }
      }
    },
    "terrainBox": {
      "type": "object",
      "required": [
        "from",
        "to"
      ],
      "additionalProperties": false,
      "properties": {
        "from": {
          "$ref": "#/$defs/position"
        },
        "to": {
          "$ref": "#/$defs/position"
        }
      }
    }
  },
  "dependentRequired": {
    "foundation": [
      "terrain"
    ],
    "surfacePath": [
      "terrain"
    ]
  }
}

</schema>
