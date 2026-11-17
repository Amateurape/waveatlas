#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 /app/ 在线版页面
=====================
读取单文件工具 WaveAtlasAudioBrowser_v3.05.html，注入：
  1. 顶部站点条（返回首页 / 下载离线版 / 赞助 / 反馈）
  2. 底部广告预留位（注释状态，不接真实代码）
输出到 app/index.html。工具本体零改动——以后工具升级，重跑本脚本即可。

站点条复用工具自身的 CSS 变量（var(--panel)/--text/--accent 等），
因此会自动跟随工具内的亮/暗主题切换，无需额外适配。

用法：python tools/build_app_page.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "WaveAtlasAudioBrowser_v3.05.html"
OUT = ROOT / "app" / "index.html"

SITE_BAR_STYLE = """<style>
  /* ===== 站点条（在线版外壳，独立于工具本体） ===== */
  .site-bar { height: 46px; flex: 0 0 46px; display: flex; align-items: center;
    justify-content: space-between; gap: 12px; padding: 0 16px;
    background: var(--panel); border-bottom: 1px solid var(--border);
    font-size: 13px; position: relative; z-index: 5; }
  .sb-brand { color: var(--text); text-decoration: none; font-weight: 600; white-space: nowrap; }
  .sb-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); margin-right: 7px; vertical-align: 1px; }
  .sb-sep { color: var(--text-dim); margin: 0 6px; }
  .sb-cur { color: var(--text-dim); font-weight: 400; }
  .sb-links { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; justify-content: flex-end; }
  .sb-links a { display: inline-flex; align-items: center; color: var(--text-dim); text-decoration: none; white-space: nowrap; }
  .sb-links a:hover { color: var(--accent); }
  /* 打赏按钮：经典文件夹黄胶囊 + 咖啡杯图标 */
  .sb-support { display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px;
    border-radius: 999px; background: #ffc107; color: #1a1a1a !important;
    font-size: 12px; font-weight: 700; text-decoration: none; white-space: nowrap;
    transition: transform .15s, background .15s, box-shadow .15s;
    box-shadow: 0 2px 10px rgba(255,193,7,.35); }
  .sb-support:hover { background: #ffca28; color: #1a1a1a !important; transform: translateY(-1px); }
  .sb-support .sb-cup { width: 14px; height: 14px; flex: 0 0 14px; }
  /* 让工具主体给站点条让出 46px，正好铺满视口 */
  .app { height: calc(100vh - 46px) !important; }
  @media (max-width: 560px) {
    .sb-links { gap: 10px; }
    .sb-cur, .sb-sep { display: none; }
    .sb-links a:not(.sb-support) { font-size: 12px; }
  }
</style>
"""

SITE_BAR_HTML = """
<div class="site-bar">
  <a class="sb-brand" href="/" title="WaveAtlas">
    <span class="sb-dot"></span>WaveAtlas<span class="sb-sep">/</span><span class="sb-cur" data-sb-i18n="sb.online">在线版</span>
  </a>
  <nav class="sb-links">
    <a href="/" data-sb-i18n="sb.home" title="Back to Home">Back to Home</a>
    <a href="/WaveAtlasAudioBrowser_v3.05.html" download="WaveAtlasAudioBrowser_v3.05.html" data-sb-i18n="sb.download" title="Download">Download</a>
    <a class="sb-support" href="https://ko-fi.com/amateurape" target="_blank" rel="noopener" data-sb-i18n="sb.support" title="Buy me a coffee"><svg class="sb-cup" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h13v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8z"/><path d="M17 9h1.5a2.5 2.5 0 0 1 0 5H17"/><path d="M8 2v3M12 2v3"/></svg><span class="sb-label">Buy me a coffee</span></a>
    <a href="https://github.com/Amateurape/waveatlas/issues" target="_blank" rel="noopener" data-sb-i18n="sb.feedback" title="Report an Issue">Report an Issue</a>
  </nav>
</div>
"""

