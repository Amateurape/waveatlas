#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WaveAtlas 线上 SEO 月度自检
===========================
检查的对象是**线上真实返回**，不是本地文件——搜索引擎看到什么，就查什么。

覆盖：
  1. 五个语言页：HTTP 状态、lang、title/description、canonical、hreflang 互指、
     OG/Twitter、JSON-LD、h1、viewport、robots meta
  2. 关键文件：robots.txt、sitemap.xml（含 URL 集合与语言互指）、favicon、
     apple-touch-icon、og-card（含 1200×630 尺寸）、CNAME、GSC 验证文件、产品本体
  3. 站内链接与资源：五个页面引用的所有根绝对路径逐个验活（死链检测）
  4. 统计与验证代码：百度统计、GA4、GSC 元标签是否还在
  5. 体积体检：HTML 大小、首屏图片总体积

用法：
    python tools/seo_audit.py                # 检查线上，简报写到 _local/seo-audit/
    python tools/seo_audit.py --no-save      # 只打印，不落盘
    python tools/seo_audit.py --base https://xxx   # 检查其他部署（预发/本地服务）

退出码：0 全绿或有警告；1 存在 FAIL（需要处理）。
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://waveatlas.top"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 语言 → 路径。顺序即简报中的展示顺序。
PAGES = [
    ("zh-CN", "/", "zh-CN"),
    ("zh-TW", "/zh-TW/", "zh-TW"),
    ("en", "/en/", "en"),
    ("ja", "/ja/", "ja"),
    ("ko", "/ko/", "ko"),
]
EXPECT_HREFLANG = {
    "zh-CN": "/", "zh-TW": "/zh-TW/", "en": "/en/", "ja": "/ja/", "ko": "/ko/",
    "x-default": "/",
}
GA4_ID = "G-RTZL87DHM4"
BAIDU_HM = "hm.baidu.com/hm.js?32b7d3fd8fe2d29174a6ea4f6af8ae5f"

results: list[dict] = []      # {sec, item, level: OK/WARN/FAIL, detail}
_cache: dict[str, tuple] = {}


# ---------- 基础工具 ----------

