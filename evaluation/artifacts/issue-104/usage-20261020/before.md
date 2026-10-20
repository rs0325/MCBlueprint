# readonly比較 v3 共通規約
あなたは以下の固定課題の候補Blueprintを生成します。tool、shell、任意ファイルアクセス、コマンド実行、追加モデル呼出、ネットワーク、Git、GUIは不要・禁止です。必要な初期JSON・参照・Schema・診断はこの送信本文へ埋め込み済みです。104では同じ初期入力からの許可されたPNGを実imageとして添付します。
返答は完成Blueprintの単一JSONオブジェクトだけ。Markdown fence、説明、path、実行コード、page要求を含めません。ファイル保存は外側がcandidate.jsonとして行います。外側は事前構造制約→静的な既存CLI validate --strict→成功時inspect/build→非公開の最終品質判定を実施し、モデル生成codeは実行しません。
CLI検証がinvalidの場合だけ、同じ表示方式の本物の診断を返して続行でき、候補は最大3roundです。103beforeはtext、103afterはJSON limit4固定。他caseは共通textです。正解/隠しoracleのヒントは返しません。最終oracleだけの不合格をヒントに再試行しません。ページング要求・自律tool探索・追加画像要求はしません。
6群とも同じgpt-6-luna/medium・標準provider/retry設定・新規独立session、wall600秒/観測response8の監視閾値で、hardcapや不可視HTTP数は保証しません。candidate roundは3以下、失敗/追加response/cached inputを含め全計上します。優位性を得るための条件変更はしません。
reference.md内のCLI/参照ファイル記述は外側検証の仕様資料です。モデルが実行/ファイルアクセスしてよいという指示ではありません。

# 課題
添付の初期isometric画像とinitial.jsonに基づき、入口床・直進階段・上端着地点に残る金の仮ブロックを直し、候補Blueprintを返してください。対象領域は元Blueprint座標from[-11,0,0] to[-5,7,10]です（この座標情報は両群共通）。
初期添付画像を実際に確認し、入口床・直進階段・上端着地に残る金の仮ブロックを探し、周辺と元の構造に一致するブロック/状態へ復元してください。正常なセルと、他の操作・座標・ヘッダ・装飾列は維持し、仮ブロックに対応するblock値だけを直してください。
添付は全体isometric画像です。画像を実際に確認して元構造に復元し、他の正常セルを維持してください。追加previewは要求しません。
# 初期JSON
<initial-json>
{
  "formatVersion": 1,
  "minecraftVersion": "1.21.11",
  "name": "usage104_repair",
  "seed": 17,
  "origin": [
    -20,
    0,
    0
  ],
  "operations": [
    {
      "type": "fill",
      "from": [
        -30,
        0,
        -10
      ],
      "to": [
        35,
        0,
        30
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        12,
        1,
        -8
      ],
      "to": [
        12,
        3,
        -8
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        12,
        1,
        2
      ],
      "to": [
        12,
        3,
        2
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        12,
        1,
        12
      ],
      "to": [
        12,
        3,
        12
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        12,
        1,
        22
      ],
      "to": [
        12,
        3,
        22
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        22,
        1,
        -8
      ],
      "to": [
        22,
        3,
        -8
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        22,
        1,
        2
      ],
      "to": [
        22,
        3,
        2
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        22,
        1,
        12
      ],
      "to": [
        22,
        3,
        12
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        22,
        1,
        22
      ],
      "to": [
        22,
        3,
        22
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        32,
        1,
        -8
      ],
      "to": [
        32,
        3,
        -8
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        32,
        1,
        2
      ],
      "to": [
        32,
        3,
        2
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        32,
        1,
        12
      ],
      "to": [
        32,
        3,
        12
      ],
      "block": "stone_bricks"
    },
    {
      "type": "fill",
      "from": [
        32,
        1,
        22
      ],
      "to": [
        32,
        3,
        22
      ],
      "block": "stone_bricks"
    },
    {
      "type": "stairs",
      "start": [
        -9,
        1,
        8
      ],
      "direction": "north",
      "height": 4,
      "headroom": 3,
      "block": "oak_stairs",
      "base": "oak_planks"
    },
    {
      "type": "fill",
      "from": [
        -9,
        4,
        1
      ],
      "to": [
        -5,
        4,
        4
      ],
      "block": "oak_planks"
    },
    {
      "type": "set",
      "position": [
        -9,
        0,
        9
      ],
      "block": "gold_block"
    },
    {
      "type": "set",
      "position": [
        -9,
        2,
        7
      ],
      "block": "gold_block"
    },
    {
      "type": "set",
      "position": [
        -9,
        4,
        4
      ],
      "block": "gold_block"
    }
  ]
}

</initial-json>
# 共通参照
<reference>
# 共通修正・座標仕様
根拠: source104@af6f097のdocs/PREVIEW_REGIONS.mdとSkillのpreview/operations仕様。
setのpositionはBlueprint元座標。床blockの一つ上が足元。階段はdirection/start/heightと周辺の段の並びから意図する向き・高さ・形状を確認する。特定座標/操作番号に対する復元値は与えない。
previewは全生成後に描画。--views isometric --scale 12 --grid 1を共通にする。水平断面/追加viewは今回使わない。isometricは+x/+z面と上面を表示し、色は近似。全体図と選択図は同じview/scale、切口や外側遮蔽の除去はcrop固有。画像pixel一致を品質判定にはしない。
crop指定は--from -11 0 0 --to -5 7 10（両端包含、元Blueprint座標、origin差引き不要）。範囲外の遮蔽は除かれる。初期添付画像は各群の許可された全体/選択isometricを同一入力から生成済み。
変更は金の仮ブロックに対応するblock値だけ。他の正常セル・操作・座標・順序・ヘッダを保護する。全体生成の保存セル/状態も照合するので外側を消して見た目だけを合わせない。

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
    }
  }
}

</schema>
