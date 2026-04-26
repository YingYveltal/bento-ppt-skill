---
name: ppt-agent
description: 从一个主题或文档生成 16:9 SVG 演示文稿（Bento Grid 风格），产出 HTML 翻页预览 + 可在 PowerPoint 中编辑的矢量 PPTX。当用户说"做 PPT"、"做幻灯片"、"做 deck"、"生成演示文稿"、"做发布会 slides"、"make a presentation/deck"、"build slides" 时使用。
when_to_use: PPT 生成、做幻灯片、生成演示文稿、把主题或文档转成 slides、做发布会、做产品介绍 PPT、make a deck、build presentation、create slides
allowed-tools: Bash, WebSearch, Read, Write, Edit, Glob, Grep
---

# ppt-agent

把一个主题（或一份文档）变成可演讲的 PPT。底层是**整页 SVG**（viewBox `0 0 1280 720`），同时产出：

1. `deck.html` — 浏览器里左右键翻页的预览
2. `deck.pptx` — 在 PowerPoint 2019+ / Office 365 / Keynote 里可编辑的矢量 PPT
3. `deck.pdf`（可选）

## 设计理念（先读完再开工）

这个 skill 模仿 sandun 的"最强 PPT Agent"方法论，**关键差异点**是在大纲和设计之间插入"**策划稿**"——每页放什么版式、什么槽位先定死，再去渲染。这是市面 AI PPT 工具普遍跳过的环节，也是质量分水岭。

四个核心反直觉：

1. **不要听到主题就直接出大纲。** 先反问 3-5 个问题（受众/场景/时长/调性/页数），写到 `brief.md`。这是质量上限的瓶颈。
2. **大纲走金字塔原理**（结论先行 + 以上统下 + 归类分组 + 逻辑递进）。详见 [reference/pyramid-outline-prompt.md](reference/pyramid-outline-prompt.md)。
3. **策划稿先于设计**。每页是哪种 Bento 布局（6 选 1）、放哪些卡片（component），先固化到 `layout.json`，再渲染 SVG。详见 [reference/bento-layouts-guide.md](reference/bento-layouts-guide.md)。
4. **底层是 SVG 不是 HTML**。理由：PowerPoint 2019+ 原生支持矢量 SVG，文字可编辑、无限放大。HTML 只用于浏览器预览。

## 7 阶段工作流

| # | 阶段 | 你做什么 | 脚本做什么 | 产物 |
|---|---|---|---|---|
| 1 | needs | 反问 3-5 个问题，把答案写进 `brief.md` | `ppt new` 起工作区 | `brief.md` |
| 2 | research | 用 WebSearch 按主题分章节搜真实材料 | — | `research/<chapter>.md` |
| 3 | outline | 套金字塔原理 prompt 出大纲 | — | `outline.json` |
| 4 | planning | 把大纲转成 layout.json（每页选布局 + 槽位 component + 内容草稿） | — | `layout.json` |
| 4.5 | **fetch（可选）** | 给 card-image 填 `src=URL` 或 `source` 规格 | `ppt fetch` 调 provider 下载/生成到 `<ws>/assets/` | `assets/*.png` |
| 5 | design | 检查 layout.json 内容质量 | `ppt scaffold` 调 render 装配 SVG | `slides/*.svg` |
| 6 | review | 看截图清单（溢出/对比度/中英排版/重复） | `ppt shoot` 截图 + 生成 deck.html | `shots/*.png`、`deck.html` |
| 7 | export | 决定导出格式 | `ppt export` | `deck.pptx` / `deck.pdf` |

任何阶段失败都可以单独重跑，**不需要从头来**。fetch 阶段也永远不会因为下载失败阻塞主流程（详见 [reference/image-providers.md](reference/image-providers.md)）。

## 阶段 1：需求调研（关键）

启动后**第一件事**是反问。不要默认用户给的主题已经够清楚了。

```
ppt new "<topic>"
# 输出 ~/ppt-decks/<date>-<slug>/
```

然后向用户问以下问题（一次问完，不要逐个），把答案写到 `<ws>/brief.md`：

