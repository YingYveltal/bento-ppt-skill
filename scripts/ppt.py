"""ppt-agent CLI: 从主题到可演讲 PPT 的端到端流水线。

子命令：
  new <topic>                       创建工作区 ~/ppt-decks/<date>-<slug>/，写 brief.md 模板
  scaffold <ws>                     根据 layout.json 渲染所有页 → slides/*.svg
  render <ws> [--page N] [--theme]  渲染单页或全部
  shoot <ws>                        playwright 截图 + 生成 deck.html 翻页预览
  export <ws> --format pptx|pdf|html  导出 PPTX (svgBlip) / PDF / 单文件 HTML

工作区合法性：根目录有 .layout 标识文件。所有命令都会检查，防误操作。
工作区根目录默认 ~/ppt-decks/，env PPT_DECKS_DIR 覆盖。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LAYOUT_MARKER = ".layout"
DEFAULT_ROOT = Path.home() / "ppt-decks"

# ---------- 工作区管理 ----------

def get_decks_root() -> Path:
    env = os.environ.get("PPT_DECKS_DIR")
    return Path(env).expanduser().resolve() if env else DEFAULT_ROOT


def ensure_root() -> Path:
    root = get_decks_root()
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        print(f"[init] 已创建 deck 工作区根目录: {root}")
        print(f"       今后所有 deck 工作区都会在这里。如需更改路径，设环境变量 PPT_DECKS_DIR。")
    return root


def slugify(name: str) -> str:
    s = re.sub(r"[\s/\\:*?\"<>|]+", "-", name.strip())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "untitled"


def is_workspace(path: Path) -> bool:
    return (path / LAYOUT_MARKER).is_file()


def find_workspace(path: Path) -> Path | None:
    p = path.resolve()
    if p.is_file():
        p = p.parent
    while True:
        if is_workspace(p):
            return p
        if p.parent == p:
            return None
        p = p.parent


def require_workspace(arg: str) -> Path:
    """把 ws 参数解析成合法工作区路径，否则报错退出。"""
    p = Path(arg).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"[ws] 路径不存在: {p}")
    ws = find_workspace(p) if not is_workspace(p) else p
    if ws is None:
        raise SystemExit(
            f"[ws] 不是合法工作区: {p}\n"
            f"  缺少 {LAYOUT_MARKER} 标识文件。\n"
            f"  请先用 new 命令创建工作区："
            f"  python3 {__file__} new \"<主题>\""
        )
    return ws


# ---------- new ----------

_BRIEF_TEMPLATE = """# Brief: {topic}

> 这份 brief 是整个 deck 的基础。**AI 不要跳过这一步直接写大纲**。
> 必须先和用户对完所有字段，再进入下一阶段。

## 核心信息

- **主题**: {topic}
- **目标受众**: <投资人 / 客户 / 内部团队 / 行业大会观众 / ...>
- **场景与时长**: <15 分钟产品发布 / 5 分钟电梯演讲 / 30 分钟内训 / ...>
- **核心目标**: <让对方掏钱 / 让对方点头 / 让对方转发 / 让对方学到东西 / ...>
- **调性偏好**: <严肃专业 / 活泼有趣 / 极简克制 / 数据密集 / ...>
- **页数预算**: <8 页内 / 15-20 页 / 30+ 页>

## 必须出现的内容

（产品截图 / 关键数据 / 团队照 / 客户 logo 墙等。AI 不能擅自决定省略）

-

## 已有素材

（用户已经提供的文档、链接、图片路径）

-

## 备注

（任何额外约束、避免提及的内容、禁忌色、合规要求等）

