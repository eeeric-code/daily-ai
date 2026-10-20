"""Rebuild archives from real issues, preserving editorial metadata and missing records.

Each new issue should provide archive.json with a concise title and summary.
Without it, existing archive copy is retained; missing copy comes from that issue,
never from invented events. No dated issue body is modified.
"""
import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from bs4 import BeautifulSoup

DAY = r"\d{4}-\d{2}-\d{2}"
EDITIONS = [
    ("ai-products/gpt", "GPT 产业简报", "产业"),
    ("ai-academic/gpt", "GPT 学术简报", "学术"),
    ("ai-products/minimax", "MiniMax 产业简报", "产业"),
    ("ai-academic/minimax", "MiniMax 学术简报", "学术"),
]
LEGACY = [("ai-daily/gpt", "GPT 分栏前历史稿", "历史"),
          ("ai-daily/minimax", "MiniMax 分栏前历史稿", "历史")]
esc = lambda value: html.escape(str(value), quote=True)
clean = lambda value: re.sub(r"\s+", " ", value).strip()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(value)

def canonical(base, href):
    url = urlparse(urljoin("https://archive.local/" + base, href))
    if url.hostname not in ("archive.local", "daily-ai-2o3.pages.dev", "eeeric-code.github.io"):
        return None
    path = unquote(url.path).lstrip("/")
    if path.startswith("daily-ai/"):
        path = path[len("daily-ai/"):]
    path = re.sub(r"/index\.html$", "/", path).rstrip("/")
    return path if re.fullmatch(r"(?:ai-products|ai-academic|ai-daily)/(?:gpt/|minimax/)?"+DAY, path) else None

def extract_metadata(repo):
    """Read all old archives before replacing any, including malformed nested lists."""
    saved = {}
    files = [repo/"briefs.html", repo/"archive.html"]
    files += [repo/path/name for path,_,_ in EDITIONS+LEGACY for name in ("briefs.html", "archive.html")]
    for file in files:
        if not file.exists():
            continue
        soup = BeautifulSoup(file.read_text(encoding="utf-8-sig"), "html.parser")
        for node in soup.select(".archive-item"):
            path = node.get("data-path")
            if not path:
                candidates = [canonical(file.relative_to(repo).as_posix(), a["href"]) for a in node.select("a[href]")]
                path = next((p for p in candidates if p), None)
            if not path:
                continue
            title = node.select_one(".title, h2")
            summary = node.select_one(".summary, p")
            item = dict(title=clean(title.get_text(" ", strip=True)) if title else "",
                        summary=clean(summary.get_text(" ", strip=True)) if summary else "")
            # A node wrapping several corrupted cards is not a trustworthy metadata source.
            own_links = {canonical(file.relative_to(repo).as_posix(), a["href"]) for a in node.select("a[href]")}
            if len({p for p in own_links if p}) > 1:
                continue
            if item["title"] or item["summary"]:
                saved[path] = item
    return saved

