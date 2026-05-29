# pptx-enterprise — 企业级 PPT 生成 Skill

为 **OpenClaw / 星Claw** 打造的企业级 PPT 生成能力。模型只需写一份 **JSON 布局树**,由布局引擎自动排版、套用 TCL 品牌母版,输出**原生可编辑**的 `.pptx`。与模型无关(Qwen / DeepSeek / Claude 均可),弱模型也能稳定产出。

> 面向 AI 智能体的详细用法见 [`SKILL.md`](SKILL.md);本文件面向人,讲清楚「是什么、怎么装、怎么用、有哪些能力」。

---

## 一、核心理念

**先内容逻辑,后排版;模型决定结构,引擎决定像素。**

- 模型按「内容形态」组合组件(card / chart / arrowflow / quadrant …)成一棵布局树;
- 引擎用 flex 式自动布局计算坐标 —— **永不重叠、自适应内容**;
- 全程套用 TCL 主题(科技蓝 + 深 navy + 红关键点 + 微软雅黑)与母版 chrome(红角标 / 五环 LOGO / 封面)。

这套设计专门解决两个老问题:**布局死板/重叠** 和 **页页卡片的"纯 AI 味"**。

---

## 二、能力总览

| 类别 | 能力 |
|---|---|
| **生成** | 大纲 → 布局树 → 原生可编辑 `.pptx`(PptxGenJS,默认)/ 母版像素级保真(python-pptx) |
| **布局引擎** | 容器 `row/col/grid` + **23+ 语义组件**,自动排版防重叠 |
| **图表** | 柱/条/折线/面积/饼/环/雷达 = **原生可编辑图表**;进度环 gauge;矩阵热力 heatmap |
| **图示** | 流程/箭头/时间线/里程碑/SWOT四象限/对比天平/漏斗/组织架构/战略屋/技术架构/辐射图… |
| **图标** | Lucide + IconPark 共 ~7000,**强制单色化**(永不出现黑色),按品牌色染色 |
| **品牌** | TCL 母版 + 红角标/五环/封面 + 多主题(tcl_feishu / ocean / midnight / mono) |
| **编辑现有 PPT** | 高层指令(改文本/表格/图表数据/换图/增删调序页)+ 任意 OOXML 深编辑(unpack/pack) |
| **质检 QA** | 多样性 lint / JSON 校验 / **OOXML 成品校验** / 文本抽取查占位符 / 逐页出图 + 缩略图网格 |
| **方法论** | 制作流程总纲、6 类材料叙事框架、内容形态→版式映射、通俗易懂规则、research-first |

---

## 三、安装

```bash
cd skills/star-claw/pptx-enterprise
bash setup.sh        # 幂等:装系统/Python/Node 依赖并跑自检
```

`setup.sh` 安装:

- **Node**(必需):`pptxgenjs` `pptxtojson` `@resvg/resvg-js` `@iconify-json/*`
- **Python**(必需):`python-pptx` `jsonschema` `Pillow`(可选 `markitdown[pptx]` 做文本抽取)
- **系统**(仅可视化 QA 需要):`libreoffice-impress` `poppler-utils` `fonts-noto-cjk`(精简装,约 300–500MB)

> 核心「生成」只需 Node + Python;可视化 QA 用 `preview_all.py`(resvg,**不依赖 LibreOffice**),所以多数环境无需装 LibreOffice。

---

## 四、快速开始

1. 写一份大纲 `deck.json`(或让模型按 `assets/examples/` 改):

```json
{
  "title": "AI 基础知识培训",
  "slides": [
    { "layout": "cover", "title": "AI 基础知识培训", "dept": "数字化转型中心", "author": "讲师:小黑" },
    { "title": "AI 不是魔法,是用数据训练出来的程序",
      "banner": "AI = 感知 + 学习 + 推理 + 行动",
      "body": { "type": "row", "sizes": [3,2], "gap": 28, "items": [
        { "type": "hero", "kicker": "一句话定义", "value": "人工智能", "label": "让机器具备感知、学习、推理、行动能力" },
        { "type": "bullets", "items": ["感知:看懂图文语音", "学习:从数据归纳规律", "推理:判断与生成", "行动:调用工具闭环"] }
      ] } }
  ]
}
```

2. 生成 → 校验 → 出片:

```bash
python scripts/outline_to_schema.py deck.json > out.deck.json   # 大纲→布局(自动排版/图标/图表)
python scripts/lint_variety.py deck.json                        # 多样性自检(防千篇一律)
node   scripts/schema_to_pptx.js out.deck.json deck.pptx        # 默认:原生可编辑 .pptx
python scripts/validate_pptx.py deck.pptx                       # 成品 OOXML 校验
python scripts/thumbnail.py out.deck.json grid.png             # 整份缩略图,一眼看全
```

母版像素级保真版本:`python scripts/schema_to_pptx_tpl.py out.deck.json deck.pptx`