1. **目标受众是谁？** （投资人 / 客户 / 内部团队 / 行业大会观众）
2. **场景和时长？** （15 分钟产品发布 / 5 分钟电梯演讲 / 30 分钟内训）
3. **核心目标？** （让对方掏钱 / 让对方点头 / 让对方转发 / 让对方学到东西）
4. **调性偏好？** （严肃专业 / 活泼有趣 / 极简克制 / 数据密集）
5. **页数预算？** （8 页内 / 15-20 页 / 30+ 页）
6. **必须出现的内容？** （某个产品截图 / 某个数据 / 团队照 / 客户 logo 墙）

如果用户已经给了文档，先 Read 一遍，然后只问没有覆盖的问题。

`brief.md` 模板由 `ppt new` 自动写入，照着填即可。

## 阶段 2：资料检索

按 `brief.md` 里的核心主题，用 WebSearch 工具分章节搜资料，结果落到 `<ws>/research/<chapter-slug>.md`。

**禁止凭空捏造数据/事实**——所有数字、产品特性、市场状况必须有出处。检索结果用来"喂"阶段 3 的大纲，不是直接抄。

## 阶段 3：大纲

读完 `brief.md` + `research/`，套用金字塔原理 prompt 生成大纲，输出到 `<ws>/outline.json`。

**完整 prompt 见 [reference/pyramid-outline-prompt.md](reference/pyramid-outline-prompt.md)**（直接复用 sandun 开源的"顶级 PPT 结构架构师"v2.0）。

`outline.json` schema（关键字段）：

```json
{
  "ppt_outline": {
    "cover": { "title": "...", "sub_title": "...", "content": [] },
    "table_of_contents": { "title": "目录", "content": ["第一部分", "第二部分", ...] },
    "parts": [
      {
        "part_title": "第一部分：...",
        "pages": [
          { "title": "页面标题", "content": ["要点 1", "要点 2", ...] }
        ]
      }
    ],
    "end_page": { "title": "总结与展望", "content": [] }
  }
}
```

## 阶段 4：策划稿（最容易跳过的关键步骤）

把 `outline.json` 的每一页转化成具体的 layout 选型 + 槽位填充。输出到 `<ws>/layout.json`。

**完整布局指南、选型规则、槽位 schema 见 [reference/bento-layouts-guide.md](reference/bento-layouts-guide.md)**。

6 种 Bento 布局（速查）：

| layout | 适合 | viewBox 用法 |
|---|---|---|
| `single-focus` | 1 个核心数字 / 1 张大图 / 1 句金句 | 1 个大卡片占满 |
| `two-col-symmetric` | 对比、并列两个概念 | 2 张等宽卡片 |
| `two-col-asymmetric` | 主内容 + 数据/图片辅助 | 2/3 + 1/3 |
| `three-col` | 三步流程、三个特性 | 3 张等宽卡片 |
| `major-minor` | 1 个主信息 + 2-3 个支撑细节 | 中央大卡 + 侧边小卡 |
| `hero-top` | 顶部一句话 + 下方多个要点 | 横幅 + 2-4 等宽卡片 |
| `mixed-grid` | 内容多样、有数据有图 | 自由混合 |

每页 component 选自（在卡片内填充）：`card-hero` / `card-stat` / `card-list` / `card-quote` / `card-text` / `card-image` / `chart-bar`。详见 reference 文档。

## 阶段 5：设计渲染

确认 `layout.json` 内容质量后（中文标点、字数控制、必须信息齐全），运行：

```bash
ppt scaffold <ws>            # 渲染所有页
ppt render <ws> --page 3     # 重渲第 3 页
ppt render <ws> --theme <name>  # 切主题重渲
```

渲染前会自动跑 `lint_cn.py` 检查中文版式。命中阻断会要求重写——**这不是警告，是错误**。

## 阶段 6：截图自校

```bash
ppt shoot <ws>
```

会用 playwright headless chromium 把每页 SVG 渲染成 PNG（放到 `<ws>/shots/`），并生成 `<ws>/deck.html` 多页翻页预览（左右键翻页 + 缩略图栏）。

