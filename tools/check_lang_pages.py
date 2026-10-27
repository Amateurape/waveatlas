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
LANGS = {"zh-TW": "zh-TW", "en": "en", "ja": "ja", "ko": "ko_KR" and "ko"}
ALL = {"zh-CN": "https://waveatlas.top/"}
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
    expect = {"zh-CN": f"{SITE}/", "zh-TW": f"{SITE}/zh-TW/", "en": f"{SITE}/en/",
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

    # 9. 是否残留中文（en/ja/ko 页）
    if lang_code in ("en", "ja", "ko"):
        leftover = len(re.findall(r"[\u4e00-\u9fff]", re.sub(r"<script.*?</script>|<style.*?</style>", "", doc, flags=re.S)))
        if leftover > 0:
            warnings.append(f"{tag} 仍含 {leftover} 个中文字符（品牌名/注释属正常，需人工确认）")

    # 10. 相对资源路径（子目录下会 404）
    rel = [u for u in re.findall(r'(?:src|href)="([^"#][^"]*)"', doc)
           if not u.startswith(("/", "http", "mailto:", "tel:"))]
    if rel:
        errors.append(f"{tag} 存在相对路径（子页会 404）: {sorted(set(rel))[:5]}")

    # 11. 切换器高亮唯一且正确
    m = re.search(r'(<div class="lang-switch"[^>]*>)(.*?)(</div>)', doc, re.S)
    if not m:
        errors.append(f"{tag} 找不到语言切换器")
    else:
        actives = re.findall(r'data-lang="([^"]+)"\s+class="active"', m.group(2))
        if actives != [lang_code]:
            errors.append(f"{tag} 切换器高亮错误: {actives}")

    # 12. 提示条应已剥离
    if "LANG-HINT" in doc or 'id="langHint"' in doc:
        errors.append(f"{tag} 提示条残留（子页不应包含）")


def main():
    dicts = load_dicts()
    # 根页单独检查（语言固定 zh-CN）
    root = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r'window\.WA_LANG_FORCE="([^"]*)"', root)
    if not m or m.group(1) != "zh-CN":
        errors.append("[zh-CN] 根页 WA_LANG_FORCE 不是 zh-CN")
    hl = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', root))
    if len(hl) != 6:
        errors.append(f"[zh-CN] hreflang 数量 {len(hl)}，应为 6")
    if "i18n.js" not in root:
        errors.append("[zh-CN] 根页缺少 i18n.js 引用")

    for lang_dir, lang_code in LANGS.items():
        p = ROOT / lang_dir / "index.html"
        if not p.exists():
            errors.append(f"[{lang_code}] 页面不存在: {p}")
            continue
        check_page(lang_code, p, dicts)

    print(f"检查完成：{len(LANGS) + 1} 个页面")
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
