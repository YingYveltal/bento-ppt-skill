# 布局与渲染延展规范

> 本文面向接力开发者或共创者。阅读完可以独立新增 **Layout（布局）**、**Component（组件）** 或 **Theme（主题）**，无需改动核心引擎代码。

---

## 一、架构契约（必读）

```
layout.json          ← AI 写的"策划稿"，唯一输入
     │
     ├─→ theme manifest.json   设计 Token（颜色 / 字号 / 间距 / 槽位坐标）
     │
     ├─→ SVG Renderer          jinja2 模板 → slides/*.svg → HTML 预览 / PDF
     │    scripts/render.py
     │    themes/<theme>/slide-base.svg.j2
     │    themes/<theme>/layouts/_base.svg.j2（或专属 layout 模板）
     │    themes/<theme>/components/<name>.svg.j2
     │
     └─→ Native Renderer       python-pptx → deck.pptx（100% 可编辑）
          scripts/native_render.py
          NativeRenderer._render_<component>()
```

**核心原则**：

| 原则 | 含义 |
|---|---|
| 契约分离 | layout.json 只描述"放什么"，不涉及像素 |
| 双 Renderer 对等 | 每个 component 必须同时实现 SVG 模板 + Native 方法 |
| Token 驱动 | 颜色 / 字号 / 圆角全部从 `theme.colors.*` / `theme.type_scale.*` 读取，禁止硬编码 |
| Theme 继承 | 派生主题只需 `manifest.json`，模板自动 fallback 到 `bento-tech` |

---

## 二、新增 Layout（布局）

Layout = 若干具名槽位（slot）的几何定义。所有 layout 逻辑在 `manifest.json` 里，一行代码都不用写。

### 2.1 在 manifest.json 里注册

在所有想用这个 layout 的主题的 `manifest.json` 里加一个 `layouts.<name>` 条目：

```json
"two-row-stack": {
  "card_count": 3,
  "description": "上方宽条 + 下方两等宽，适合时间线/流程大图 + 两个数据点",
  "slots": {
    "top":   { "x": 56,  "y": 56,  "w": 1168, "h": 320 },
    "left":  { "x": 56,  "y": 396, "w": 574,  "h": 238 },
    "right": { "x": 650, "y": 396, "w": 574,  "h": 238 }
  }
}
```

**坐标规范**：
- 画布 `1280 × 720`
- 页边距 = `spacing.page_padding`（默认 56）
- 卡片之间的间隔 = `spacing.card_gap`（默认 20）
- 全部卡片不得超出 `y = 690`（下方留 30px 给页脚）
- 同一 layout 里所有槽位面积之和建议 ≥ 画布的 70%，否则视觉太空

### 2.2 可选：写专属 layout SVG 模板

如果 layout 需要额外装饰（例如：时间线连接线、步骤序号气泡），在：

```
themes/<theme>/layouts/<layout-name>.svg.j2
```

写专属模板。模板会被 render.py **优先于** `_base.svg.j2` 使用。

```jinja2
{# 专属 layout 模板示例：带连接线的 three-col #}
{%- set slot_defs = theme.layouts[page.layout].slots -%}

{# 在 left.middle right 之间画连接箭头 #}
{%- set lx = slot_defs.left.x + slot_defs.left.w -%}
{%- set rx = slot_defs.right.x -%}
{%- set cy = slot_defs.left.y + slot_defs.left.h // 2 -%}
<line x1="{{ lx }}" y1="{{ cy }}" x2="{{ rx }}" y2="{{ cy }}"
      stroke="{{ theme.colors.accent_primary }}" stroke-opacity="0.4"
      stroke-width="2" stroke-dasharray="6 4"/>

{# 再把 _base 的卡片渲染逻辑复制进来（或 include 它）#}
{% include "layouts/_base.svg.j2" %}
```

### 2.3 更新文档

在 `reference/bento-layouts-guide.md` 的布局表格里追加一行。

### 2.4 Native Renderer 无需改动

native_render.py 用 `self.theme["layouts"][layout_name]["slots"]` 读几何，新 layout 自动支持。

---

## 三、新增 Component（组件）

Component = 一种内容类型的可视化。需要**同时**完成两件事：

```
① themes/bento-tech/components/<name>.svg.j2   SVG Renderer 用
② native_render.py  NativeRenderer._render_<name>()  Native Renderer 用
```

### 3.1 SVG 模板（① 必须）

模板接收以下变量：

