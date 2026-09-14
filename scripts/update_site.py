from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
INDEX_PATH = ROOT / "index.html"
NEWS_JSON = DATA_DIR / "latest-news.json"


@dataclass(frozen=True)
class Source:
    name: str
    channel: str
    url: str
    keywords: tuple[str, ...]


SOURCES = (
    Source("OpenAI News", "OpenAI 官网", "https://openai.com/news/", ("openai", "model", "agent", "api", "chatgpt", "codex")),
    Source("Google AI Blog", "Google Blog", "https://blog.google/technology/ai/", ("google", "gemini", "deepmind", "ai", "agent")),
    Source("Microsoft Source AI", "Microsoft Source", "https://news.microsoft.com/source/tag/ai/", ("microsoft", "copilot", "ai", "agent", "azure")),
    Source("Anthropic News", "Anthropic News", "https://www.anthropic.com/news", ("anthropic", "claude", "safety", "model", "agent")),
    Source("百度 AI 开放平台", "百度 AI 开放平台", "https://ai.baidu.com/support/news", ("百度", "文心", "ai", "大模型", "智能")),
    Source("百度智能云新闻", "百度智能云", "https://cloud.baidu.com/news/news", ("百度", "智能云", "文心", "ai", "大模型")),
    Source("腾讯新闻", "腾讯官网", "https://www.tencent.com/zh-cn/newsroom/all-news/", ("腾讯", "混元", "ai", "大模型", "开源")),
    Source("腾讯云动态", "腾讯云", "https://cloud.tencent.com/developer/news", ("腾讯", "混元", "ai", "大模型", "云")),
)


FALLBACK_BY_SOURCE = {
    "OpenAI News": {
        "date": "2026-09-10",
        "channel": "OpenAI 官网",
        "title": "OpenAI 发布 Agents API 公测",
        "background": "OpenAI 官网在自动抓取中可能返回 403；此条为人工核验过的保底条目，页面会继续保留原始来源链接。",
        "content": "Agents API 将 Codex 背后的 agent harness 和基础设施开放给开发者，支持托管沙箱、MCP、工具搜索、并行子代理和长会话压缩。",
        "url": "https://openai.com/index/introducing-the-agents-api/",
        "source": "OpenAI News",
        "status": "manual-verified-fallback",
    }
}


PAPERS = (
    {
        "meta": "AI Safety / Control",
        "title": "AI Control: Improving Safety Despite Intentional Subversion",
        "summary": "Redwood Research 提出的 AI control 方向：即使强模型可能故意破坏，也通过弱可信模型监督、监控与协议设计限制其造成损害的能力。",
        "source": "Redwood Research",
        "url": "https://www.redwoodresearch.org/research/ai-control",
    },
    {
        "meta": "Frontier Alignment / 2026",
        "title": "Diffuse AI Control on Fuzzy Tasks",
        "summary": "Anthropic Alignment Science Blog 文章，研究在难以评分的模糊任务中如何评估和改进弱评分器对强模型蓄意规避的鲁棒性。",
        "source": "Anthropic Alignment",
        "url": "https://alignment.anthropic.com/2026/diffuse-ai-control/",
    },
    {
        "meta": "AI R&D Evaluation / 2026",
        "title": "ResearchArena: Evaluating Sabotage and Monitoring in Automated AI R&D",
        "summary": "围绕自动化 AI 研发中的研究破坏与监控评估构建测试场景，适合放入智能体安全与科研自动化风险文献池。",
        "source": "Kurate / arXiv",
        "url": "https://kurate.org/paper/43d6199c-5b7d-4ef8-99ac-d00dcaafb672",
    },
    {
        "meta": "Control + LLM + RL / 2026",
        "title": "Hierarchical Control Framework Integrating LLMs with RL for Decarbonized HVAC Operation",
        "summary": "楼宇控制研究：使用 LLM 生成动作掩码，再由 RL 在约束空间内优化舒适度与能耗。",
        "source": "arXiv",
        "url": "https://arxiv.org/abs/2603.26050",
    },
    {
        "meta": "Smart Building / China Data / 2026",
        "title": "Video-based Indoor Occupancy Measurement with Occupant-centric Control",
        "summary": "基于中国研究实验室真实监控数据，将视觉识别管线用于 occupancy measurement，并接入 HVAC 监督 MPC。",
        "source": "arXiv",
        "url": "https://arxiv.org/abs/2603.26081",
    },
    {
        "meta": "Robotics / LLM + RL / 2026",
        "title": "Hybrid Framework for Robotic Manipulation: Integrating RL and LLMs",
        "summary": "将低层强化学习控制与高层 LLM 任务规划结合，用于机械臂操作任务，是具身智能与控制结合的典型入口。",
        "source": "arXiv",
        "url": "https://arxiv.org/abs/2603.30022",
    },
)


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AI-News-Radar/1.0 (+https://github.com/sweetboyes/ai-news-site)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def extract_title(page: str) -> str:
    for pattern in (
        r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"']([^\"']+)[\"']",
        r"<title[^>]*>(.*?)</title>",
        r"<h1[^>]*>(.*?)</h1>",
    ):
        match = re.search(pattern, page, re.I | re.S)
        if match:
            return clean_text(match.group(1))
    return "Latest AI update"


def extract_description(page: str) -> str:
    for pattern in (
        r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']+)[\"']",
        r"<meta[^>]+property=[\"']og:description[\"'][^>]+content=[\"']([^\"']+)[\"']",
    ):
        match = re.search(pattern, page, re.I | re.S)
        if match:
            return clean_text(match.group(1))
    return "官方页面已更新，需人工复核具体变更内容。"


