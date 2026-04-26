# PPTX 双 Renderer 路线说明

ppt-agent 有两条 PPTX 导出路线，对应不同需求。

## 速查

| 路线 | 命令 | 视觉效果 | PowerPoint 可编辑性 | 文件大小 |
|---|---|---|---|---|
| **Native**（默认） | `ppt export <ws> --format pptx` | 商务平面（无渐变 / 光斑 / 网格纹理） | ✅ 100%，单击文字直接改 | ~50KB / 8 页 |
| **SVG (svgBlip)** | `ppt export <ws> --format pptx-svg` | 完美保留 SVG 渐变 / 光斑 / 玻璃拟态 | ❌ 默认不能改，需右键"转换为形状"且转换会丢渐变 | ~3MB / 8 页 |

**默认推荐 Native**。要"出片好看、给 PM 看完不改"，用 SVG 路线。

---

## Native 路线（推荐）

### 工作原理

`scripts/native_render.py` 的 `NativeRenderer`：
1. 读 `layout.json`（结构）+ `theme manifest`（colors / fonts / spacing / layouts.slots）
2. 用 `python-pptx` API 直接画原生 PowerPoint shape：
   - 卡片 → `add_shape(MSO_SHAPE.ROUNDED_RECTANGLE)`
   - 文字 → `add_textbox()` + 设字体 / 字号 / 颜色 / 加粗
   - 进度条 → 两个 `add_shape` rectangle 叠加
   - badges → 圆角矩形 + 内部 textbox
   - 装饰大字（半透明）→ textbox + lxml 改 `<a:rPr>` 加 alpha

### 可编辑性

打开 deck.pptx 后：
- 单击任意文字 → 直接进入编辑模式（**无需"转换为形状"**）
- 单击任意卡片背景 → 拖动 / 调色 / 加边框
- 字体名称、颜色、字号都在 PowerPoint Format 面板可见
- badges、进度条、装饰条都是独立的 shape，可单独点选

### 视觉妥协（"商务平面"风格）

不渲染：
- 装饰光斑（径向渐变）
- 网格纹理 pattern
- 玻璃拟态半透明渐变
- 大引号字符装饰

**接受这些妥协的原因**：python-pptx 对 gradient / pattern fill 支持不完整。要硬上要直接写 OOXML XML，工作量极大且兼容性差。**可编辑是硬要求，视觉是次要的**。

完整保留：
- 卡片圆角矩形 + 描边
- 所有文字字体属性
- 序号方块（card-list）
- 进度条（card-stack）
- 左侧主题色竖条（card-quote / card-list highlight）
- 三栏 metadata（card-hero）
- badges
- 装饰大字（半透明文本）

### 字体回退

模板用 PingFang SC。Windows PowerPoint 没有此字体会回落到默认字体（Yahei / Arial）。建议在 manifest.fonts.sans 里同时声明备用字体（已默认带 Microsoft YaHei / SF Pro / Inter）。

---

## SVG 路线（svgBlip 注入）

### 工作原理

`scripts/export.py` 的 `to_pptx_svg`：
1. 用 shoot 截好的 PNG 全屏铺底（rId2，作为 fallback）
2. 找到 `<a:blip>` 元素
3. 把对应 SVG 文件作为新 ImagePart 加入 slide rels（rId3）
4. 注入：

```xml
<a:blip r:embed="rIdN_to_PNG">
  <a:extLst>
    <a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}">
      <asvg:svgBlip
        xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main"
        r:embed="rIdM_to_SVG"/>
    </a:ext>
  </a:extLst>
</a:blip>
```

### PowerPoint 行为

| 版本 | 显示 | 可编辑性 |
|---|---|---|
| PowerPoint 365 / 2019+ Win/Mac | 优先渲染 SVG 矢量（完美） | 整页是 picture 对象。要点选改文字必须右键"转换为形状"，转换后渐变 / 光斑 / 网格 / pattern 多半丢失 |
| PowerPoint 2016 | 回落 PNG（不识别 svgBlip） | 完全不可编辑（PNG 图片）|
| WPS | 视版本，部分支持 SVG | 与 PowerPoint 同 |
| Keynote | 部分支持 SVG | 与 PowerPoint 同 |

### 怎么验证

```bash
unzip -o deck.pptx -d /tmp/check/
ls /tmp/check/ppt/media/  # 应有 image*.png + svg-deck-*.svg
grep -c svgBlip /tmp/check/ppt/slides/slide*.xml  # 每页 1 个
```

---

## 选哪个？

- **要给客户/PM 看完拿走自己改文字、调色、加备注** → Native
- **要给设计稿一样的视觉效果，不需二次编辑** → SVG
- **同时要两个产物** → 跑两次 export，命令不同：
  ```bash
  ppt export <ws> --format pptx        # deck.pptx (native)
  ppt export <ws> --format pptx-svg    # 会覆盖 deck.pptx
  ```
  注意当前两条路径都写到同一个 `deck.pptx`，建议改名后再跑第二次。

## V3 待做

- 用 lxml 直接写 OOXML `<a:gradFill>`，让 Native 路线也能渲染渐变
- 装饰光斑用大圆 shape + 透明度近似
- pattern fill 网格纹理（PowerPoint 支持有限，可能放弃）