| 变量 | 说明 |
|---|---|
| `data` | layout.json 该 card 的 `data` 字段 |
| `theme` | 当前主题 manifest dict（colors / type_scale / spacing / fonts） |
| `slot_w` | 内容区宽度（slot.w − card_padding × 2） |
| `slot_h` | 内容区高度（slot.h − card_padding × 2） |

模板输出坐标系是 `(0, 0)` 到 `(slot_w, slot_h)` 的相对坐标（已由 `_base.svg.j2` 用 `<svg x=... y=...>` 映射到绝对位置）。

**标准模板骨架**：

```jinja2
{# card-<name>：一句话说这个组件干什么
   data:
     eyebrow  string?   顶部小字
     title    string?   主标题
     ...      其他字段
#}
{%- set d = data -%}
{%- set H = slot_h or 500 -%}
{%- set W = slot_w or 600 -%}

{# ---- 头部区（eyebrow + title）---- #}
{%- set y = namespace(p=0) -%}

{%- if d.eyebrow -%}
{%- set y.p = y.p + theme.type_scale.eyebrow + 4 -%}
<text x="0" y="{{ y.p }}" class="eyebrow">{{ d.eyebrow }}</text>
{%- endif -%}

{%- if d.title -%}
{%- set y.p = y.p + theme.type_scale.h3 + 18 -%}
<text x="0" y="{{ y.p }}" class="h3">{{ d.title }}</text>
{%- set y.p = y.p + 16 -%}
{%- endif -%}

{%- if not d.eyebrow and not d.title -%}{%- set y.p = 4 -%}{%- endif -%}

{# ---- 主体内容（在 y.p 以下渲染）---- #}
{# ...你的内容... #}
```

**可用 CSS 类**（在 `slide-base.svg.j2` 的 `<style>` 里定义）：

| 类 | 字号 | 颜色 |
|---|---|---|
| `.eyebrow` | eyebrow | accent_secondary，letter-spacing 3px |
| `.h1 .h2 .h3 .h4` | h1~h4 | text_primary |
| `.body` | body | text_secondary |
| `.small` | small | text_muted |
| `.stat-huge` | stat_huge | text_primary |
| `.stat-unit` | stat_unit | text_secondary |

渐变 id（在 `slide-base.svg.j2` 的 `<defs>` 里）：

- `url(#accent-grad)` — 横向主题色渐变（accent_primary → accent_secondary）
- `url(#accent-grad-v)` — 纵向渐变
- `url(#spot-1)` / `url(#spot-2)` — 径向光斑

### 3.2 Native 渲染方法（② 必须）

在 `NativeRenderer` 里添加 `_render_card_<name>(self, slide, inner, data)`。

方法命名规则：`card-flow` → `_render_card_flow`，`chart-radar` → `_render_chart_radar`。

`inner` 结构：

```python
inner = {
    "x": slot["x"] + card_padding,   # 内容区左上角 SVG x
    "y": slot["y"] + card_padding,   # 内容区左上角 SVG y
    "w": slot["w"] - card_padding*2, # 内容区宽度（SVG 单位）
    "h": slot["h"] - card_padding*2, # 内容区高度（SVG 单位）
}
```

**标准方法骨架**：

```python
def _render_card_<name>(self, slide, inner: dict, data: dict) -> None:
    H, W = inner["h"], inner["w"]
    ts = self.theme["type_scale"]
    c  = self.theme["colors"]
    
    # --- 头部（eyebrow + title，共用逻辑）---
    y = 0
    if data.get("eyebrow"):
        self._add_textbox(
            slide, data["eyebrow"],
            inner["x"], inner["y"] + y - 4, W, ts["eyebrow"] + 6,
            font_size=ts["eyebrow"], color=c["accent_secondary"],
            bold=True, letter_spacing=300,
        )
        y += ts["eyebrow"] + 18
    if data.get("title"):
        self._add_textbox(
            slide, data["title"],
            inner["x"], inner["y"] + y - int(ts["h3"] * 0.15), W, ts["h3"] + 8,
            font_size=ts["h3"], color=c["text_primary"], bold=True,
        )
        y += ts["h3"] + 22
    
    # --- 主体内容 ---
    content_y = y + 8
    # ... 你的内容 ...
```

**常用工具方法速查**：

