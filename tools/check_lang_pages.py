#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多语言页面交叉校验
=================
逐个语言页检查：lang 属性、title、canonical、hreflang 互指、OG、结构化数据、
译文是否真的落进了 HTML、资源路径是否为根绝对、切换器高亮、提示条是否已剥离。

用法：python tools/check_lang_pages.py
退出码 0 = 全部通过；1 = 有问题（详情见输出）。
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://waveatlas.top"
HOME_LANG = "en"
# 语言 key -> 目录；en 为首页（根目录），zh-CN 为新增子目录
LANGS = {"zh-CN": "zh-CN", "zh-TW": "zh-TW", "ja": "ja", "ko": "ko"}
ALL = {"en": f"{SITE}/"}
for k in LANGS:
    ALL[LANGS[k]] = f"{SITE}/{k}/"

errors = []
warnings = []


def load_dicts():
    raw = (ROOT / "i18n.js").read_text(encoding="utf-8")
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])


def span(doc, attr, key):
    idx = doc.find(f'{attr}="{key}"')
    if idx < 0:
        return None
    lt = doc.rfind("<", 0, idx)
    m = re.match(r"<([a-zA-Z][\w-]*)", doc[lt:])
    if not m:
        return None
    tag = m.group(1)
    oe = doc.find(">", idx)
    start, depth, pos = oe + 1, 1, oe + 1
    o_re = re.compile(r"<" + re.escape(tag) + r"\b", re.I)
    c_re = re.compile(r"</" + re.escape(tag) + r"\s*>", re.I)
    while True:
        o, c = o_re.search(doc, pos), c_re.search(doc, pos)
        if not c:
            return None
        if o and o.start() < c.start():
            depth += 1
            pos = o.end()
        else:
            depth -= 1
            if depth == 0:
                return start, c.start()
            pos = c.end()