-
"""


def cmd_new(topic: str) -> dict:
    root = ensure_root()
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(topic)
    workspace = root / f"{today}-{slug}"
    if workspace.exists():
        i = 2
        while (root / f"{today}-{slug}-{i}").exists():
            i += 1
        workspace = root / f"{today}-{slug}-{i}"
    workspace.mkdir(parents=True)
    (workspace / "research").mkdir()
    (workspace / "slides").mkdir()
    (workspace / "shots").mkdir()
    (workspace / "assets").mkdir()
    (workspace / LAYOUT_MARKER).write_text(
        f"ppt-agent workspace\ncreated_at: {datetime.now(timezone.utc).isoformat()}\ntopic: {topic}\n",
        encoding="utf-8",
    )
    (workspace / "brief.md").write_text(_BRIEF_TEMPLATE.format(topic=topic), encoding="utf-8")
    return {"workspace": str(workspace), "root": str(root)}


# ---------- scaffold / render（委托给 render.py）----------

def _import_render():
    """延迟导入，避免没装 jinja2 时跑 new 也失败。"""
    sys.path.insert(0, str(Path(__file__).parent))
    import render  # type: ignore
    return render


def cmd_scaffold(ws: Path, theme: str | None = None) -> dict:
    """根据 layout.json 渲染所有页 → slides/*.svg。"""
    render = _import_render()
    layout_path = ws / "layout.json"
    if not layout_path.exists():
        raise SystemExit(
            f"[scaffold] 找不到 {layout_path}\n"
            f"  scaffold 之前需要先：\n"
            f"  1. 填好 brief.md（受众/场景/调性等）\n"
            f"  2. 写好 outline.json（金字塔结构大纲）\n"
            f"  3. 写好 layout.json（每页布局选型 + 槽位 component + 内容草稿）\n\n"
            f"  layout.json schema 详见 ~/.claude/skills/ppt-agent/reference/bento-layouts-guide.md"
        )
    return render.render_all(ws, theme=theme)


def cmd_render(ws: Path, page: int | None = None, theme: str | None = None) -> dict:
    render = _import_render()
    if page is None:
        return render.render_all(ws, theme=theme)
    return render.render_page(ws, page, theme=theme)


# ---------- shoot（委托给 shoot.py）----------

def cmd_shoot(ws: Path) -> dict:
    sys.path.insert(0, str(Path(__file__).parent))
    import shoot  # type: ignore
    return shoot.shoot_all(ws)


# ---------- fetch（委托给 fetch.py）----------

def cmd_fetch(ws: Path) -> dict:
    sys.path.insert(0, str(Path(__file__).parent))
    import fetch  # type: ignore
    return fetch.fetch_all(ws)


# ---------- export（委托给 export.py）----------

def cmd_export(ws: Path, fmt: str) -> dict:
    sys.path.insert(0, str(Path(__file__).parent))
    import export  # type: ignore
    if fmt == "pptx":
        return export.to_pptx(ws)
    if fmt == "pptx-svg":
        return export.to_pptx_svg(ws)
    if fmt == "pdf":
        return export.to_pdf(ws)
    if fmt == "html":
        return export.to_html(ws)
    raise SystemExit(f"[export] 未知格式: {fmt}（支持 pptx / pptx-svg / pdf / html）")


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="ppt-agent: 主题 → 可演讲 PPT 的端到端流水线")
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="创建 deck 工作区 + brief.md 模板")
    n.add_argument("topic", help="主题，会被转成 slug。例：'Dify 企业介绍'")

    s = sub.add_parser("scaffold", help="按 layout.json 渲染所有页")
    s.add_argument("ws", help="工作区路径")
    s.add_argument("--theme", default=None, help="覆盖 layout.json 里的 theme 字段")

    r = sub.add_parser("render", help="渲染单页或全部")
    r.add_argument("ws", help="工作区路径")
    r.add_argument("--page", type=int, default=None, help="只渲染第 N 页（1-based）")
    r.add_argument("--theme", default=None, help="覆盖 layout.json 里的 theme 字段")

    sh = sub.add_parser("shoot", help="playwright 截图 + 生成 deck.html 翻页预览")
    sh.add_argument("ws", help="工作区路径")

    fe = sub.add_parser("fetch", help="按 layout.json 里 card-image 的 src/source 拉图片到 <ws>/assets/")
    fe.add_argument("ws", help="工作区路径")

    e = sub.add_parser("export", help="导出最终产物")
    e.add_argument("ws", help="工作区路径")
    e.add_argument("--format", "-f", default="pptx", choices=["pptx", "pptx-svg", "pdf", "html"])

    args = ap.parse_args()

    if args.cmd == "new":
        result = cmd_new(args.topic)
        ws = result["workspace"]
        print(f"[ok] 工作区已创建: {ws}")
        print(f"\n下一步（按 SKILL.md 7 阶段流程）：")
        print(f"  1. 阶段 1（needs）：反问用户 3-5 个问题，把答案填进 {ws}/brief.md")
        print(f"  2. 阶段 2（research）：用 WebSearch 按主题搜资料，落到 {ws}/research/<chapter>.md")
        print(f"  3. 阶段 3（outline）：用 reference/pyramid-outline-prompt.md 出 {ws}/outline.json")
        print(f"  4. 阶段 4（planning）：把大纲转成 {ws}/layout.json（每页布局 + 槽位）")
        print(f"  5. 阶段 5（design）：python3 {__file__} scaffold {ws}")
        print(f"  6. 阶段 6（review）：python3 {__file__} shoot {ws}")
        print(f"  7. 阶段 7（export）：python3 {__file__} export {ws} --format pptx")

    elif args.cmd == "scaffold":
        ws = require_workspace(args.ws)
        result = cmd_scaffold(ws, theme=args.theme)
        print(f"[ok] 渲染 {result['rendered']} 页 → {ws}/slides/")
        print(f"     主题: {result['theme']}")
        print(f"\n下一步: python3 {__file__} shoot {ws}")

    elif args.cmd == "render":
        ws = require_workspace(args.ws)
        result = cmd_render(ws, page=args.page, theme=args.theme)
        if args.page is not None:
            print(f"[ok] 第 {args.page} 页已重渲: {result['file']}")
        else:
            print(f"[ok] 渲染 {result['rendered']} 页")

    elif args.cmd == "shoot":
        ws = require_workspace(args.ws)
        result = cmd_shoot(ws)
        print(f"[ok] 截图 {result['shots']} 张 → {ws}/shots/")
        print(f"     翻页预览: {result['deck_html']}")

    elif args.cmd == "fetch":
        ws = require_workspace(args.ws)
        result = cmd_fetch(ws)
        print(
            f"[ok] 下载 {result['fetched']}，"
            f"已就绪本地图 {result['skipped_local']}，"
            f"没找到 provider {result['no_provider']}，"
            f"失败 {result['failed']}"
        )
        print(f"     assets: {result['assets_dir']}")

    elif args.cmd == "export":
        ws = require_workspace(args.ws)
        result = cmd_export(ws, args.format)
        print(f"[ok] 已导出: {result['output']}")


if __name__ == "__main__":
    main()
