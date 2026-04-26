# 阶段 4：策划稿（layout.json）规范

把 outline.json 的每一页**翻译成具体布局 + 槽位 + 内容**。这是市面 AI PPT 工具普遍跳过的关键环节。

## layout.json 完整 schema

```json
{
  "theme": "bento-tech",
  "meta": {
    "title": "Dify 企业介绍",
    "subtitle": "(可选)"
  },
  "lint": {
    "no_ascii_punct": true,
    "no_cn_en_space": false
  },
  "pages": [
    {
      "page": 1,
      "name": "cover",
      "layout": "single-focus",
      "cards": [
        {
          "slot": "main",
          "component": "card-hero",
          "data": { ... }
        }
      ]
    }
  ]
}
```

字段说明：

- `theme`：选用的主题包名（缺省 `bento-tech`）
- `meta.title`：页脚显示的 deck 标题
- `lint`：覆盖 lint 默认（公众号/严苛中文场景把 `no_cn_en_space` 开成 true）
- `pages[].page`：1-based 页码
- `pages[].name`：用于生成 slides/<NN>-<name>.svg 文件名
- `pages[].layout`：6 种 Bento 布局之一
- `pages[].cards[].slot`：槽位名（必须匹配 layout 在 manifest 里声明的 slots）
- `pages[].cards[].component`：6 种 component 之一
- `pages[].cards[].data`：传给 component 的数据（每种 component 的 data schema 不同）

---

## 6 种 Bento 布局选型规则

| layout | 槽位（slot） | 适合 |
|---|---|---|
| `single-focus` | main | 1 个核心数字 / 1 句金句 / 1 张大图。**封面、章节首页、末页**首选 |
| `two-col-symmetric` | left, right | **对比 / 并列**两个概念（A vs B、前 vs 后、问题 vs 方案）|
| `two-col-asymmetric` | main(2/3), side(1/3) | **主内容 + 数据/图片辅助**（详细论点 + 关键指标）|
| `three-col` | left, middle, right | **三步流程 / 三个特性 / 三种方案对比** |
| `major-minor` | main(中央大), top, bottom, right_top, right_bottom | **1 主信息 + 2-4 支撑细节**（核心引言 + 周边数据）|
| `hero-top` | hero(顶横幅), col1, col2, col3 | **论点（顶部）+ 多个论据（下方等宽）**（章节论证页）|
| `mixed-grid` | tl, tr, bl, br | **混合内容**（数据 + 文字 + 图，自由度最高的版式）|

### 选型口诀

- 数字够大、文字够少 → `single-focus`
- 比较关系 → `two-col-symmetric` / `two-col-asymmetric`
- 步骤/特性 = 3 → `three-col`
- 1 个核心 + 多个数据点 → `major-minor`
- 章节内多论据 → `hero-top`
- 内容杂、想塞图表 → `mixed-grid`

每页只放 **1 个核心信息**——这是 sandun 的核心方法论。如果一页想塞 5 个不相关的点，拆成 5 页。

---

## 6 种 Component 速查

每种 component 的 data schema：

### card-hero（封面/金句/章节首页）

```json
{
  "eyebrow": "PRODUCT INTRO · 2026 Q2",   // 顶部小字（可选）
  "title": "主标题" | ["第一行", "第二行"],   // 字符串 = 单行；数组 = 多行
  "badges": ["PRODUCTION-READY", {"text": "BETA", "variant": "warning"}],  // 可选胶囊小标签
  "subtitle": "副标题",                     // 可选
  "footer": "底部小字",                     // 可选（非封面用）
  "meta_columns": [                         // 可选（封面专用，会覆盖 footer）：底部三栏
    {"label": "PRESENTED BY", "value": "..."},
    {"label": "DATE", "value": "..."},
    {"label": "AUDIENCE", "value": "..."}
  ],
  "deco_text": "2026 FUTURE"                // 可选：右下半透明大字装饰（H>=320 才显示）
}
```

`badges`：每项可以是字符串（默认 `accent` 色）或 `{text, variant}`，variant: `accent|success|warning|muted`。

`meta_columns`：封面用，会覆盖 footer。常用三栏：演讲人 / 日期 / 受众；或 项目名 / 版本 / 提交日期 等。

`deco_text`：3-12 字英文/数字最佳，做封面背景装饰（半透明大字）。

### card-stat（数据卡）

```json
{
  "label": "全球开发者",      // 数字含义
  "value": "180",            // 大数字
  "unit": "万+",              // 单位（可选）⚠ 只放单位（万/%/亿/ms）
  "sub_value": "10:00",       // 附加信息（可选）：时间/型号/批次等。NOT unit
  "change": "+180% YoY",      // 变化（可选）
  "change_dir": "up",         // up/down/flat，影响颜色（可选）
  "desc": "覆盖 130+ 国家"    // 辅助说明（可选）
}
```

⚠ **`unit` 只能放单位**。"04-23 10:00" 这种时间不要塞进 unit，用 `sub_value`。

### card-list（要点列表，最多 5 条）

```json
{
  "eyebrow": "顶部小字",        // 可选
  "title": "卡片大标题",        // 可选
  "accent": "success",          // 可选：'success'|'warning'|'default'，影响序号方块颜色
  "items": [
    { "title": "Workflow", "desc": "可视化编排", "highlight": true },  // highlight: 重点项
    { "title": "Agent", "desc": "工具调用框架" },
    "字符串也行"               // 简短形式
  ]
}
```

`accent` 用法：好评 / 优势 / 已完成项用 `success`（绿）；差评 / 风险 / 未完成项用 `warning`（橙）；默认 `default`（紫蓝渐变）。两栏对比布局（如好评 vs 差评）一定要用此字段做色彩区分。