def check_page(lang_code, path, dicts):
    doc = path.read_text(encoding="utf-8")
    tag = f"[{lang_code}]"
    target = dicts[lang_code]
    zh = dicts["zh-CN"]
    page_url = ALL[lang_code]

    # 1. html lang
    m = re.search(r'<html lang="([^"]*)"', doc)
    if not m or m.group(1) != lang_code:
        errors.append(f"{tag} html lang 错误: {m.group(1) if m else '缺失'}")

    # 2. 强制语言声明
    m = re.search(r'window\.WA_LANG_FORCE="([^"]*)"', doc)
    if not m or m.group(1) != lang_code:
        errors.append(f"{tag} WA_LANG_FORCE 错误: {m.group(1) if m else '缺失'}")

    # 3. title 与描述
    m = re.search(r"<title>(.*?)</title>", doc, re.S)
    if not m or html.unescape(m.group(1)).strip() != target["doc.title"].strip():
        errors.append(f"{tag} title 未按译文生成")
    m = re.search(r'<meta name="description" content="([^"]*)"', doc)
    if not m or html.unescape(m.group(1)).strip() != target["meta.desc"].strip():
        errors.append(f"{tag} meta description 未按译文生成")

    # 4. canonical 指向自己
    m = re.search(r'<link rel="canonical" href="([^"]*)"', doc)
    if not m or m.group(1) != page_url:
        errors.append(f"{tag} canonical 错误: {m.group(1) if m else '缺失'}（应为 {page_url}）")

    # 5. hreflang 六条互指
    hl = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', doc))
    expect = {"en": f"{SITE}/", "zh-CN": f"{SITE}/zh-CN/", "zh-TW": f"{SITE}/zh-TW/",
              "ja": f"{SITE}/ja/", "ko": f"{SITE}/ko/", "x-default": f"{SITE}/"}
    for k, v in expect.items():
        if hl.get(k) != v:
            errors.append(f"{tag} hreflang {k} 缺失或错误: {hl.get(k)}")

    # 6. OG
    m = re.search(r'<meta property="og:url" content="([^"]*)"', doc)
    if not m or m.group(1) != page_url:
        errors.append(f"{tag} og:url 错误: {m.group(1) if m else '缺失'}")

    # 7. 结构化数据
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
        try:
            data = json.loads(block)
        except Exception as e:
            errors.append(f"{tag} 结构化数据 JSON 非法: {e}")
            continue
        if data.get("@type") == "SoftwareApplication":
            if data.get("url") != page_url:
                errors.append(f"{tag} JSON-LD url 错误: {data.get('url')}")
            il = data.get("inLanguage")
            if il != [lang_code]:
                errors.append(f"{tag} JSON-LD inLanguage 错误: {il}")

    # 8. 译文是否真的落进 HTML（逐元素比对）
    bad = []
    for key, val in target.items():
        sp = span(doc, "data-i18n", key)
        is_html_key = False
        if not sp:
            sp = span(doc, "data-i18n-html", key)
            is_html_key = True
        if not sp:
            continue
        got = doc[sp[0]:sp[1]]
        got_cmp = got if is_html_key else html.unescape(got)
        if got_cmp.strip() != val.strip():
            bad.append(key)
    if bad:
        errors.append(f"{tag} {len(bad)} 处译文未落盘: {bad[:5]}")

    # 8b. 浮标文案是否落进 title 属性（data-tip-key 元素）
    bad_tip = []
    for key, val in target.items():
        if not key.endswith(".tip"):
            continue
        m = re.search(r'data-tip-key="' + re.escape(key) + r'"[^>]*\btitle="([^"]*)"', doc)
        if not m or html.unescape(m.group(1)).strip() != val.strip():
            bad_tip.append(key)
    if bad_tip:
        errors.append(f"{tag} {len(bad_tip)} 处浮标未落盘: {bad_tip[:5]}")

    # 9. 是否残留中文（zh-CN 页本身是中文，不检查；其余语言页检查）
    #    英文首页含给中文访客的提示条（中文文案属预期），先剥掉提示条再统计
    if lang_code in ("en", "ja", "ko", "zh-TW"):
        body = re.sub(r"<script.*?</script>|<style.*?</style>", "", doc, flags=re.S)
        if lang_code == "en":
            body = re.sub(r"<!-- LANG-HINT-START.*?<!-- LANG-HINT-END -->", "", body, flags=re.S)
        leftover = len(re.findall(r"[\u4e00-\u9fff]", body))
        if leftover > 0:
            warnings.append(f"{tag} 仍含 {leftover} 个中文字符（品牌名/注释属正常，需人工确认）")

    # 10. 相对资源路径（子目录下会 404）
    rel = [u for u in re.findall(r'(?:src|href)="([^"#][^"]*)"', doc)
           if not u.startswith(("/", "http", "mailto:", "tel:"))
           and not u.split("?")[0] == "i18n.js"]  # i18n.js 可带破缓存查询串，属同目录本地资源
    if rel:
        errors.append(f"{tag} 存在相对路径（子页会 404）: {sorted(set(rel))[:5]}")

    # 11. 切换器高亮唯一且正确（下拉菜单里 data-lang="xx" class="active"）
    if 'id="langSwitch"' not in doc or 'id="langMenu"' not in doc:
        errors.append(f"{tag} 找不到语言下拉切换器")
    else:
        actives = re.findall(r'data-lang="([^"]+)"\s+class="active"', doc)
        if actives != [lang_code]:
            errors.append(f"{tag} 切换器高亮错误: {actives}")

    # 12. 提示条：英文首页应保留（提示中文访客），其他语言页应剥离
    has_hint = "LANG-HINT" in doc or "langHint" in doc
    if lang_code == "en":
        if not has_hint:
            errors.append(f"{tag} 英文首页缺少中文访客提示条")
    elif has_hint:
        errors.append(f"{tag} 提示条残留（非首页不应包含 HTML 或配套 JS）")


def main():
    dicts = load_dicts()
    # 英文首页（根目录 index.html）走完整检查
    check_page("en", ROOT / "index.html", dicts)

    # 其余四语页在各自子目录
    for lang_dir, lang_code in LANGS.items():
        p = ROOT / lang_dir / "index.html"
        if not p.exists():
            errors.append(f"[{lang_code}] 页面不存在: {p}")
            continue
        check_page(lang_code, p, dicts)

    # 旧 /en/ 跳转页应存在且指向首页
    legacy = ROOT / "en" / "index.html"
    if not legacy.exists():
        errors.append("[/en/] 旧链接跳转页不存在")
    else:
        page = legacy.read_text(encoding="utf-8")
        if 'url=/' not in page and 'url="/"' not in page:
            errors.append("[/en/] 跳转页未指向首页 /")

    print(f"检查完成：{len(LANGS) + 2} 个页面（含首页与旧链接跳转页）")
    for w in warnings:
        print("  ⚠ " + w)
    if errors:
        print(f"\n发现 {len(errors)} 个问题：")
        for e in errors:
            print("  ✗ " + e)
        return 1
    print("  ✓ 全部检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