# 站点条多语言字典 + 同步脚本。工具本体零改动：注入的脚本独立监听 langSelect
# 的 change 事件并读取 localStorage(audioBrowser.lang)，与工具语言状态保持一致。
# 语言代码与工具内置 LANGUAGES 一致：en / zh-Hans / zh-Hant / ja / ko / fr / de。
SITE_BAR_I18N_JS = """<script>
(function () {
  var DICT = {
    'en':      { 'sb.online':'Online',   'sb.home':'Back to Home',  'sb.download':'Download',      'sb.support':'Buy me a coffee',      'sb.feedback':'Report an Issue' },
    'zh-Hans': { 'sb.online':'在线版',    'sb.home':'回到首页',      'sb.download':'下载离线版',    'sb.support':'请我喝杯咖啡',         'sb.feedback':'问题反馈' },
    'zh-Hant': { 'sb.online':'線上版',    'sb.home':'回到首頁',      'sb.download':'下載離線版',    'sb.support':'請我喝杯咖啡',         'sb.feedback':'問題回饋' },
    'ja':      { 'sb.online':'オンライン','sb.home':'ホームへ戻る',  'sb.download':'ダウンロード',  'sb.support':'コーヒーをごちそうする','sb.feedback':'問題を報告' },
    'ko':      { 'sb.online':'온라인',    'sb.home':'홈으로 돌아가기','sb.download':'다운로드',      'sb.support':'커피 한 잔 사주세요',  'sb.feedback':'문제 보고' },
    'fr':      { 'sb.online':'En ligne', 'sb.home':'Retour accueil','sb.download':'Télécharger',  'sb.support':'Offrez-moi un café',  'sb.feedback':'Signaler un problème' },
    'de':      { 'sb.online':'Online',   'sb.home':'Zur Startseite','sb.download':'Herunterladen','sb.support':'Kauf mir einen Kaffee','sb.feedback':'Problem melden' }
  };
  function applySiteBar() {
    var sel = document.getElementById('langSelect');
    var code = sel ? sel.value : '';
    if (!code) { try { code = localStorage.getItem('audioBrowser.lang') || ''; } catch (e) {} }
    var pack = DICT[code] || DICT['en'];
    document.querySelectorAll('[data-sb-i18n]').forEach(function (el) {
      var k = el.getAttribute('data-sb-i18n');
      if (pack[k] == null) return;
      // 打赏按钮内含 SVG 图标，只改 .sb-label 文字，避免 textContent 抹掉图标
      var label = el.querySelector('.sb-label');
      if (label) label.textContent = pack[k];
      else el.textContent = pack[k];
      el.setAttribute('title', pack[k]);
    });
  }
  applySiteBar();
  var sel = document.getElementById('langSelect');
  if (sel) sel.addEventListener('change', applySiteBar);
})();
</script>
"""

AD_SLOT = """
<!-- ===== AD SLOT RESERVED · 广告预留位（当前注释状态，不接真实代码） =====
     流量起来后再启用（AdSense / Adsterra），启用前需先补隐私政策页。
     注意：当前 .app 占满剩余视口，启用广告时需相应调整 .app 高度或改为可滚动布局。
<div class="ad-slot" style="height:90px;display:flex;align-items:center;justify-content:center;
     background:var(--panel-2);border-top:1px solid var(--border);color:var(--text-dim);">
  Advertisement
</div>
============================================================================== -->
"""


def main():
    doc = SRC.read_text(encoding="utf-8")

    # 1. 注入覆盖样式（在 </head> 前）
    if "</head>" not in doc:
        raise SystemExit("错误：工具源码找不到 </head>")
    doc = doc.replace("</head>", SITE_BAR_STYLE + "</head>", 1)

    # 2. 注入站点条（在 <body> 后、工具 .app 之前）
    if "<body>" not in doc:
        raise SystemExit("错误：工具源码找不到 <body>")
    doc = doc.replace("<body>", "<body>" + SITE_BAR_HTML, 1)

    # 3. 注入广告预留位 + 站点条多语言同步脚本（在工具脚本执行完之后）
    if "</body>" not in doc:
        raise SystemExit("错误：工具源码找不到 </body>")
    doc = doc.replace("</body>", AD_SLOT + SITE_BAR_I18N_JS + "</body>", 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8", newline="\n")

    checks = {
        "站点条": doc.count('class="site-bar"'),
        "多语言标记": doc.count('data-sb-i18n='),
        "七语字典": doc.count("'sb.support':"),
        "语言同步脚本": doc.count("sel.addEventListener('change', applySiteBar)"),
        "打赏按钮": doc.count('class="sb-support"'),
        "咖啡杯图标": doc.count('class="sb-cup"'),
        "文案容器": doc.count('class="sb-label"'),
        "打赏Ko-fi链接": doc.count("ko-fi.com/amateurape"),
        "下载入口": doc.count('download="WaveAtlasAudioBrowser_v3.05.html"'),
        "反馈入口": doc.count("github.com/Amateurape/waveatlas/issues"),
        "广告预留": doc.count("AD SLOT RESERVED"),
        "工具主体": doc.count('class="app"'),
    }
    print(f"[OK] {OUT.relative_to(ROOT)}  {len(doc.encode('utf-8'))} 字节")
    for name, n in checks.items():
        flag = "OK" if n >= 1 else "缺失!"
        print(f"  [{flag}] {name}: {n}")


if __name__ == "__main__":
    main()