然后 **Read 截图**，按下面清单逐页检查：

- [ ] 文字溢出卡片边界
- [ ] 中英文之间多余空格、英文标点（应是中标点）
- [ ] 主标题被装饰元素遮挡
- [ ] 配色对比度过低（白底白字、深底深字）
- [ ] 重复元素（同一图标/装饰被复制粘贴的痕迹）
- [ ] viewBox 越界（内容跑到 1280×720 外）

发现问题：改 `layout.json` → `ppt render <ws> --page N` 单页重渲。

## 阶段 7：导出

```bash
ppt export <ws> --format pptx       # 默认：Native renderer（python-pptx 原生 shape，100% 可编辑）
ppt export <ws> --format pptx-svg   # 备选：svgBlip 注入（SVG 矢量，好看但 PowerPoint 把整页当图片对象，需手动"转换为形状"）
ppt export <ws> --format pdf        # chrome --print-to-pdf 转 deck.html
ppt export <ws> --format html       # 单文件版 deck-standalone.html
```

**`pptx`（默认 / 推荐）**：
- 用 `scripts/native_render.py` 直接渲染 PowerPoint 原生 shape
- 单击文字 → 直接进入编辑模式
- 单击卡片背景 → 拖动 / 调色 / 加边框
- 视觉妥协：无渐变 / 无装饰光斑 / 无网格纹理（"商务平面"风格），但布局结构与 SVG 版完全一致

**`pptx-svg`（备选）**：
- 现行 svgBlip OOXML 注入方案
- PowerPoint 2019+/365 显示完美矢量（保留所有渐变 / 光斑 / 网格）
- 但每页是一个 picture 对象，要右键"转换为形状"才能编辑文字（且转换会丢渐变）
- 适合"出片好看、不需要二次编辑"的场景

详见 [reference/pptx-rendering.md](reference/pptx-rendering.md)。

## CLI Reference

所有命令位于 `${CLAUDE_SKILL_DIR}/scripts/ppt.py`（如未定义，回退到 `~/.claude/skills/ppt-agent/scripts/ppt.py`）。

```bash
SKILL=${CLAUDE_SKILL_DIR:-$HOME/.claude/skills/ppt-agent}

python3 $SKILL/scripts/ppt.py new "<topic>"
python3 $SKILL/scripts/ppt.py fetch <ws>
python3 $SKILL/scripts/ppt.py scaffold <ws>
python3 $SKILL/scripts/ppt.py render <ws> [--page N] [--theme <name>]
python3 $SKILL/scripts/ppt.py shoot <ws>
python3 $SKILL/scripts/ppt.py export <ws> --format pptx|pdf|html
```

工作区根目录默认 `~/ppt-decks/`，可通过 env `PPT_DECKS_DIR` 覆盖。

每个工作区根有 `.layout` 标识文件，所有命令都会校验合法性以防误操作。

## Prerequisites

首次使用前需要 Python 依赖：

```bash
pip3 install jinja2 python-pptx playwright cairosvg lxml
playwright install chromium
```

## 添加新主题

复制 `themes/bento-tech/` 改名，按 [reference/theme-authoring.md](reference/theme-authoring.md) 修改 manifest.json + layouts/components 模板。`ppt scaffold --theme <name>` 自动识别。

## 中文版式硬约束

- 中文与英文/数字之间**不加空格**（写 `1米93` 不是 `1 米 93`）
- 用中文标点（`，。""：！？`），不用英文标点
- 这两条是 AI 生成的常见痕迹，会被一眼识破，所以 lint 阻断而不是警告

## 已知限制

- 演讲者备注、动画 / 过渡：未实现
- 数据图表（chart-bar）只是占位，复杂图表请在 layout.json 里描述清楚后人工补
- Linux 端 PowerPoint 打开 SVG 中文字体可能 fallback 到方块字，建议在 macOS/Windows 端打开
- 一次性页数建议 ≤ 30 页（playwright 截图慢）