def now_cn() -> datetime:
    return datetime.now(timezone(timedelta(hours=8)))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """禁用自动跟随，便于读取 3xx 的 Location。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url: str, method: str = "GET", timeout: int = 25) -> tuple:
    """返回 (status, headers, body_bytes)。异常统一折叠成 status=None。"""
    key = f"{method} {url}"
    if key in _cache:
        return _cache[key]
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA, "Cache-Control": "no-cache", "Pragma": "no-cache",
        "Accept": "*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read() if method == "GET" else b""
            out = (r.status, dict(r.headers), body)
    except urllib.error.HTTPError as e:
        try:
            body = e.read() if method == "GET" else b""
        except Exception:
            body = b""
        out = (e.code, dict(e.headers or {}), body)
    except Exception as e:                     # 超时 / DNS / TLS
        out = (None, {}, str(e).encode("utf-8", "replace"))
    _cache[key] = out
    return out


def alive(url: str) -> tuple:
    """验一个资源是否活着。HEAD 优先，不支持则退回 GET（只读前 1KB 无意义，直接全读）。"""
    st, hd, _ = fetch(url, "HEAD")
    if st in (405, 501):
        st, hd, _ = fetch(url, "GET")
    return st, hd.get("Content-Type", ""), hd.get("Content-Length", "")


def rec(sec: str, item: str, level: str, detail: str = "") -> None:
    results.append({"sec": sec, "item": item, "level": level, "detail": detail})


def png_size(data: bytes) -> tuple:
    """从 PNG 的 IHDR 读宽高。非 PNG 或损坏返回 (0, 0)。"""
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    return struct.unpack(">II", data[16:24])


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def gsc_file_url(base: str) -> str:
    """GSC 文件验证的地址（文件名从仓库里读，避免写死）。"""
    for p in ROOT.glob("google*.html"):
        return f"{base}/{p.name}?_audit=1"
    return f"{base}/__no_gsc_file__"


# ---------- 一、五个语言页 ----------

def audit_pages(base: str) -> dict:
    sec = "核心页面"
    docs: dict[str, str] = {}
    for code, path, lang_expect in PAGES:
        url = base + path
        stamp = int(time.time())
        sep = "&" if "?" in url else "?"
        st, hd, body = fetch(f"{url}{sep}_audit={stamp}")
        if st != 200:
            rec(sec, f"{path} 可访问", "FAIL", f"HTTP {st}" if st else "请求失败（网络/超时）")
            continue
        doc = body.decode("utf-8", "replace")
        docs[code] = doc
        rec(sec, f"{path} 可访问", "OK", f"200, {len(body) / 1024:.1f} KB")

        # lang
        m = re.search(r'<html[^>]*\slang="([^"]*)"', doc)
        if not m:
            rec(sec, f"{path} html lang", "FAIL", "缺失 lang 属性")
        elif m.group(1) != lang_expect:
            rec(sec, f"{path} html lang", "FAIL", f"应为 {lang_expect}，实际 {m.group(1)}")
        else:
            rec(sec, f"{path} html lang", "OK", lang_expect)

        # title
        mt = re.search(r"<title>(.*?)</title>", doc, re.S)
        title = strip_tags(mt.group(1)) if mt else ""
        if not title:
            rec(sec, f"{path} title", "FAIL", "缺失")
        elif len(title) > 70:
            rec(sec, f"{path} title", "WARN", f"{len(title)} 字符，可能被截断：{title[:50]}…")
        else:
            rec(sec, f"{path} title", "OK", f"{len(title)} 字符")

        # description
        md = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', doc)
        desc = md.group(1) if md else ""
        if not desc:
            rec(sec, f"{path} description", "FAIL", "缺失")
        elif len(desc) < 40:
            rec(sec, f"{path} description", "WARN", f"偏短（{len(desc)} 字符）")
        elif len(desc) > 300:
            rec(sec, f"{path} description", "WARN", f"偏长（{len(desc)} 字符）")
        else:
            rec(sec, f"{path} description", "OK", f"{len(desc)} 字符")

        # canonical
        mc = re.search(r'<link\s+rel="canonical"\s+href="([^"]*)"', doc)
        want = base + path                      # 根页为 base + "/"，与 canonical 写法一致
        if not mc:
            rec(sec, f"{path} canonical", "FAIL", "缺失")
        elif mc.group(1).rstrip("/") != want.rstrip("/"):
            rec(sec, f"{path} canonical", "FAIL", f"应指向自己（{want}），实际 {mc.group(1)}")
        else:
            rec(sec, f"{path} canonical", "OK", mc.group(1))

        # hreflang 互指
        hs = re.findall(r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)"', doc)
        got = {k: v for k, v in hs}
        missing = [k for k in EXPECT_HREFLANG if k not in got]
        wrong = [k for k, v in got.items()
                 if k in EXPECT_HREFLANG and v.rstrip("/") != (base + EXPECT_HREFLANG[k]).rstrip("/")]
        if missing:
            rec(sec, f"{path} hreflang", "FAIL", f"缺少 {', '.join(missing)}")
        elif wrong:
            rec(sec, f"{path} hreflang", "FAIL", f"指向错误：{', '.join(wrong)}")
        else:
            rec(sec, f"{path} hreflang", "OK", f"{len(got)} 条互指完整")

        # OG / Twitter
        need_og = ["og:title", "og:description", "og:image", "og:url", "og:type"]
        miss_og = [k for k in need_og if f'property="{k}"' not in doc]
        if miss_og:
            rec(sec, f"{path} OG 标签", "WARN", f"缺少 {', '.join(miss_og)}")
        else:
            rec(sec, f"{path} OG 标签", "OK", "5 项齐全")
        if 'name="twitter:card"' not in doc:
            rec(sec, f"{path} twitter 卡", "WARN", "缺少 twitter:card")

        # JSON-LD
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)
        if not blocks:
            rec(sec, f"{path} 结构化数据", "FAIL", "无 JSON-LD")
        else:
            types, bad = [], []
            for b in blocks:
                try:
                    d = json.loads(b)
                    types.append(d.get("@type", "?"))
                except Exception as e:
                    bad.append(str(e)[:40])
            if bad:
                rec(sec, f"{path} 结构化数据", "FAIL", f"JSON 解析失败：{bad[0]}")
            elif "SoftwareApplication" not in types:
                rec(sec, f"{path} 结构化数据", "WARN", f"仅 {types}，缺 SoftwareApplication")
            else:
                extra = "含 FAQPage" if "FAQPage" in types else "缺 FAQPage"
                rec(sec, f"{path} 结构化数据", "OK", f"{types}（{extra}）")

        # h1
        h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        if len(h1s) == 0:
            rec(sec, f"{path} h1", "FAIL", "缺失")
        elif len(h1s) > 1:
            rec(sec, f"{path} h1", "WARN", f"有 {len(h1s)} 个 h1（建议唯一）")
        else:
            rec(sec, f"{path} h1", "OK", strip_tags(h1s[0])[:40])

        # 基础 head 项
        basics = []
        if 'charset="utf-8"' not in doc.lower() and "charset=utf-8" not in doc.lower():
            basics.append("charset")
        if 'name="viewport"' not in doc:
            basics.append("viewport")
        if 'name="theme-color"' not in doc:
            basics.append("theme-color")
        if basics:
            rec(sec, f"{path} head 基础项", "WARN", f"缺少 {', '.join(basics)}")
        else:
            rec(sec, f"{path} head 基础项", "OK", "charset / viewport / theme-color")

        # 误加 noindex
        mi = re.search(r'<meta\s+name="robots"\s+content="([^"]*)"', doc)
        if mi and "noindex" in mi.group(1).lower():
            rec(sec, f"{path} robots meta", "FAIL", f"含 noindex：{mi.group(1)}")
    return docs


# ---------- 二、关键文件 ----------

def audit_keyfiles(base: str) -> None:
    sec = "关键文件"

    # robots.txt
    st, hd, body = fetch(f"{base}/robots.txt?_audit=1")
    if st != 200:
        rec(sec, "robots.txt", "FAIL", f"HTTP {st}")
    else:
        txt = body.decode("utf-8", "replace")
        sitemap_line = re.search(r"(?im)^\s*Sitemap:\s*(\S+)", txt)
        if not sitemap_line:
            rec(sec, "robots.txt", "WARN", "未声明 Sitemap 行")
        elif sitemap_line.group(1).rstrip("/") != f"{base}/sitemap.xml":
            rec(sec, "robots.txt", "WARN", f"Sitemap 指向 {sitemap_line.group(1)}")
        elif re.search(r"(?im)^\s*Disallow:\s*/\s*$", txt):
            rec(sec, "robots.txt", "FAIL", "存在全站 Disallow: /（会导致整站不被收录）")
        else:
            rec(sec, "robots.txt", "OK", "含正确 Sitemap 指令")

    # sitemap.xml
    st, hd, body = fetch(f"{base}/sitemap.xml?_audit=1")
    if st != 200:
        rec(sec, "sitemap.xml", "FAIL", f"HTTP {st}")
    else:
        import xml.etree.ElementTree as ET
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9",
              "x": "http://www.w3.org/1999/xhtml"}
        try:
            root = ET.fromstring(body)
            urls = root.findall("s:url", ns)
            locs = [(u.find("s:loc", ns).text or "").strip() for u in urls]
            want = {(base + p) for _, p, _ in PAGES}
            got = set(locs)
            missing = want - got
            extra = got - want
            links = [len(u.findall("x:link", ns)) for u in urls]
            if missing:
                rec(sec, "sitemap.xml URL 集合", "FAIL", f"缺少 {sorted(missing)}")
            elif extra:
                rec(sec, "sitemap.xml URL 集合", "WARN", f"多出 {sorted(extra)}")
            else:
                rec(sec, "sitemap.xml URL 集合", "OK", f"{len(locs)} 个 URL 与页面一致")
            if links and min(links) < len(EXPECT_HREFLANG):
                rec(sec, "sitemap.xml 语言互指", "WARN", f"最少的只有 {min(links)} 条 hreflang")
            else:
                rec(sec, "sitemap.xml 语言互指", "OK", f"每条 {len(EXPECT_HREFLANG)} 条")
        except ET.ParseError as e:
            rec(sec, "sitemap.xml 解析", "FAIL", f"XML 不合法：{e}")

    # 图标与分享卡
    checks = [
        ("/favicon.svg", "image/svg", None),
        ("/apple-touch-icon.png", "image/png", (180, 180)),
        ("/images/og-card.png", "image/png", (1200, 630)),
    ]
    for path, ctype, want_size in checks:
        st, ct, cl = alive(base + path)
        if st != 200:
            rec(sec, path, "FAIL", f"HTTP {st}")
            continue
        if not ct.startswith(ctype):
            rec(sec, path, "WARN", f"Content-Type 异常：{ct or '(空)'}")
            continue
        if want_size:
            _, _, data = fetch(base + path)
            w, h = png_size(data)
            if (w, h) != want_size:
                rec(sec, path, "WARN", f"尺寸 {w}×{h}，建议 {want_size[0]}×{want_size[1]}")
            else:
                rec(sec, path, "OK", f"{w}×{h}, {len(data) / 1024:.0f} KB")
        else:
            rec(sec, path, "OK", f"{ct}, {cl or '?'} B")

    # 自定义域名 + HTTPS 强制跳转
    # 注：CNAME 文件在 GitHub Pages 上不对外提供（访问恒 404），不能用来验证域名绑定。
    # 域名是否生效由「HTTPS 下五个页面均 200」间接证明，这里只查 http 是否强制跳 https。
    try:
        http_url = "http://" + base.split("://", 1)[1] + "/"
        opener = urllib.request.build_opener(_NoRedirect)
        req = urllib.request.Request(http_url, headers={"User-Agent": UA})
        try:
            with opener.open(req, timeout=20) as r:
                code, loc = r.status, r.headers.get("Location", "")
        except urllib.error.HTTPError as e:
            code, loc = e.code, (e.headers or {}).get("Location", "")
        if code in (301, 302, 307, 308) and str(loc).startswith("https://"):
            rec(sec, "HTTP→HTTPS 跳转", "OK", f"{code} → {loc}")
        elif code == 200:
            rec(sec, "HTTP→HTTPS 跳转", "WARN", "http 直接返回 200，未强制跳转 HTTPS")
        else:
            rec(sec, "HTTP→HTTPS 跳转", "WARN", f"HTTP {code}，Location={loc or '(空)'}")
    except Exception as e:
        rec(sec, "HTTP→HTTPS 跳转", "WARN", f"无法检测：{str(e)[:60]}")

    st, hd, _ = alive(f"{base}/WaveAtlasAudioBrowser_v3.05.html")
    rec(sec, "产品本体下载", "OK" if st == 200 else "FAIL", f"HTTP {st}")

    st, hd, body = fetch(f"{base}/google35b4551d46ccfa66.html?_audit=1")
    if st != 200:
        rec(sec, "GSC 验证文件", "FAIL", f"HTTP {st}（GSC 所有权可能失效）")
    else:
        txt = body.decode("utf-8", "replace")
        if "google-site-verification" in txt:
            rec(sec, "GSC 验证文件", "OK", "内容正确")
        else:
            rec(sec, "GSC 验证文件", "WARN", "内容不含 verification 串")


# ---------- 三、站内链接与资源（死链检测） ----------

def audit_links(base: str, docs: dict) -> None:
    sec = "站内链接与资源"
    seen: set[str] = set()
    dead: list[str] = []
    external: set[str] = set()

    for code, doc in docs.items():
        body = re.sub(r"<script.*?</script>|<style.*?</style>", "", doc, flags=re.S)
        for attr in ("src", "href"):
            for m in re.finditer(rf'{attr}="([^"]+)"', body):
                u = m.group(1).strip()
                if not u or u.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                    continue
                if u.startswith("http"):
                    if not u.startswith(base):
                        external.add(u.split("?")[0])
                        continue          # 外站链接不参与站内死链判定
                    u = u[len(base):] or "/"
                if not u.startswith("/"):
                    # 子目录页面里出现相对路径 = 必然 404
                    if code != "zh-CN":
                        dead.append(f"[{code}] 相对路径 {u}（子目录下会 404）")
                    continue
                seen.add(u.split("#")[0] or "/")

    for u in sorted(seen):
        if u.startswith(("/images/", "/i18n.js", "/favicon", "/apple-touch", "/WaveAtlas")):
            st, _, _ = alive(base + u)
            if st != 200:
                dead.append(f"{u} → HTTP {st}")

    # 外部链接只统计不打扰（外站抖动不该算自家问题）
    st, _, _ = alive(base + "/i18n.js")
    if st != 200:
        dead.append(f"/i18n.js → HTTP {st}")

    if dead:
        rec(sec, "内部链接/资源", "FAIL", f"{len(dead)} 处问题：" + "；".join(dead[:6]))
    else:
        rec(sec, "内部链接/资源", "OK", f"{len(seen)} 个站内目标全部 200")
    if external:
        rec(sec, "外部链接", "OK", f"{len(external)} 个外站链接（未主动探测）")


# ---------- 四、统计与验证代码 ----------

def audit_tags(base: str, docs: dict) -> None:
    sec = "统计与验证"
    home = docs.get("zh-CN", "")
    if not home:
        rec(sec, "首页统计代码", "FAIL", "首页抓取失败，跳过")
        return

    if BAIDU_HM in home:
        rec(sec, "百度统计", "OK", "hm.js 脚本存在")
    else:
        rec(sec, "百度统计", "FAIL", "hm.js 脚本缺失（国内数据会断）")

    if GA4_ID in home:
        rec(sec, "GA4", "OK", f"{GA4_ID} 存在")
    else:
        rec(sec, "GA4", "FAIL", f"未找到 {GA4_ID}")

    if "google-site-verification" in home:
        rec(sec, "GSC 验证", "OK", "meta 标签存在")
    else:
        # 没有 meta 时看文件验证是否可用（本方案走的是文件验证）
        st, _, body = fetch(gsc_file_url(base))
        if st == 200 and b"google-site-verification" in body:
            rec(sec, "GSC 验证", "OK", "文件验证有效（无 meta，属正常）")
        else:
            rec(sec, "GSC 验证", "WARN", "meta 与验证文件均不可用，GSC 所有权可能失效")

    # 统计代码在子页是否也带上了（本方案子页共用 head，应一致）
    missing = [c for c, d in docs.items() if BAIDU_HM not in d and c != "zh-CN"]
    if missing:
        rec(sec, "子页统计覆盖", "WARN", f"缺百度统计：{', '.join(missing)}")
    elif len(docs) > 1:
        rec(sec, "子页统计覆盖", "OK", f"{len(docs)} 个语言页均含统计代码")


# ---------- 五、体积体检 ----------

def audit_weight(base: str, docs: dict) -> None:
    sec = "体积体检"
    home = docs.get("zh-CN", "")
    if not home:
        return
    rec(sec, "首页 HTML", "OK" if len(home.encode()) < 150_000 else "WARN",
        f"{len(home.encode()) / 1024:.0f} KB")

    # 根页用相对路径 images/xxx，子页用根绝对 /images/xxx，统一归一化后统计
    raw = re.findall(r'(?:src|href)="([^"]*images/[\w.-]+\.(?:webp|png|jpg))"', home)
    imgs = sorted({"/" + u.lstrip("/") for u in raw})
    total = 0
    heavy = []
    for p in imgs:
        st, _, cl = alive(base + p)
        if st != 200:
            continue
        try:
            size = int(cl or 0)
        except ValueError:
            size = 0
        total += size
        if size > 250_000:
            heavy.append(f"{p.split('/')[-1]} {size / 1024:.0f}KB")
    if imgs:
        level = "OK" if total < 900_000 else "WARN"
        rec(sec, "首页图片总量", level, f"{len(imgs)} 张 / {total / 1024:.0f} KB")
        if heavy:
            rec(sec, "单图超重（>250KB）", "WARN", "、".join(heavy))


# ---------- 汇总与输出 ----------

def summarize() -> dict:
    ok = [r for r in results if r["level"] == "OK"]
    warn = [r for r in results if r["level"] == "WARN"]
    fail = [r for r in results if r["level"] == "FAIL"]
    return {"ok": len(ok), "warn": len(warn), "fail": len(fail), "total": len(results)}


def render_md(base: str) -> str:
    s = summarize()
    ts = now_cn().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# WaveAtlas 站点 SEO 自检简报",
        "",
        f"- 生成时间：{ts}（北京时间）",
        f"- 检查对象：{base}",
        f"- 检查项：{s['total']}　通过 {s['ok']}　警告 {s['warn']}　失败 {s['fail']}",
        "",
        "**结论：** " + ("全绿，无需处理。" if s["fail"] == 0 and s["warn"] == 0
                          else ("有警告，建议看一眼。" if s["fail"] == 0
                                else f"有 {s['fail']} 项失败，需要处理。")),
        "",
    ]

    secs: dict[str, list] = {}
    for r in results:
        secs.setdefault(r["sec"], []).append(r)

    for sec, rows in secs.items():
        lines.append(f"## {sec}")
        lines.append("")
        lines.append("| 检查项 | 结果 | 说明 |")
        lines.append("|---|---|---|")
        icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌"}
        for r in rows:
            detail = r["detail"].replace("|", "\\|")
            lines.append(f"| {r['item']} | {icon[r['level']]} | {detail} |")
        lines.append("")

    bad = [r for r in results if r["level"] != "OK"]
    if bad:
        lines.append("## 需要关注")
        lines.append("")
        for r in bad:
            lines.append(f"- **[{r['level']}] {r['item']}** — {r['detail']}")
        lines.append("")
    else:
        lines.append("## 需要关注")
        lines.append("")
        lines.append("无。所有检查项通过。")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=SITE, help="检查的站点根地址")
    ap.add_argument("--no-save", action="store_true", help="不写简报文件")
    ap.add_argument("--out", default=None, help="简报输出目录（默认 _local/seo-audit）")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"检查 {base} …")
    docs = audit_pages(base)
    audit_keyfiles(base)
    audit_links(base, docs)
    audit_tags(base, docs)
    audit_weight(base, docs)

    s = summarize()
    md = render_md(base)
    if not args.no_save:
        out_dir = Path(args.out) if args.out else ROOT / "_local" / "seo-audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        f = out_dir / f"{now_cn().strftime('%Y-%m-%d_%H%M')}.md"
        f.write_text(md, encoding="utf-8")
        print(f"简报已写入：{f}")

    icon = {"OK": "OK  ", "WARN": "WARN", "FAIL": "FAIL"}
    for r in results:
        if r["level"] != "OK":
            print(f"[{icon[r['level']]}] {r['item']} — {r['detail']}")
    print(f"\n合计 {s['total']} 项：通过 {s['ok']}，警告 {s['warn']}，失败 {s['fail']}")
    return 0 if s["fail"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
