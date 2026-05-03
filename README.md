# bento-ppt-skill

A Claude Code skill that turns a topic or document into a 16:9 SVG slide deck in **Bento Grid** style — with HTML preview and editable PowerPoint export.

灵感来自 sandun [《应该是目前最强的 PPT Agent，附上完整思路分享》](https://linux.do/t/topic/1782304)。把作者的"四步流水线 + Bento Grid 卡片布局 + 整页 SVG"方法论工程化成一个可复用的 Claude Code skill。

![cover](examples/dify-intro/shots/01-cover.png)
![data page](examples/dify-intro/shots/05-major-minor-demo.png)
![mixed grid](examples/dify-intro/shots/07-mixed-grid-demo.png)

## Features

- **7 阶段流水线**：needs（反问） → research → outline（金字塔原理） → planning → fetch → design → review → export
- **6 种 Bento 布局** + **9 种卡片组件**：single-focus / two-col-symmetric / two-col-asymmetric / three-col / major-minor / hero-top / mixed-grid 任选；卡内可放 card-hero / card-stat / **card-stack**（多数据叠加）/ card-list（highlight 焦点项）/ card-quote / card-text / card-image / **card-compare**（多列对比表）/ chart-bar
- **跨组件装饰元素**：胶囊 badges / 三栏 metadata / 半透明装饰大字 / **ghost_text 背景装饰字** / 网格背景纹理
- **双主题**：`bento-tech`（深色科技风）/ `bento-light`（浅色商务风），主题继承机制让新主题只需一个 manifest.json
- **底层 SVG**（viewBox `0 0 1280 720`），双 PPTX 导出路径：
  - **Native**（默认）：`scripts/native_render.py` 用 python-pptx 直接画原生 shape，**100% 可编辑**（单击文字直接改、无需"转换为形状"）。视觉商务平面（无渐变 / 光斑）
  - **SVG**（备选 `--format pptx-svg`）：通过 `asvg:svgBlip` OOXML 注入到 pptx，PowerPoint 2019+/Office 365 显示完美矢量但默认是 picture 对象
- **HTML 翻页预览**：左右键 / 缩略图栏 / 全屏，在浏览器里直接放映
- **图片 provider 协议**：可插拔的 `url_download` / `nanobanana` / `unsplash`，AI 自己决定用搜还是生
- **中文版式 lint**：默认拦截英文标点（公众号/严苛场景可开"中英不空格"）

## Install

```bash
git clone https://github.com/YingYveltal/bento-ppt-skill.git ~/.claude/skills/ppt-agent
pip3 install jinja2 python-pptx lxml
```

可选（看你机器上有没有）：

```bash
# 截图依赖：自动探测 Chrome / Chromium / Edge / Brave，找不到再装
# 不依赖 playwright
```

## Use

**新开** Claude Code 窗口（让 description 自动加载），直接说自然语言：

```
帮我做一份 6-8 页的 X 主题 PPT
```

```
把 ./report.md 转成发布会 deck
```

Claude 会自动加载 ppt-agent skill，反问受众/调性/页数，然后跑完 7 阶段流程。产物在 `~/ppt-decks/<date>-<slug>/`：

- `slides/*.svg` — 每页 SVG 矢量
- `deck.html` — 浏览器翻页预览
- `deck.pptx` — PowerPoint 可编辑
- （可选）`deck.pdf`

## Manual CLI

```bash
SKILL=~/.claude/skills/ppt-agent

python3 $SKILL/scripts/ppt.py new "<topic>"
python3 $SKILL/scripts/ppt.py fetch <ws>      # 可选，下载/生成 card-image
python3 $SKILL/scripts/ppt.py scaffold <ws>    # SVG 渲染
python3 $SKILL/scripts/ppt.py shoot <ws>       # 截图 + deck.html
python3 $SKILL/scripts/ppt.py export <ws> --format pptx
```

## Sample

`examples/dify-intro/` 是端到端样本：

- 8 页 deck，覆盖全部 6 种 Bento 布局
- 含 layout.json（输入）、slides/SVG（产物）、shots/PNG（截图）、deck.pptx
- 直接 `open examples/dify-intro/deck.html` 看翻页效果

## 延展开发（Layout / Component / Theme）

完整的接力开发规范见 **[reference/extension-guide.md](reference/extension-guide.md)**，涵盖：

- 新增 Layout：只改 manifest.json，零代码
- 新增 Component：写 1 个 SVG 模板 + 1 个 native 方法
- 新增 Theme：只需 manifest.json，模板自动继承

## 添加新风格

```bash
# 只需创建 manifest.json，模板自动从 bento-tech 继承
mkdir themes/<your-style>
# 复制 bento-tech 或 bento-light 的 manifest.json，修改颜色 / 字号
```

详见 [reference/extension-guide.md](reference/extension-guide.md)。

## 添加新图片 provider

```bash
# 在 scripts/providers/ 下新建一个 .py 文件
# 实现 ImageProvider 接口 + 末尾 register(YourProvider())
# 自动被 fetch 阶段发现
```

详见 [scripts/providers/README.md](scripts/providers/README.md)。

## Architecture

```
ppt-agent/
├── SKILL.md                       # skill 入口（Claude 自动加载）
├── reference/                     # 渐进披露文档（需要时再读）
│   ├── extension-guide.md         # Layout / Component / Theme 延展规范（接力开发必读）
│   ├── bento-layouts-guide.md     # 6 种布局 + component data schema
│   ├── pyramid-outline-prompt.md  # sandun 开源的金字塔原理 prompt
│   ├── image-providers.md         # AI 怎么写 src / source
│   ├── pptx-rendering.md          # 双 Renderer 路线（native vs svgBlip）
│   └── theme-authoring.md         # 加新主题（简版）
├── scripts/
│   ├── ppt.py                     # 主 CLI
│   ├── render.py                  # SVG 装配 (jinja2 + 主题继承)
│   ├── native_render.py           # Native PPTX 渲染（python-pptx，100% 可编辑）
│   ├── shoot.py                   # Chrome headless 截图 + deck.html
│   ├── export.py                  # SVG → PPTX (svgBlip 备选路线)
│   ├── fetch.py                   # 图片 provider 调度
│   ├── lint_cn.py                 # 中文版式硬约束
│   └── providers/                 # 可插拔图片 provider
│       ├── url_download.py        # 内置（无 API key）
│       ├── nanobanana.py          # Gemini Image (stub)
│       └── unsplash.py            # Unsplash (stub)
├── themes/
│   ├── bento-tech/                # 深色科技风（默认）：渐变光斑 + 玻璃拟态卡片
│   │   ├── manifest.json          # 设计 token + layout 槽位元数据
│   │   ├── slide-base.svg.j2      # 1280×720 容器（背景 / defs / ghost_text / 页脚）
│   │   ├── layouts/_base.svg.j2   # 数据驱动通用 layout
│   │   └── components/            # 9 种 component 模板
│   └── bento-light/               # 浅色商务风：只有 manifest.json，模板继承 bento-tech
└── examples/
    └── dify-intro/                # 端到端跑通样本（8 页，覆盖全部布局）
```

## Credit

- 方法论：[sandun @ linux.do](https://linux.do/t/topic/1782304) — 四步流水线 + Bento Grid + 整页 SVG
- skill 框架：[Anthropic Claude Code](https://code.claude.com/docs/en/skills.md)
- 实现：Claude (Opus 4.7) + 我

## License

MIT