def concise(text, limit):
    text = clean(text).lstrip("★☆ ")
    if len(text) <= limit:
        return text
    prefix = text.rstrip("…")[:limit-1]
    boundaries = [prefix.rfind(char) for char in "。；;！"]
    end = max(boundaries)
    if end >= limit//2:
        return prefix[:end+1]
    # Historical copy often separates independent events with '+'. Keep complete
    # events instead of cutting a company name, amount or claim halfway through.
    end = max(prefix.rfind(" + "), prefix.rfind("；"), prefix.rfind(" · "))
    if end >= min(limit//2, len(prefix)//2):
        return prefix[:end].rstrip("，、 ")
    end = max(prefix.rfind("，"), prefix.rfind(";"), prefix.rfind(", "))
    if end >= limit*2//3:
        return prefix[:end].rstrip() + "…"
    if re.search(r"[A-Za-z0-9]$",prefix):
        boundary = prefix.rfind(" ")
        if boundary >= limit*2//3:
            prefix = prefix[:boundary]
    return prefix.rstrip("，、 +;；") + "…"

def informative(title):
    return bool(title and not re.search(r"^(?:AI|GPT|MiniMax|gpt|minimax).{0,12}(?:每日简报|产业简报|学术简报)(?:[（(].*?[）)])?$", title))

def records(repo, path, metadata):
    folder = repo/path
    present = {p.name for p in folder.iterdir() if p.is_dir()
               and re.fullmatch(DAY, p.name) and (p/"index.html").is_file()} if folder.exists() else set()
    known = {key.rsplit("/",1)[-1] for key in metadata if key.rsplit("/",1)[0] == path}
    rows = []
    for day in sorted(present | known, reverse=True):
        key = path + "/" + day
        available = day in present
        item = dict(metadata.get(key, {}))
        count = None
        if available:
            soup = BeautifulSoup((folder/day/"index.html").read_text(encoding="utf-8-sig"), "html.parser")
            count = len(soup.select(".card"))
            override = folder/day/"archive.json"
            if override.exists():
                item = json.loads(override.read_text(encoding="utf-8-sig"))
                assert isinstance(item.get("title"), str) and isinstance(item.get("summary"), str), override
                assert 8 <= len(item["title"]) <= 100 and 40 <= len(item["summary"]) <= 200, override
            else:
                heads = [clean(n.get_text(" ",strip=True)).lstrip("★☆ ") for n in soup.select(".exec strong")]
                if not heads:
                    heads = [clean(n.get_text(" ",strip=True)).lstrip("★☆ ") for n in soup.select(".card-title")][:4]
                if not informative(item.get("title", "")):
                    item["title"] = " · ".join(heads[:3])
                if not item.get("summary") or item["summary"].startswith(("聚焦", "本栏", "MiniMax 当日原稿学术选编")):
                    bodies = []
                    for node in soup.select(".exec li")[:4]:
                        clone = BeautifulSoup(str(node), "html.parser")
                        for label in clone.select(".num, .label"):
                            label.decompose()
                        bodies.append(clean(clone.get_text(" ",strip=True)))
                    item["summary"] = "；".join(bodies) or "；".join(heads)
        title = concise(item.get("title", ""), 100)
        summary = concise(item.get("summary", ""), 200)
        assert title and summary, f"Missing archive copy for {key}; add archive.json"
        rows.append(dict(path=key, date=day, title=title, summary=summary,
                         available=available, count=count))
    return rows

def card(row, base, label):
    from posixpath import relpath
    if row["available"]:
        href = relpath(row["path"], base or ".") + "/"
        action = f'<a class="open-btn" href="./{esc(href)}" aria-label="查看 {esc(label)} {row["date"]}">查看 →</a>'
    else:
        action = '<span class="unavailable">原文暂缺</span>'
    count = f' · {row["count"]} 条' if row.get("count") else ""
    note = "" if row["available"] else '<p class="missing-note">保留原归档记录；原文文件当前缺失，暂不提供失效链接。</p>'
    return f'''    <li class="archive-item" data-path="{esc(row["path"])}" data-date="{row["date"]}" data-available="{str(row["available"]).lower()}">
      <div class="left">
        <div class="date">{row["date"]} <span class="edition-pill">{esc(label)}{count}</span></div>
        <div class="title">{esc(row["title"])}</div>
        <div class="summary">{esc(row["summary"])}</div>{note}
      </div>
      <div class="right">{action}</div>
    </li>'''

EXTRA_CSS = """
  .brand{gap:12px}.nav{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px;font-size:13px}
  .edition-pill{display:inline-block;font-size:11px;font-weight:500;letter-spacing:0;color:var(--ink-soft);margin-left:7px}
  .section-heading{font-size:21px;margin:32px 0 8px}.section-note{font-size:14px;color:var(--ink-soft)}
  .unavailable{font-size:13px;color:var(--ink-soft);white-space:nowrap}.missing-note{font-size:12px;color:var(--gold);margin:8px 0 0}
  a:focus-visible{outline:3px solid var(--gold);outline-offset:3px}
  @media(max-width:520px){.brand{flex-direction:column;align-items:flex-start}.edition-pill{display:block;margin-left:0}.title,.summary{overflow-wrap:anywhere}}
"""

def page(style, title, description, groups, base="", root_page=False):
    from posixpath import relpath
    home = "../" * len(base.split("/")) if base else "./"
    nav = [f'<a href="{home}">← 返回首页</a>']
    for path,label,_ in EDITIONS:
        href = relpath(path+"/archive.html", base or ".")
        nav.append(f'<a href="./{href}">{label}</a>')
    if base:
        nav.append(f'<a href="{home}briefs.html">全部往期</a>')
    body = []
    for heading, note, rows, label in groups:
        body.append(f'<section><h2 class="section-heading">{esc(heading)}</h2><p class="section-note">{esc(note)}</p><ul class="archive-list">')
        body.extend(card(row, base, row.get("label",label)) for row in rows)
        body.append("</ul></section>")
    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} · 往期归档</title>
{style}
<style>{EXTRA_CSS}</style></head><body><div class="container">
<div class="brand"><div class="logo">AI Daily Brief <span>· 往期归档</span></div><div class="meta">全球视野 · 按日期倒序 · 原文可追溯</div></div>
<header><nav class="nav" aria-label="归档导航">{"".join(nav)}</nav><h1>📚 {esc(title)} · <span class="accent">往期归档</span></h1><p class="subtitle">{esc(description)}</p></header>
{"".join(body)}
<footer>© 2026 AI Daily Brief · 历史标题与摘要用于索引，不代表重新核验原稿全部事实</footer>
</div></body></html>
'''

def build(repo, metadata_source=None):
    original = (repo/"example/archive.html").read_text(encoding="utf-8-sig")
    style = re.search(r"<style[^>]*>.*?</style>", original, re.S).group()
    metadata = extract_metadata(repo)
    if metadata_source:
        # Optional one-time migration source, kept outside the public repository.
        # Ordinary daily runs read current metadata and never require this backup.
        metadata.update(extract_metadata(metadata_source))
    all_rows = {path: records(repo,path,metadata) for path,_,_ in EDITIONS+LEGACY}
    output, audit = {}, {}
    for path,label,kind in EDITIONS+LEGACY:
        rows = all_rows[path]
        live = sum(row["available"] for row in rows)
        missing = len(rows)-live
        note = f"{live} 期原文可阅读" + (f"；另有 {missing} 条历史记录的原文暂缺，已保留记录。" if missing else "。")
        groups = [("独立学术版" if kind=="学术" else "历史简报" if kind=="历史" else "产业版往期", note, rows, label)]
        description = "按日期倒序展示每期重点标题、内容摘要与原文入口。"
        if kind == "学术":
            legacy_path = "ai-daily/" + path.rsplit("/",1)[-1]
            historical = all_rows[legacy_path]
            n = sum(row["available"] for row in historical)
            m = len(historical)-n
            groups.append(("分栏前历史稿（含产业内容）",
                f"以下保留原稿，不冒充独立学术版，不计入首页学术版期数。{n} 期可阅读"
                + (f"，{m} 条原文暂缺。" if m else "。"), historical, label.split()[0]+" 分栏前历史稿"))
            description += "独立学术版与分栏前历史稿分区展示。"
        if kind == "历史":
            description += "本区含学术与产业混合内容，保留原稿，不作为新的独立学术版。"
        value = page(style,label,description,groups,base=path)
        for name in ("archive.html","briefs.html"):
            output[path+"/"+name] = value
        audit[path] = dict(available=live, missing=missing,
            dates=[r["date"] for r in rows if r["available"]],
            unavailable=[r["date"] for r in rows if not r["available"]])
    current = [dict(row,label=label) for path,label,_ in EDITIONS for row in all_rows[path]]
    historical = [dict(row,label=label) for path,label,_ in LEGACY for row in all_rows[path]]
    # Preserve previously indexed, unattributed early dates without guessing a model.
    generic_paths = {key.rsplit("/",1)[0] for key in metadata if re.fullmatch(r"ai-daily/"+DAY,key)}
    for path in generic_paths:
        for row in records(repo,path,metadata):
            if row["path"] in metadata:
                historical.append(dict(row,label="早期通用稿"))
    current.sort(key=lambda row: (row["date"],row["label"]),reverse=True)
    historical.sort(key=lambda row: (row["date"],row["label"]),reverse=True)
    value = page(style,"全部栏目","四个独立栏目与分栏前历史稿分区展示；日期倒序排列。",
        [("四个独立栏目","GPT 与 MiniMax 的产业、学术版分别收录。",current,""),
         ("分栏前历史稿","含产业与学术混合内容，保留历史，不重新标为独立学术版。",historical,"")], root_page=True)
    output["archive.html"] = output["briefs.html"] = value
    return output,audit

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo",type=Path,default=Path("."))
    parser.add_argument("--workspace",type=Path)
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--audit",type=Path)
    parser.add_argument("--metadata-source",type=Path,
                        help="Optional original archive backup for a one-time repair")
    args=parser.parse_args()
    repo=args.repo.resolve()
    output,audit=build(repo,args.metadata_source)
    different=[]
    for relative,value in output.items():
        path=repo/relative
        if not path.exists() or path.read_text(encoding="utf-8-sig")!=value:
            different.append(relative)
            if not args.check:
                write(path,value)
    if args.workspace and not args.check:
        for name in ("archive.html","briefs.html"):
            write(args.workspace/name,output[name])
    if args.audit:
        write(args.audit,json.dumps(audit,ensure_ascii=False,indent=2))
    print(json.dumps(dict(mode="check" if args.check else "render",changed=different,
        counts={key:{k:v for k,v in value.items() if k in ("available","missing")} for key,value in audit.items()}),ensure_ascii=False))
    if args.check and different:
        raise SystemExit(1)

if __name__=="__main__":
    main()
