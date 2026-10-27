#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WaveAtlas 落地页多语言页面构建脚本
=================================
把 index.html（简中母版）+ i18n.js（译文字典）烘焙成各语言独立页面：

    /            -> zh-CN（母版，手工维护）
    /zh-TW/      -> 繁中
    /en/         -> 英语
    /ja/         -> 日语
    /ko/         -> 韩语

每个输出页都做到：<html lang> 正确、title/description/OG/Twitter 已翻译、
canonical 指向自己、hreflang 五语互指、结构化数据 url/inLanguage 正确、
资源路径改根绝对（子目录下不会 404）、语言切换器高亮当前语言。

为什么必须烘焙而不是靠 JS 切换：搜索引擎只读服务端返回的 HTML，
JS 注入的译文对收录无效。这是多语言 SEO 的前提。

用法（改完 index.html 或 i18n.js 后必须重跑）：
    python tools/build_lang_pages.py
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
DICT_SRC = ROOT / "i18n.js"
SITE = "https://waveatlas.top"

# 目录名 -> (html lang, og:locale)
LANGS = {
    "zh-TW": ("zh-TW", "zh_TW"),
    "en": ("en", "en_US"),
    "ja": ("ja", "ja_JP"),
    "ko": ("ko", "ko_KR"),
}
ROOT_LANG = "zh-CN"

# 图片 alt 与色块 aria-label 是硬编码在 HTML 里的（不属 i18n 字典），
# 但搜索引擎会索引 alt，读屏软件会读 aria-label，所以一并翻译。
# 按图片文件名索引，键与 images/ 下的文件名去掉 .webp 后一致。
IMG_ALT = {
    "zh-TW": {
        "01-select-folder": "觀瀾音訊瀏覽器：選擇本機音訊資料夾的介面",
        "02-waveforms": "瀏覽資料夾內所有音訊的波形清單，自動標註 BPM 與情緒",
        "03-click-to-play": "點擊波形即播放對應音訊",
        "04-light-theme": "淺色主題下的音訊波形瀏覽器介面",
        "05-dark-theme": "深色主題下的音訊波形瀏覽器介面",
        "06-accent-red": "自訂主題色效果",
    },
    "en": {
        "01-select-folder": "WaveAtlas Audio Browser: choosing a local audio folder",
        "02-waveforms": "Waveform list of every audio file in the folder, with automatic BPM and mood tags",
        "03-click-to-play": "Click anywhere on a waveform to play that track instantly",
        "04-light-theme": "Light theme of the audio waveform browser",
        "05-dark-theme": "Dark theme of the audio waveform browser",
        "06-accent-red": "Custom accent colour applied across the interface",
    },
    "ja": {
        "01-select-folder": "WaveAtlas 音声ブラウザ：ローカルの音声フォルダを選択する画面",
        "02-waveforms": "フォルダ内の全音声ファイルの波形リスト（BPM とムードを自動表示）",
        "03-click-to-play": "波形をクリックすると即座に再生",
        "04-light-theme": "ライトテーマの音声波形ブラウザ画面",
        "05-dark-theme": "ダークテーマの音声波形ブラウザ画面",
        "06-accent-red": "カスタムアクセントカラーを適用した画面",
    },
    "ko": {
        "01-select-folder": "WaveAtlas 오디오 브라우저: 로컬 오디오 폴더 선택 화면",
        "02-waveforms": "폴더 내 모든 오디오 파일의 파형 목록, BPM과 무드 자동 표시",
        "03-click-to-play": "파형을 클릭하면 해당 오디오가 즉시 재생됩니다",
        "04-light-theme": "라이트 테마의 오디오 파형 브라우저 화면",
        "05-dark-theme": "다크 테마의 오디오 파형 브라우저 화면",
        "06-accent-red": "사용자 지정 강조 색상을 적용한 화면",
    },
}

OG_IMAGE_ALT = {
    "zh-TW": "WaveAtlas Audio Browser — 免費、本機、單一檔案的音訊波形瀏覽器",
    "en": "WaveAtlas Audio Browser — free, local, single-file audio waveform browser",
    "ja": "WaveAtlas Audio Browser — 無料・ローカル・単一ファイルの音声波形ブラウザ",
    "ko": "WaveAtlas Audio Browser — 무료, 로컬, 단일 파일 오디오 파형 브라우저",
}