def extract_date(page: str) -> str:
    patterns = (
        r"<time[^>]+datetime=[\"']([^\"']+)[\"']",
        r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})",
        r"(20\d{2}年\d{1,2}月\d{1,2}日)",
        r"([A-Z][a-z]+ \d{1,2}, 20\d{2})",
    )
    for pattern in patterns:
        match = re.search(pattern, page, re.I | re.S)
        if match:
            return normalize_date(match.group(1))
    return dt.date.today().isoformat()


def normalize_date(value: str) -> str:
    value = value.strip()
    iso_match = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", value)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        return dt.date(year, month, day).isoformat()
    cn_match = re.search(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", value)
    if cn_match:
        year, month, day = map(int, cn_match.groups())
        return dt.date(year, month, day).isoformat()
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return dt.date.today().isoformat()


def candidate_links(source: Source, page: str) -> Iterable[tuple[str, str]]:
    seen: set[str] = set()
    for href, text in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", page, re.I | re.S):
        text = clean_text(text)
        if len(text) < 8 or len(text) > 130:
            continue
        haystack = f"{text} {href}".lower()
        if not any(keyword.lower() in haystack for keyword in source.keywords):
            continue
        url = urljoin(source.url, html.unescape(href))
        if url in seen:
            continue
        seen.add(url)
        yield text, url


def build_news_item(source: Source) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    try:
        source_page = fetch(source.url)
        first_candidate = next(iter(candidate_links(source, source_page)), None)
        if first_candidate:
            title, url = first_candidate
            detail_page = fetch(url)
        else:
            url = source.url
            detail_page = source_page
            title = extract_title(detail_page)
        description = extract_description(detail_page)
        published = extract_date(detail_page)
        return {
            "date": published,
            "channel": source.channel,
            "title": title,
            "background": "来自官方或可信公开页面的自动抓取条目；已记录原始来源，仍建议对关键数字和政策表述做人工复核。",
            "content": description[:240],
            "url": url,
            "source": source.name,
            "status": "official-source",
        }, None
    except Exception as exc:
        print(f"[warn] {source.name}: {exc}", file=sys.stderr)
        fallback = FALLBACK_BY_SOURCE.get(source.name)
        failure = {
            "source": source.name,
            "channel": source.channel,
            "url": source.url,
            "error": str(exc),
            "used_fallback": "yes" if fallback else "no",
        }
        return (dict(fallback) if fallback else None), failure


def load_previous_news() -> list[dict[str, str]]:
    if not NEWS_JSON.exists():
        return []
    try:
        data = json.loads(NEWS_JSON.read_text(encoding="utf-8"))
        return data.get("news", [])
    except Exception:
        return []


def collect_news() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    items: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for source in SOURCES:
        item, failure = build_news_item(source)
        if failure:
            failures.append(failure)
        if item and item["url"] not in seen_urls:
            items.append(item)
            seen_urls.add(item["url"])
    if len(items) < 5:
        for item in load_previous_news():
            if item.get("url") not in seen_urls:
                item["status"] = "previous-run"
                items.append(item)
                seen_urls.add(item["url"])
            if len(items) >= 8:
                break
    items.sort(key=lambda item: item.get("date", ""), reverse=True)
    return items[:8], failures


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def render(news: list[dict[str, str]], failures: list[dict[str, str]]) -> str:
    generated = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    today_cn = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d")
    if failures:
        failed_names = "、".join(f"{item['channel']}（{item['source']}）" for item in failures)
        fallback_count = sum(1 for item in failures if item.get("used_fallback") == "yes")
        status_title = "部分来源抓取失败"
        status_detail = f"本次未能自动抓取：{failed_names}。"
        if fallback_count:
            status_detail += f" 其中 {fallback_count} 个来源已使用人工核验保底条目；其余来源未写入新资讯。"
    else:
        status_title = "来源抓取正常"
        status_detail = "本次自动刷新未发现官方来源抓取失败。"
    failure_list = "".join(
        f'<li><a href="{esc(item["url"])}" target="_blank" rel="noreferrer">{esc(item["channel"])}</a>：{esc(item["error"])}</li>'
        for item in failures
    )
    status_class = "status-alert has-failures" if failures else "status-alert ok"
    failure_details = f"<ul>{failure_list}</ul>" if failures else ""
    status_banner = f"""
    <div class="{status_class}">
      <div>
        <strong>{esc(status_title)}</strong>
        <p>{esc(status_detail)}</p>
        {failure_details}
      </div>
    </div>"""
    news_cards = "\n".join(
        f"""
          <article class="news-item">
            <div class="news-top"><span>{esc(item['date'])}</span><span class="source-tag">{esc(item['channel'])}</span></div>
            <h3>{esc(item['title'])}</h3>
            <div class="news-copy">
              <div><span class="label">背景</span> {esc(item['background'])}</div>
              <div><span class="label">内容</span> {esc(item['content'])}</div>
            </div>
            <a class="card-link" href="{esc(item['url'])}" target="_blank" rel="noreferrer">查看来源</a>
          </article>"""
        for item in news
    )
    paper_cards = "\n".join(
        f"""
          <article class="paper">
            <div class="paper-meta">{esc(item['meta'])}</div>
            <h3>{esc(item['title'])}</h3>
            <p>{esc(item['summary'])}</p>
            <a class="card-link" href="{esc(item['url'])}" target="_blank" rel="noreferrer">{esc(item['source'])}</a>
          </article>"""
        for item in PAPERS
    )
    source_links = "\n".join(
        f'          <p><a href="{esc(source.url)}" target="_blank" rel="noreferrer">{esc(source.name)}</a></p>'
        for source in SOURCES
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Frontier Radar</title>
  <style>
    :root {{ color-scheme: dark; --bg:#050608; --paper:#f6f7f9; --ink:#f5f7fb; --muted:#9da7b6; --line:rgba(255,255,255,.13); --blue:#4da3ff; --blue-2:#87c5ff; --panel:#0c0f14; --panel-2:#11151d; --ok:#8fd6b4; --warn:#f2cf7e; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; background:var(--bg); color:var(--ink); letter-spacing:0; }}
    a {{ color:inherit; }}
    .shell {{ width:min(1180px, calc(100% - 36px)); margin:0 auto; }}
    header {{ min-height:92vh; display:grid; align-items:center; border-bottom:1px solid var(--line); background:linear-gradient(115deg, rgba(5,6,8,.96) 0%, rgba(5,6,8,.84) 56%, rgba(15,31,48,.62) 100%), url("https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1800&q=80") center / cover; }}
    nav {{ position:fixed; inset:0 0 auto; z-index:20; border-bottom:1px solid rgba(255,255,255,.1); background:rgba(5,6,8,.78); backdrop-filter:blur(18px); }}
    .nav-inner {{ width:min(1180px, calc(100% - 36px)); margin:0 auto; height:64px; display:flex; align-items:center; justify-content:space-between; gap:20px; }}
    .brand {{ display:flex; align-items:center; gap:12px; font-weight:760; }}
    .mark {{ width:26px; height:26px; border:1px solid var(--blue); display:grid; place-items:center; color:var(--blue-2); font-size:13px; }}
    .nav-links {{ display:flex; gap:18px; color:var(--muted); font-size:14px; }}
    .nav-links a {{ text-decoration:none; }}
    .hero {{ padding-top:84px; max-width:900px; }}
    .eyebrow {{ display:inline-flex; align-items:center; gap:9px; color:var(--blue-2); text-transform:uppercase; font-size:12px; font-weight:760; letter-spacing:.08em; margin-bottom:22px; }}
    .pulse {{ width:8px; height:8px; background:var(--blue); box-shadow:0 0 24px var(--blue); }}
    h1 {{ margin:0; max-width:820px; font-size:clamp(48px, 8vw, 116px); line-height:.91; font-weight:820; }}
    .hero p {{ max-width:680px; margin:28px 0 0; color:#d7dde6; font-size:clamp(18px, 2.2vw, 24px); line-height:1.55; }}
    .hero-meta {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:36px; }}
    .chip {{ border:1px solid var(--line); color:#dbe6f5; padding:8px 11px; font-size:13px; background:rgba(255,255,255,.04); }}
    .family-note {{ width:fit-content; margin-top:24px; padding:14px 18px; border-left:4px solid var(--blue); background:rgba(255,255,255,.07); color:var(--paper); font-size:clamp(19px, 2.6vw, 30px); font-weight:850; line-height:1.25; box-shadow:0 18px 60px rgba(0,0,0,.25); }}
    .status-alert {{ margin-top:28px; padding:18px 20px; border:1px solid rgba(255,255,255,.14); background:rgba(12,15,20,.82); max-width:860px; }}
    .status-alert strong {{ display:block; font-size:20px; margin-bottom:6px; color:var(--paper); }}
    .status-alert p {{ margin:0; max-width:none; color:#d9e1eb; font-size:15px; line-height:1.6; }}
    .status-alert ul {{ margin:10px 0 0; padding-left:19px; color:#d9e1eb; font-size:14px; line-height:1.6; }}
    .status-alert a {{ color:var(--blue-2); }}
    .status-alert.has-failures {{ border-left:4px solid var(--warn); }}
    .status-alert.ok {{ border-left:4px solid var(--ok); }}
    main {{ background:var(--bg); }}
    section {{ padding:76px 0; border-bottom:1px solid var(--line); }}
    .section-head {{ display:grid; grid-template-columns:minmax(0, 1fr) auto; gap:20px; align-items:end; margin-bottom:30px; }}
    h2 {{ margin:0; font-size:clamp(30px, 4vw, 54px); line-height:1; }}
    .section-note {{ color:var(--muted); max-width:600px; line-height:1.7; }}
    .date-pill {{ border-left:2px solid var(--blue); padding-left:14px; color:#dce7f6; font-size:14px; white-space:nowrap; }}
    .news-grid {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:14px; }}
    .news-item {{ border:1px solid var(--line); background:linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02)); padding:22px; min-height:320px; display:grid; grid-template-rows:auto auto 1fr auto; gap:16px; }}
    .news-top {{ display:flex; justify-content:space-between; gap:14px; color:var(--muted); font-size:13px; }}
    .source-tag {{ color:var(--blue-2); font-weight:700; }}
    .news-item h3 {{ margin:0; font-size:24px; line-height:1.18; }}
    .news-copy {{ display:grid; gap:10px; color:#c8d0dc; line-height:1.65; font-size:15px; }}
    .label {{ color:var(--paper); font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }}
    .card-link {{ width:fit-content; color:var(--paper); text-decoration:none; border-bottom:1px solid var(--blue); padding-bottom:4px; font-size:14px; }}
    .verify-band {{ display:grid; grid-template-columns:1.05fr .95fr; gap:18px; align-items:stretch; }}
    .panel {{ border:1px solid var(--line); background:var(--panel); padding:24px; }}
    .panel h3 {{ margin:0 0 14px; font-size:22px; }}
    .checks {{ display:grid; gap:12px; color:#d1d8e2; line-height:1.6; }}
    .check {{ display:grid; grid-template-columns:13px 1fr; gap:10px; align-items:start; }}
    .dot {{ width:8px; height:8px; margin-top:8px; background:var(--ok); }}
    .watchlist {{ display:flex; flex-wrap:wrap; gap:9px; }}
    .watchlist span {{ padding:8px 10px; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.035); color:#d8dee8; font-size:13px; }}
    .watchlist .pending {{ color:var(--warn); border-color:rgba(242,207,126,.32); }}
    .papers {{ display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:14px; }}
    .paper {{ border:1px solid var(--line); background:var(--panel-2); padding:20px; display:grid; gap:12px; min-height:270px; }}
    .paper h3 {{ margin:0; font-size:19px; line-height:1.25; }}
    .paper p {{ margin:0; color:#c4ccd8; line-height:1.6; font-size:14px; }}
    .paper-meta {{ color:var(--blue-2); font-size:13px; font-weight:700; }}
    .source-list {{ columns:2; column-gap:32px; color:#c8d0dc; line-height:1.9; font-size:14px; }}
    .source-list a {{ color:#dfe7f3; text-decoration-color:rgba(77,163,255,.7); }}
    footer {{ padding:36px 0 52px; color:var(--muted); font-size:13px; }}
    @media (max-width:860px) {{ .nav-links{{display:none}} .section-head,.verify-band,.news-grid,.papers{{grid-template-columns:1fr}} .date-pill{{white-space:normal}} .source-list{{columns:1}} header{{min-height:88vh}} .news-item{{min-height:auto}} }}
  </style>
</head>
<body>
  <nav><div class="nav-inner"><div class="brand"><span class="mark">AI</span><span>Frontier Radar</span></div><div class="nav-links"><a href="#news">AI资讯</a><a href="#verify">核验规则</a><a href="#papers">前沿文献</a><a href="#sources">来源索引</a></div></div></nav>
  <header><div class="shell hero"><div class="eyebrow"><span class="pulse"></span>Verified AI Intelligence</div><h1>AI资讯核验与前沿文献雷达</h1><p>聚合公开渠道中的 AI 产品、模型、安全、产业与研究动态。每日自动刷新官方公开来源；社媒内容进入待核验池，不将传闻写成事实。</p><div class="hero-meta"><span class="chip">页面日期：{esc(today_cn)}</span><span class="chip">最近自动更新：{esc(generated)}</span><span class="chip">本期资讯：{len(news)} 条</span><span class="chip">重点覆盖：OpenAI / Google / Microsoft / Anthropic / 百度 / 腾讯</span></div><div class="family-note">此网页仅供波家人参考</div>{status_banner}</div></header>
  <main>
    <section id="news"><div class="shell"><div class="section-head"><div><h2>本期AI资讯</h2><p class="section-note">按自动抓取到的公开发布时间倒序整理。每条记录原始链接；关键事实仍建议人工复核，尤其是参数、价格、榜单和监管表述。</p></div><div class="date-pill">每日 08:00 自动刷新，北京时间</div></div><div class="news-grid">{news_cards}</div></div></section>
    <section id="verify"><div class="shell"><div class="section-head"><div><h2>核验规则</h2><p class="section-note">本页不是自动转载墙，而是可核验摘要。自动化只处理官方或可信公开页面；社媒爆料、截图、转述需要原帖与可信来源交叉确认。</p></div></div><div class="verify-band"><div class="panel"><h3>进入主资讯流的最低标准</h3><div class="checks"><div class="check"><span class="dot"></span><span>优先采用官网、官方博客、公告页、开发者文档、论文页、监管或会议页面。</span></div><div class="check"><span class="dot"></span><span>每条必须记录发布时间、主体、背景、关键事实和原始链接。</span></div><div class="check"><span class="dot"></span><span>对社媒内容，要求原帖链接与至少一个可信来源交叉确认；无法确认时标注为待核验。</span></div><div class="check"><span class="dot"></span><span>抓取失败或结构变化时不编造资讯，页面保留上次结果或提示需人工检查。</span></div></div></div><div class="panel"><h3>覆盖渠道状态</h3><div class="watchlist"><span>OpenAI 官网</span><span>Google Blog</span><span>Microsoft Source</span><span>Anthropic News</span><span>百度 AI 开放平台</span><span>百度智能云</span><span>腾讯官网</span><span>腾讯云动态</span><span class="pending">知乎：待人工核验</span><span class="pending">微博：待人工核验</span><span class="pending">抖音：待人工核验</span><span class="pending">微信公众号：待人工核验</span><span class="pending">小红书：待人工核验</span></div></div></div></div></section>
    <section id="papers"><div class="shell"><div class="section-head"><div><h2>AI 与控制前沿文献</h2><p class="section-note">方向先占位为 AI control、智能体安全、LLM+RL 控制、楼宇与机器人控制。后续可按你的研究方向继续收窄。</p></div><div class="date-pill">种子文献：国内外混合</div></div><div class="papers">{paper_cards}</div></div></section>
    <section id="sources"><div class="shell"><div class="section-head"><div><h2>来源索引</h2><p class="section-note">自动刷新脚本使用的公开来源。后续可以加入 RSS、API、人工审核队列和可信度评分。</p></div></div><div class="source-list">{source_links}</div></div></section>
  </main>
  <footer><div class="shell">AI Frontier Radar prototype. 自动刷新由 GitHub Actions 执行；最后生成时间：{esc(generated)}。</div></footer>
</body>
</html>
"""


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    news, failures = collect_news()
    NEWS_JSON.write_text(
        json.dumps(
            {
                "generated_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
                "news": news,
                "failures": failures,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    INDEX_PATH.write_text(render(news, failures), encoding="utf-8", newline="\n")
    print(f"Generated {INDEX_PATH} with {len(news)} news items and {len(failures)} failed sources.")


if __name__ == "__main__":
    main()