| 方法 | 用途 |
|---|---|
| `_add_textbox(slide, text, x, y, w, h, *, font_size, color, bold, align, word_wrap)` | 文本框（SVG 坐标） |
| `_add_card_bg(slide, slot)` | 圆角卡片背景（自动读 theme 颜色） |
| `_set_solid_fill(shape, color_hex, opacity)` | 填充颜色 + 透明度（用 lxml 写入 OOXML） |
| `_set_line_alpha(shape, color_hex, opacity, width_pt)` | 描边颜色 + 透明度 |
| `_render_badges(slide, badges, svg_x, svg_y)` | 一排胶囊 badge |
| `_add_solid_rect(slide, x, y, w, h, color_hex)` | 不透明纯色矩形（用于强调条） |
| `_add_image_placeholder(slide, inner, y_top, img_h, alt)` | 图片占位框 |
| `_x(svg_x)` / `_y(svg_y)` | SVG 坐标 → EMU 坐标转换 |

**关于 `word_wrap`**：
- 数字 / 单行值 → `word_wrap=False`（防止 PowerPoint 将 "180%" 截为 "180" + "%"）
- 普通文字 → `word_wrap=True`（默认）

### 3.3 更新 bento-layouts-guide.md

在"6 种 Component 速查"小节追加新组件的 data schema 说明（参照现有格式）。

### 3.4 如果 component 要在 bento-light 里表现不同

bento-light 使用同一套 SVG 模板（继承），只需在组件模板里对 `theme.colors.*` 用条件判断：

```jinja2
{%- set is_light = (theme.colors.bg_start | first) == '#F' -%}
{# 浅色主题下给背景用深色 #}
<rect fill="{{ '#000000' if is_light else '#ffffff' }}" fill-opacity="0.04"/>
```

> 更好的做法：在 manifest 里加一个 `"is_light": true` 语义字段供模板读取。

---

## 四、新增 Theme（主题）

### 4.1 目录结构

```
themes/
└── <your-theme>/
    └── manifest.json        ← 唯一必须文件
    [可选覆盖的模板文件]
```

所有 `.svg.j2` 模板自动从 `bento-tech` 继承，只需覆盖你想改的文件。

### 4.2 manifest.json 必填字段

```json
{
  "name": "your-theme",
  "version": "1.0.0",
  "description": "一句话描述风格和调性",
  "viewBox": { "width": 1280, "height": 720 },
  "fonts": {
    "sans": "...",
    "mono": "...",
    "display": "..."
  },
  "type_scale": {
    "eyebrow": 16, "h1": 60, "h2": 44, "h3": 30, "h4": 22,
    "body": 18,   "small": 14,
    "stat_huge": 110, "stat_unit": 28
  },
  "colors": {
    "bg_start":            "#...",   "bg_end":              "#...",
    "card_fill":           "#...",   "card_fill_opacity":   0.06,
    "card_stroke":         "#...",   "card_stroke_opacity": 0.12,
    "text_primary":        "#...",   "text_secondary":      "#...",
    "text_muted":          "#...",
    "accent_primary":      "#...",   "accent_secondary":    "#...",
    "accent_tertiary":     "#...",
    "accent_success":      "#...",   "accent_warning":      "#..."
  },
  "spacing": {
    "page_padding": 56,
    "footer_height": 30,
    "card_padding": 40,
    "card_gap": 20,
    "card_radius": 20,
    "card_stroke_width": 1
  },
  "effects": {
    "bg_texture":       "grid",       "bg_texture_opacity": 0.08,
    "bg_texture_size":  48,           "bg_texture_color":   "#ffffff",
    "bg_spot_opacity":  0.4
  },
  "layouts": { ... }   ← 复制 bento-tech 的 layouts 块
}
```

**颜色设计要点**：

| 场景 | 深色主题 | 浅色主题 |
|---|---|---|
| `card_fill_opacity` | 0.04~0.08（白色打在深色背景 = 半透明玻璃感） | 0.65~0.85（白/浅色卡片） |
| `card_stroke_opacity` | 0.10~0.15 | 0.06~0.12 |
| `bg_texture_color` | `"#ffffff"` | `"#1a1a2e"`（深色线条） |
| `bg_spot_opacity` | 0.35~0.50 | 0.08~0.15（避免太亮） |
| eyebrow（accent_secondary） | 亮蓝/亮青（在深底上读得清） | 深蓝/深紫（在浅底上读得清） |

### 4.3 Native Renderer 的颜色对应

native_render.py 直接读 `self.theme["colors"]`，无需改代码。唯一例外：
- `_render_card_hero` 的 `badge_text`（序号文字颜色）固定为 `"#0a0e27"`。深色 accent 背景 + 深色文字在浅色主题里会不可读。建议在组件里判断 `theme.colors.bg_start` 亮度后选 `"#0a0e27"` 或 `"#ffffff"`。

---

## 五、测试清单