# 主题色色块的无障碍标签：中文原文 -> 各语言译文
ARIA_DOTS = {
    "zh-TW": {"蓝色主题": "藍色主題", "紫色主题": "紫色主題", "绿色主题": "綠色主題",
              "黄色主题": "黃色主題", "橙色主题": "橙色主題", "红色主题": "紅色主題"},
    "en": {"蓝色主题": "Blue accent", "紫色主题": "Purple accent", "绿色主题": "Green accent",
           "黄色主题": "Yellow accent", "橙色主题": "Orange accent", "红色主题": "Red accent"},
    "ja": {"蓝色主题": "ブルーのアクセント", "紫色主题": "パープルのアクセント", "绿色主题": "グリーンのアクセント",
           "黄色主题": "イエローのアクセント", "橙色主题": "オレンジのアクセント", "红色主题": "レッドのアクセント"},
    "ko": {"蓝色主题": "블루 강조색", "紫色主题": "퍼플 강조색", "绿色主题": "그린 강조색",
           "黄色主题": "옐로 강조색", "橙色主题": "오렌지 강조색", "红色主题": "레드 강조색"},
}


def load_dicts() -> dict:
    """i18n.js 的字典是纯 JSON 兼容写法，直接抠出来解析。"""
    raw = DICT_SRC.read_text(encoding="utf-8")
    body = raw[raw.index("{"): raw.rindex("}") + 1]
    return json.loads(body)


def find_element_span(doc: str, attr: str, key: str):
    """定位 attr="key" 所属元素的 (内文起点, 内文终点)，用配平扫描处理嵌套标签。"""
    idx = doc.find(f'{attr}="{key}"')
    if idx < 0:
        return None
    lt = doc.rfind("<", 0, idx)
    name_m = re.match(r"<([a-zA-Z][\w-]*)", doc[lt:])
    if not name_m:
        return None
    tag = name_m.group(1)
    open_end = doc.find(">", idx)
    if open_end < 0:
        return None
    start = open_end + 1

    depth, pos = 1, start
    open_re = re.compile(r"<" + re.escape(tag) + r"\b", re.I)
    close_re = re.compile(r"</" + re.escape(tag) + r"\s*>", re.I)
    while True:
        o = open_re.search(doc, pos)
        c = close_re.search(doc, pos)
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


def set_inner(doc: str, attr: str, key: str, value: str, escape: bool) -> tuple:
    span = find_element_span(doc, attr, key)
    if not span:
        return doc, False
    s, e = span
    text = html.escape(value, quote=False) if escape else value
    return doc[:s] + text + doc[e:], True


def set_attr(doc: str, pattern: str, value: str) -> tuple:
    """替换某个固定 CSS 选择器对应的 content="..." 值。pattern 必须含三组：(前缀)(旧值)(后缀)"""
    new, n = re.subn(pattern, lambda m: m.group(1) + html.escape(value, quote=True) + m.group(3), doc, count=1)
    return new, n > 0