`item.highlight: true`：标记当前焦点项。**只要有任何一项 highlight=true**，模板会进入"降亮模式"——非高亮项变灰、高亮项加粗 + 左侧细线。适合"3 步流程当前在哪一步""5 个特性主推哪一个"的场景。

**容量参考**（card-list 在不同 slot 下能塞多少项）：

| Slot 来源 | inner H | 有 desc 最多 | 无 desc 最多 |
|---|---|---|---|
| `single-focus.main` / `two-col-*` | 498-578 | 6 | 8 |
| `hero-top.col1/col2/col3` | 238 | 3 | 4 |
| `mixed-grid.bl/br` | 198 | **2** | 3 |
| `mixed-grid.tl/tr` | 200 | **2** | 3 |
| `hero-top.hero` | 160 | **1-2** | 2 |

**截断行为**：layout.json 写 N 项但卡装不下时，模板**优先保留所有 highlight 项**，剩余按原顺序填补。所以"重点项一定不丢"。但仍建议 AI 写 layout 时主动控制项数：放不下就拆页或换更大的 slot。

### card-stack（多数据叠加卡 — 一卡承载一组相关指标）

```json
{
  "label": "全球最大消费级 IoT 平台",
  "primary": {
    "value": "8.6",
    "unit": "亿+",                     // 可选：紧贴 value 右侧
    "suffix": "连接设备数"             // 可选：单位右侧的描述短语
  },
  "secondary": [                       // 可选：2-3 个支撑指标，横向铺
    { "label": "全球月活用户", "value": "6.86 亿" },
    { "label": "日均互联使用", "value": "4000 万次" }
  ],
  "progress": {                        // 可选：底部进度条
    "percent": 95,                     // 0-100
    "label": "覆盖 95% 以上生活场景"
  },
  "badges": [...]                      // 可选
}
```

**何时用 card-stack 而不是 card-stat**：当一张卡需要承载"主数据 + 2-3 个相关支撑数据 + 完成度"时。例：用户画像、性能指标组、销售达成情况。一张 card-stack ≈ 3-4 张 card-stat 的信息量，但视觉更集中。

### card-quote（引言）

```json
{
  "quote": "AI 应用的瓶颈不是模型，而是工程化。",
  "author": "Dify 创始团队",   // 可选
  "role": "2024 技术分享会"     // 可选
}
```

### card-text（段落文本）

```json
{
  "eyebrow": "顶部小字",                 // 可选
  "title": "标题",                       // 可选
  "badges": ["资本市场", {"text": "已跌停", "variant": "warning"}],  // 可选
  "paragraphs": [
    "第一段。",
    "第二段。"
  ]
}
```

⚠ paragraphs 用粗暴的字符宽度估算换行，**单段建议 ≤ 80 字**。多了就拆段或拆页。

### card-image（图片）

```json
{
  "title": "界面预览",        // 顶部小字（可选）
  "src": "/abs/path.png",    // 图路径（缺省 = 渲染占位框）
  "alt": "Workflow 编排画布",
  "caption": "图下方说明"     // 可选
}
```

### chart-bar（水平柱状图，最多 6 条）

```json
{
  "title": "模型调用量月环比",
  "items": [
    { "label": "GPT-4", "value": 42, "unit": "亿", "color": "#7c5cff" }
  ]
}
```

---

## 翻译流程（从 outline.json → layout.json）

1. **总览大纲**：算总页数 = 1 + 1 + sum(part 内页数) + 1
2. **逐页定位**：
   - 封面 / 目录 / 末页 → `single-focus`
   - 每个 part 的第一页 → 一般用 `hero-top` 或 `single-focus`（章节首页）
   - part 内常规页 → 看内容选布局
3. **每页 → 选 layout → 定 slot 内容**：把 outline 里那一页的 `content` 拆到对应 slot
4. **写完所有页**：跑 `python3 scripts/lint_cn.py layout.json` 检查中文版式
5. **scaffold 渲染**：`ppt scaffold <ws>`

## 反模式（避免）

- ❌ 一页塞 5 个不相关的点 → 拆成 5 页
- ❌ 全 deck 都用 single-focus → 视觉单调，每章至少换 2 种 layout
- ❌ card-text 段落 > 80 字 → 文字会溢出卡片边界
- ❌ card-stat 的 value 超过 6 字符（如 "1234567"）→ 大字号塞不下，改用单位或科学计数（"1.2M"）
- ❌ chart-bar items > 6 → 拆成两页或换非水平条形的呈现
- ❌ **mixed-grid 4 个槽全塞复合 component**（card-list / card-stack / card-text 同时上）→ 信息密度爆表，可读性骤降。如果一页确实需要 4 块独立信息，要么：
  - 用 `single-focus` 强调一个核心 + 拆出第二页放剩余
  - mixed-grid 里**至少一个 slot 用 card-stat / card-image / card-quote**（"轻"组件）做留白
  - 改用 `hero-top`，顶横幅 + 下方 3 列轻组件，比 mixed-grid 4 槽更易读
- ❌ **多列同时给 highlight**（每列 card-list 都有 highlight=true）→ 跨列对比会凸显这些 highlight 项，确认它们确实是"读者最该看的"再用；如果只是想强调每列的"第一项"，不必都加 highlight

## 何时拆页

发生以下任一就拆：

- mixed-grid 4 槽都用了"复合"组件（card-text / card-list / card-stack）
- 一页要回答 ≥ 2 个独立问题
- 用 card-text 时单段超 80 字 + 同页还有其他 component
- card-list items > 5（自动会被截断到 5）