每次新增 layout / component / theme 后，依次跑以下命令：

```bash
SKILL=~/.claude/skills/ppt-agent

# 1. SVG 渲染（快速冒烟）
python3 $SKILL/scripts/render.py   # 无 ws 参数时直接报帮助，改为：
python3 -c "
from scripts.render import render_all
from pathlib import Path
print(render_all(Path('examples/dify-intro')))
"

# 2. 中文版式 lint（如有中文内容）
python3 $SKILL/scripts/lint_cn.py <ws>/layout.json

# 3. Native PPTX 渲染
python3 -c "
from scripts.native_render import render_pptx
from pathlib import Path
render_pptx(Path('<ws>'), theme_name='bento-tech', out_path=Path('/tmp/test.pptx'))
print('OK')
"

# 4. 截图视觉验证（需要 Chrome）
python3 $SKILL/scripts/ppt.py shoot <ws>

# 5. 在 PowerPoint / Keynote 打开 deck.pptx 手动验证
#    - 单击文字 → 进入编辑模式（不需要"转换为形状"）
#    - 单击卡片背景 → 能拖动、调色
```

**视觉验证检查项**：

```
□ 文字没有溢出卡片边界
□ 数字值没有被换行截断（word_wrap=False）
□ highlight 项在 card-list 里左侧竖条对齐内容区顶部
□ 全部 slot 都有渲染内容（无"slot not found"红色警告框）
□ 深色 + 浅色主题各跑一次
□ Native PPTX 里所有文字直接可点选编辑
```

---

## 六、设计规范（保持视觉一致性）

### 信息密度

| 指标 | 限制 |
|---|---|
| 单页核心信息数 | 1 个（多了拆页） |
| card-list items | ≤ 5（超出自动截断）|
| card-text 单段字数 | ≤ 80 字 |
| card-stat value 字符数 | ≤ 6 字符（"1.2M" 而非 "1234567"）|
| chart-bar items | ≤ 6 条 |
| card-compare 列数 | 2~3 列；行数 ≤ 6 |

### 颜色使用

- **accent 颜色**只用于强调（eyebrow、badge、高亮项），不用于普通正文
- `accent_success`（绿）= 好评 / 优势 / 已完成；`accent_warning`（橙）= 风险 / 差评 / 待办
- 同一页里 `card-list` 的 `accent` 字段：对比两列时左列 success + 右列 warning

### 字体层级

```
eyebrow  →  辅助分类 / 页面标签（全大写，letter-spacing 3px）
h3       →  卡片主标题（大多数 component 的标题级别）
h4       →  子标题 / 表格列头
body     →  正文 / 列表描述
small    →  辅助说明 / caption / 页脚
```

### 间距节奏

- eyebrow → title 间距：约 `eyebrow_size + 14`（18~20px）
- title → 内容区间距：约 `24~32px`
- 列表行高（有 desc）：`44px`；无 desc：`32px`

### layout 视觉节奏（deck 级别）

- 避免连续 3 页使用同一 layout（单调）
- 封面 / 末页首选 `single-focus`
- 每章至少用 2 种不同 layout
- 深色主题建议间隔穿插 `bento-light` 章节首页（切换气氛）

---

## 七、文件地图（快速定位）

```
ppt-agent/
├── reference/
│   ├── extension-guide.md       ← 本文档
│   ├── bento-layouts-guide.md   ← layout + component data schema 速查
│   └── pptx-rendering.md        ← 双 renderer 路线说明
├── themes/
│   ├── bento-tech/
│   │   ├── manifest.json        ← 深色主题 token（修改此文件影响所有深色产出）
│   │   ├── slide-base.svg.j2    ← SVG 容器 + 背景 + 页脚
│   │   ├── layouts/
│   │   │   ├── _base.svg.j2     ← 通用 layout（大多数情况不需要动）
│   │   │   └── *.svg.j2         ← 专属 layout 模板（有额外装饰才需要）
│   │   └── components/
│   │       └── card-*.svg.j2    ← 每个 component 一个文件
│   └── bento-light/
│       └── manifest.json        ← 浅色主题 token（模板全继承自 bento-tech）
├── scripts/
│   ├── render.py                ← SVG 渲染引擎（不需要改）
│   ├── native_render.py         ← Native PPTX 渲染（新增 component 在此加方法）
│   ├── ppt.py                   ← CLI 入口
│   └── lint_cn.py               ← 中文版式检查
└── examples/
    └── dify-intro/              ← 端到端参考样本
        └── layout.json          ← 参考写法
```