---

## 五、制作流程(专家级,模型按此执行)

① 立意(目标/受众/唯一主张/材料类型) → ② 搭故事线(没有大纲就自己设计,每页一个论点) → ③ 用 `web_search` 检索真实内容与图片 → ④ 定稿内容结构 → ⑤ 逐页按内容形态选版式、组合成论点、写通俗易懂 → ⑥ QA 当 bug-hunt(多样性/内容/视觉,修完复验) → ⑦ 对照唯一主张终审。详见 SKILL.md。

**6 类材料叙事框架**:培训(认知阶梯)/ 工作汇报(结论先行 BLUF)/ 方案(SCQA)/ 复盘(目标vs结果→归因)/ 产品(痛点→定位→证据)/ 战略(战略屋)。

---

## 六、组件与版式

- **容器**:`row` / `col` / `grid`(`gap` / `sizes` / `cols`,可任意嵌套)
- **文本/卡片**:`text` `bullets` `card` `panel` `iconitem` `imagecard` `personcard` `quote`
- **数字**:`stat` `hero` `gauge`
- **流程/结构**:`arrowflow` `timeline` `milestone` `funnel` `quadrant` `balance` `regions` `orgchart`
- **进度/对比**:`progresslist` `pricing`
- **图表**:`chart`(column/bar/line/area/pie/donut/radar) + `heatmap`
- **固定版式预设**:cover / agenda / section / closing 等(快速骨架用)

任意 item 加 `"accent":"red"` 标记关键节点;图标在彩色块上恒为白色。

---

## 七、脚本速查

| 用途 | 命令 |
|---|---|
| 大纲→布局 | `outline_to_schema.py` |
| 生成(默认,可编辑) | `schema_to_pptx.js` |
| 生成(母版保真) | `schema_to_pptx_tpl.py` |
| 多样性自检 | `lint_variety.py` |
| JSON 校验 | `validate.py` |
| 成品 OOXML 校验 | `validate_pptx.py` |
| 文本+备注抽取 | `extract_text.py` |
| 逐页出图 / 缩略图网格 | `preview_all.py` / `thumbnail.py` |
| 单页出图(无需 LibreOffice) | `preview.js` |
| 看现有 PPT 结构 | `dump_pptx.py` |
| 编辑现有 PPT(高层) | `edit_pptx.py` |
| 深编辑任意 XML | `unpack_pptx.py` → 改 → `pack_pptx.py` |
| 填充品牌模板 | `template_fill.py` |
| 一键自检 | `smoke_test.py` |
| Lark 进度通知 | `notify_lark.py`(`LARK_CLI_CMD` / `LARK_WEBHOOK`) |

---

## 八、与 Anthropic 官方 pptx skill 的关系

能力面 **≥ 官方**:官方靠模型逐页手写 PptxGenJS 代码(灵活但易重叠,靠大量 QA 兜底);本 skill 用**自动布局引擎**(防重叠、模型无关)+ **可量化多样性卡口** + **品牌母版系统**。官方的强项(原生图表、内容抽取、视觉 QA bug-hunt 协议、深 OOXML 编辑、缩略图)均已吸收。

差异点:官方做 ISO **XSD schema 校验**,本 skill 做**结构完整性校验**(可加载性 + XML 良构 + 关系解析),对"成品是否损坏"目标等价。

---

## 九、已知边界(诚实说明)

- 双产物「内容一致,非像素一致」:浏览器与 PowerPoint 排版引擎在折行/字体度量上有差异;品牌像素级以母版路径为准。
- `gauge`(进度环)是栅格化图片,非原生图表;真实地理地图需外部地图 SVG 素材(现以 `regions` 排名条表达)。
- 母版路径(python-pptx)不绘制柔和阴影;阴影在默认 PptxGenJS 路径与预览中渲染。
- `web_search` / Lark-CLI 依赖 OpenClaw 运行环境提供。

---

## 十、目录结构

```
pptx-enterprise/
├── SKILL.md              # 面向 AI 的完整说明(流程/框架/规则/组件)
├── README.md             # 本文件(面向人)
├── setup.sh              # 一键装环境 + 自检
├── schema/slide_schema.json
├── scripts/              # 生成/渲染/编辑/QA/工具脚本
├── assets/
│   ├── themes/           # tcl_feishu(默认)/ ocean / midnight / mono
│   ├── examples/         # 6 类材料可模仿范例(training/report/solution/review/product/strategy)
│   ├── csot_master.pptx  # TCL 母版
│   └── tcl_logo.png …    # 品牌素材
└── references/           # schema 编写 / PptxGenJS 速查
```

> 无第三方 AGPL/GPL 代码:输出基于 PptxGenJS(MIT)/ python-pptx(MIT),图标 ISC/Apache-2.0 —— 不会给你的 PPT 带来 copyleft 义务。
