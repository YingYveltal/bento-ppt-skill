"""SVG 装配引擎：layout.json + theme + jinja2 模板 → slides/*.svg。

渲染流程：
1. 读 layout.json（每页指定 layout 类型 + 槽位 component + data）
2. 加载主题：themes/<theme>/manifest.json + jinja2 env（FileSystemLoader 指向 theme 目录）
3. 对每页：
   a. 渲染每个 card 的 component（components/<name>.svg.j2 → SVG fragment 字符串）
   b. 渲染 layout（layouts/<name>.svg.j2，把 cards fragment 拼到对应槽位）
   c. 渲染 slide-base（slide-base.svg.j2，把 layout fragment 注入背景容器）
4. 写 slides/<NN>-<slug>.svg，渲染前过 lint_cn 阻断检查

layout.json schema（核心字段）：
{
  "theme": "bento-tech",
  "meta": { "title": "Dify 企业介绍" },
  "pages": [
    {
      "page": 1,
      "name": "cover",
      "layout": "single-focus",
      "cards": [
        { "slot": "main", "component": "card-hero",
          "data": { "eyebrow": "...", "title": "...", "subtitle": "...", "footer": "..." } }
      ]
    }
  ]
}
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))

SKILL_DIR = Path(os.environ.get("CLAUDE_SKILL_DIR", str(Path.home() / ".claude/skills/ppt-agent"))).resolve()


def slugify(name: str) -> str:
    s = re.sub(r"[\s/\\:*?\"<>|]+", "-", name.strip())
    s = re.sub(r"-+", "-", s).strip("-")
    return (s or "untitled").lower()


def load_theme(theme_name: str):
    """返回 (manifest dict, jinja2 Environment)。"""
    theme_dir = SKILL_DIR / "themes" / theme_name
    if not theme_dir.is_dir():
        raise SystemExit(
            f"[render] 找不到主题: {theme_dir}\n"
            f"  现有主题: {[p.name for p in (SKILL_DIR / 'themes').iterdir() if p.is_dir()]}"
        )
    manifest_path = theme_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"[render] 主题缺 manifest.json: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # 支持主题继承：派生主题目录只需 manifest.json，模板 fallback 到 bento-tech
    loader_paths = [str(theme_dir)]
    base_dir = SKILL_DIR / "themes" / "bento-tech"
    if theme_name != "bento-tech" and base_dir.is_dir():
        loader_paths.append(str(base_dir))
    env = Environment(
        loader=FileSystemLoader(loader_paths),
        autoescape=True,  # data 里用户字符串自动 escape XML 特殊字符；SVG 嵌套用 | safe 透传
        keep_trailing_newline=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return manifest, env


def render_card(env: Environment, manifest: dict, card: dict, slot_w: int = 0, slot_h: int = 0) -> str:
    """渲染单个 card 的 component 为 SVG fragment。"""
    comp_name = card.get("component")
    if not comp_name:
        return ""
    tpl_path = f"components/{comp_name}.svg.j2"
    try:
        tpl = env.get_template(tpl_path)
    except Exception as e:
        raise SystemExit(f"[render] 找不到 component 模板: {tpl_path} ({e})")
    return tpl.render(
        theme=manifest,
        data=card.get("data", {}),
        slot=card.get("slot"),
        slot_w=slot_w,
        slot_h=slot_h,
    )


def render_one_page(env: Environment, manifest: dict, page: dict, total_pages: int, meta: dict) -> str:
    """渲染单页 → 完整 SVG 字符串。"""
    layout_name = page.get("layout")
    if not layout_name:
        raise SystemExit(f"[render] 第 {page.get('page')} 页缺 layout 字段")
    layout_meta = manifest.get("layouts", {}).get(layout_name)
    if not layout_meta:
        raise SystemExit(
            f"[render] 第 {page.get('page')} 页 layout='{layout_name}' 不在主题 manifest.layouts 列表里。\n"
            f"  支持: {list(manifest.get('layouts', {}).keys())}"
        )
    slot_defs = layout_meta.get("slots", {})
    card_padding = manifest["spacing"]["card_padding"]

    # 先渲染所有 cards 的 component fragment（按 slot 算可用空间）
    rendered_cards = []
    for card in page.get("cards", []):
        slot_name = card.get("slot")
        slot = slot_defs.get(slot_name) if slot_name else None
        slot_w = (slot["w"] - card_padding * 2) if slot else 0
        slot_h = (slot["h"] - card_padding * 2) if slot else 0
        rendered_cards.append({
            "slot": slot_name,
            "data": card.get("data", {}),
            "svg": render_card(env, manifest, card, slot_w=slot_w, slot_h=slot_h),
        })

    # 渲染 layout：优先找 layouts/<layout-name>.svg.j2 专属模板，缺省用 _base.svg.j2
    try:
        layout_tpl = env.get_template(f"layouts/{layout_name}.svg.j2")
    except Exception:
        layout_tpl = env.get_template("layouts/_base.svg.j2")
    layout_frag = layout_tpl.render(theme=manifest, cards=rendered_cards, page=page, meta=meta)

    # 渲染 slide-base
    base_tpl = env.get_template("slide-base.svg.j2")
    return base_tpl.render(theme=manifest, content=layout_frag, page=page, meta=meta, total_pages=total_pages)


def lint_check(layout: dict) -> None:
    """渲染前的中文版式检查。命中阻断退出。"""
    try:
        from lint_cn import lint_layout
    except ImportError:
        return  # lint_cn 还没装就跳过
    issues = lint_layout(layout)
    if issues:
        msg = "[lint] 中文版式检查未通过：\n" + "\n".join(f"  - {i}" for i in issues)
        msg += "\n\n规则：\n  - 中文与英文/数字之间不加空格\n  - 用中文标点（，。：！？""）不用英文标点\n请修改 layout.json 的 data.* 文案后重新渲染。"
        raise SystemExit(msg)


def render_all(ws: Path, theme: str | None = None) -> dict:
    """渲染工作区里所有页。"""
    layout_path = ws / "layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))

    lint_check(layout)

    theme_name = theme or layout.get("theme", "bento-tech")
    manifest, env = load_theme(theme_name)

    pages = layout.get("pages", [])
    if not pages:
        raise SystemExit("[render] layout.json 里 pages 为空")
    meta = layout.get("meta", {})

    slides_dir = ws / "slides"
    slides_dir.mkdir(exist_ok=True)
    # 清掉旧 svg（防止删页后残留文件）
    for old in slides_dir.glob("*.svg"):
        old.unlink()

    rendered = 0
    for page in pages:
        svg = render_one_page(env, manifest, page, total_pages=len(pages), meta=meta)
        page_no = page.get("page", rendered + 1)
        page_name = page.get("name") or f"page-{page_no}"
        out = slides_dir / f"{page_no:02d}-{slugify(page_name)}.svg"
        out.write_text(svg, encoding="utf-8")
        rendered += 1

    return {"rendered": rendered, "theme": theme_name, "slides_dir": str(slides_dir)}


def render_page(ws: Path, page_num: int, theme: str | None = None) -> dict:
    """渲染单页（page_num 是 1-based）。"""
    layout = json.loads((ws / "layout.json").read_text(encoding="utf-8"))
    lint_check(layout)
    theme_name = theme or layout.get("theme", "bento-tech")
    manifest, env = load_theme(theme_name)
    pages = layout.get("pages", [])
    target = next((p for p in pages if p.get("page") == page_num), None)
    if not target:
        raise SystemExit(f"[render] 第 {page_num} 页不存在（共 {len(pages)} 页）")
    meta = layout.get("meta", {})
    svg = render_one_page(env, manifest, target, total_pages=len(pages), meta=meta)
    page_name = target.get("name") or f"page-{page_num}"
    out = ws / "slides" / f"{page_num:02d}-{slugify(page_name)}.svg"
    out.write_text(svg, encoding="utf-8")
    return {"file": str(out), "page": page_num, "theme": theme_name}
