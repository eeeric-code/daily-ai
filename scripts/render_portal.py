"""Render the four-edition homepage from actual published date directories."""
import argparse
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape

EDITIONS = [
    ("gpt-products", "GPT", "产业简报", "ai-products/gpt",
     "监管、资本、算力、模型平台、产品采用与竞争格局。", "#7ee787"),
    ("gpt-academic", "GPT", "学术简报", "ai-academic/gpt",
     "论文、研究方法、可复现实验、评测与开放科研。", "#79c0ff"),
    ("minimax-products", "MiniMax", "产业简报", "ai-products/minimax",
     "从商业证据出发，观察全球 AI 产品与产业链变化。", "#d2a8ff"),
    ("minimax-academic", "MiniMax", "学术简报", "ai-academic/minimax",
     "从研究贡献出发，追踪科学发现、智能体与技术方法。", "#e3b341"),
]

def write_lf(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)

def render(repo, workspace=None):
    template = (repo / "portal-template.html").read_text(encoding="utf-8-sig")
    cards = []
    dates = []
    for slug, model, edition, path, desc, accent in EDITIONS:
        directory = repo / path
        published = sorted(p.name for p in directory.iterdir()
                           if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
                           and (p / "index.html").is_file()) if directory.exists() else []
        latest = published[-1] if published else None
        if latest:
            dates.append(latest)
            href = f"./{path}/{latest}/"
            status = f"最新：{latest}"
            action = f'<a class="primary" href="{href}">阅读最新 <span aria-hidden="true">↗</span></a>'
        else:
            status = "尚无已发布内容"
            action = '<span class="empty">等待首期发布</span>'
        archive = directory / "archive.html"
        archive_link = f'<a href="./{path}/archive.html">往期归档</a>' if archive.is_file() else ""
        cards.append(f'''<section class="card model-card" data-edition="{slug}" style="--model-accent:{accent}" aria-labelledby="{slug}-title">
  <div class="model-head"><span class="model-dot"></span><span class="model-name">{model}</span><span class="edition-label">{edition}</span></div>
  <h2 id="{slug}-title">{model} {edition}</h2>
  <p class="card-desc">{desc}</p>
  <div class="model-meta"><span>{status}</span><span>已收录 {len(published)} 期</span></div>
  <div class="model-actions">{action}{archive_link}</div>
</section>''')
    assert template.count("<!-- EDITION_CARDS -->") == 1
    page = template.replace("<!-- EDITION_CARDS -->", "\n".join(cards))
    page = page.replace("<!-- UPDATED -->", escape(max(dates) if dates else "尚未发布"))
    assert len(re.findall(r'data-edition="', page)) == 4
    assert "Claude" not in page and "综合简报" not in page
    write_lf(repo / "index.html", page)
    if workspace and workspace.resolve() != repo.resolve():
        write_lf(workspace / "index.html", page)
        write_lf(workspace / "portal-template.html", template)
    return {"editions": 4, "latest": max(dates) if dates else None}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    print(render(args.repo.resolve(), args.workspace.resolve() if args.workspace else None))