def build(lang_dir: str, dicts: dict) -> str:
    lang_code, og_locale = LANGS[lang_dir]
    d = dicts[lang_dir]
    page_url = f"{SITE}/{lang_dir}/"
    doc = SRC.read_text(encoding="utf-8")
    missing = []

    # --- 1. html lang ---
    doc = re.sub(r'<html lang="[^"]*">', f'<html lang="{lang_code}">', doc, count=1)

    # --- 2. 声明本页语言（供 JS 引擎优先采用，避免被浏览器语言覆盖）---
    doc = re.sub(r'window\.WA_LANG_FORCE="[^"]*"', f'window.WA_LANG_FORCE="{lang_code}"', doc, count=1)

    # --- 3. 正文译文烘焙 ---
    for key in d:
        doc, ok = set_inner(doc, "data-i18n", key, d[key], escape=True)
        if not ok:
            doc, ok = set_inner(doc, "data-i18n-html", key, d[key], escape=False)
    # 校验：所有标记都应该被替换过（保留标记本身，供 JS 二次对齐）

    # --- 4. head 元信息 ---
    doc = re.sub(r"<title>.*?</title>",
                 "<title>" + html.escape(d["doc.title"], quote=False) + "</title>",
                 doc, count=1, flags=re.S)

    head_targets = [
        (r'(<meta name="description" content=")([^"]*)(")', d["meta.desc"]),
        (r'(<meta property="og:title" content=")([^"]*)(")', d["doc.title"]),
        (r'(<meta property="og:description" content=")([^"]*)(")', d["meta.desc"]),
        (r'(<meta name="twitter:title" content=")([^"]*)(")', d["doc.title"]),
        (r'(<meta name="twitter:description" content=")([^"]*)(")', d["meta.desc"]),
        (r'(<meta property="og:url" content=")([^"]*)(")', page_url),
        (r'(<meta property="og:locale" content=")([^"]*)(")', og_locale),
        (r'(<link rel="canonical" href=")([^"]*)(")', page_url),
    ]
    for pat, val in head_targets:
        doc, ok = set_attr(doc, pat, val)
        if not ok:
            missing.append(pat[:40])

    # --- 5. 结构化数据：url / inLanguage ---
    doc = re.sub(r'("url":\s*")[^"]*(")', lambda m: m.group(1) + page_url + m.group(2), doc, count=1)
    doc = re.sub(r'("inLanguage":\s*)\[[^\]]*\]',
                 lambda m: m.group(1) + '["' + lang_code + '"]', doc, count=1)

    # --- 6. 资源路径改根绝对（子目录下否则全 404）---
    doc = doc.replace('src="images/', 'src="/images/')
    doc = doc.replace('src="i18n.js"', 'src="/i18n.js"')
    doc = doc.replace('href="WaveAtlasAudioBrowser_v3.05.html"',
                      'href="/WaveAtlasAudioBrowser_v3.05.html"')

    # --- 6.5 图片 alt / 分享卡 alt / 色块 aria-label 翻译 ---
    for fname, alt in IMG_ALT[lang_dir].items():
        doc = re.sub(
            r'(src="/images/' + re.escape(fname) + r'\.webp"[^>]*?alt=")[^"]*(")',
            lambda m, a=alt: m.group(1) + html.escape(a, quote=True) + m.group(2),
            doc, count=1)
    doc, _ = set_attr(doc, r'(<meta property="og:image:alt" content=")([^"]*)(")', OG_IMAGE_ALT[lang_dir])
    for zh_label, translated in ARIA_DOTS[lang_dir].items():
        doc = doc.replace(f'aria-label="{zh_label}"', f'aria-label="{html.escape(translated, quote=True)}"')

    # --- 7. 语言切换器：高亮当前语言 ---
    def fix_switch(m):
        inner = re.sub(r'\sclass="active"', "", m.group(2))
        inner = inner.replace(f'data-lang="{lang_code}"', f'data-lang="{lang_code}" class="active"')
        return m.group(1) + inner + m.group(3)

    doc = re.sub(r'(<div class="lang-switch"[^>]*>)(.*?)(</div>)', fix_switch, doc, count=1, flags=re.S)

    # --- 8. 剥离「非中文访客提示条」的 HTML 与配套 JS（子页已是对应语言，不需要）---
    doc = re.sub(r"<!-- LANG-HINT-START.*?<!-- LANG-HINT-END -->\s*", "", doc, flags=re.S)
    doc = re.sub(r"/\* LANG-HINT-START.*?/\* LANG-HINT-END \*/\s*", "", doc, flags=re.S)

    # --- 9. 生成标记 + 写盘 ---
    doc = doc.replace("<!DOCTYPE html>",
                      "<!DOCTYPE html>\n<!-- 由 tools/build_lang_pages.py 自动生成，请勿直接编辑；"
                      "改动请改 index.html 或 i18n.js 后重跑脚本 -->", 1)

    out_dir = ROOT / lang_dir
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(doc, encoding="utf-8", newline="")
    return lang_dir, len(doc), missing


def write_sitemap() -> int:
    """按同一份语言清单生成 sitemap.xml，含 xhtml:link 语言互指。
    这样加/减语言时 sitemap 不会和页面脱节。"""
    import datetime
    today = datetime.date.today().isoformat()
    entries = [(ROOT_LANG, f"{SITE}/", "1.0")] + \
              [(code, f"{SITE}/{folder}/", "0.9") for folder, (code, _) in LANGS.items()]

    def alternates(indent="    "):
        rows = [f'{indent}<xhtml:link rel="alternate" hreflang="{ROOT_LANG}" href="{SITE}/"/>']
        for folder, (code, _) in LANGS.items():
            rows.append(f'{indent}<xhtml:link rel="alternate" hreflang="{code}" href="{SITE}/{folder}/"/>')
        rows.append(f'{indent}<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/"/>')
        return "\n".join(rows)

    blocks = []
    for _code, url, pri in entries:
        blocks.append(
            "  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            "    <changefreq>weekly</changefreq>\n"
            f"    <priority>{pri}</priority>\n"
            f"{alternates()}\n"
            "  </url>")

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
           '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "\n".join(blocks) + "\n</urlset>\n")
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8", newline="")
    return len(entries)


def main() -> int:
    dicts = load_dicts()
    ok = True
    for lang_dir in LANGS:
        name, size, missing = build(lang_dir, dicts)
        flag = "OK" if not missing else "警告"
        print(f"[{flag}] {name:6s} index.html  {size:6d} 字节")
        if missing:
            ok = False
            print("     未匹配的 head 元素:", missing)
    n = write_sitemap()
    print(f"[OK] sitemap.xml  已生成 {n} 条 URL（含 hreflang 互指）")
    print("\n完成。提交前建议跑一遍 tools/check_lang_pages.py 做交叉校验。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
