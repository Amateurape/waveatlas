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

# GA4：只统计页面与交互事件，不采集、不上传任何音频内容
ANALYTICS = """<!-- WaveAtlas 在线版：GA4（页面 + 交互事件；不触碰音频数据） -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RTZL87DHM4"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-RTZL87DHM4', { anonymize_ip: true });
</script>
"""

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
  // 打赏链接分流：简中（zh-Hans）走爱发电（国内微信/支付宝），其余 6 语保持 Ko-fi。
  // 与落地页简中页策略一致；文案/图标不动，只换跳转目标。
  var SUPPORT_HREF = { 'zh-Hans': 'https://afdian.com/a/amateurape' };
  var DEFAULT_SUPPORT_HREF = 'https://ko-fi.com/amateurape';
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
    // 打赏链接随语言切换：简中→爱发电，其他→Ko-fi
    var supportBtn = document.querySelector('.sb-support');
    if (supportBtn) supportBtn.href = SUPPORT_HREF[code] || DEFAULT_SUPPORT_HREF;
  }
  applySiteBar();
  var sel = document.getElementById('langSelect');
  if (sel) sel.addEventListener('change', applySiteBar);
})();
</script>
"""

# ============================================================
# 浏览器兼容横幅 + 内置示例音频（P0，为外链分发准备）
# ------------------------------------------------------------
# 目的：
#   1. 非 Chromium / 移动端访客一眼看到"为什么不能用"，而不是点了按钮才被 toast 告知；
#   2. 访客手边没有成文件夹的音频时，一键载入 3 段内置示例，直接看到波形与播放效果。
# 实现要点（工具本体零改动的关键）：
#   工具全程只在一处调用 window.showDirectoryPicker（pickFolder 内）。点击选择文件夹的
#   瞬间把它替换成返回"内存里伪造的文件夹句柄"，工具自己的 loadDir / 解码 / 画波形流程
#   原样执行；结束后立即还原。示例音频：
#     1. 鼓组 loop 在浏览器里现算现生成（不占页面体积）；
#     2. 《天鹅》大提琴（45s，从大提琴进入点起）+ 《High Flight》诗歌
#        整首朗读（47.5s）是真实录音 mp3，放在 app/demo/ 下，点击示例按钮时才懒加载
#        （合计约 930KB，不拖慢首屏）。长度故意给足：让访客真正体验"看波形跳转播放"。
#   素材版权（可放心分发）：
#     - The Swan：Camille Saint-Saëns, Le Cygne (No. 13)，Matilda Colliard（大提琴）&
#       Stefano Ligoratti（钢琴）2015 现场录音，Wikimedia Commons，CC BY 4.0
#       （来源：IMSLP；曲谱本身已入公有领域）。
#     - High Flight（John Gillespie Magee Jr., 1921）：诗已入公有领域；朗读为 LibriVox
#       志愿者 brenlo，Public Domain Mark 1.0（librivox.org，按惯例在页面注释中致谢）。
# ============================================================

EXTRA_STYLE = """<style>
  /* ===== 浏览器兼容横幅 ===== */
  .compat-bar { display: none; height: 34px; flex: 0 0 34px; align-items: center;
    justify-content: center; gap: 8px; padding: 0 12px; font-size: 12.5px;
    background: #fff4d6; color: #6b4a00; border-bottom: 1px solid #eed79a;
    text-align: center; line-height: 1.3; }
  body.has-compat .compat-bar { display: flex; }
  body.has-compat .app { height: calc(100vh - 46px - 34px) !important; }
  .compat-bar a { color: #6b4a00; font-weight: 700; text-decoration: underline; white-space: nowrap; }
  .compat-bar .cb-msg { min-width: 0; }
  .compat-bar .cb-close { flex: 0 0 auto; border: 0; background: transparent; color: #6b4a00;
    opacity: .55; cursor: pointer; font-size: 16px; line-height: 1; padding: 2px 4px; }
  .compat-bar .cb-close:hover { opacity: 1; }
  @media (max-width: 560px) { .compat-bar { font-size: 11.5px; height: 40px; flex: 0 0 40px; }
    body.has-compat .app { height: calc(100vh - 46px - 40px) !important; } }

  /* ===== 侧栏「先看效果」示例音频按钮 ===== */
  .demo-btn { margin-top: 6px; width: 100%; padding: 7px 10px; border-radius: 7px;
    border: 1px dashed var(--accent); background: transparent; color: var(--accent);
    font-size: 12.5px; font-weight: 600; cursor: pointer; font-family: inherit;
    transition: background .15s, transform .15s; }
  .demo-btn:hover { background: rgba(127,127,127,.12); }
  .demo-btn:active { transform: translateY(1px); }
</style>
"""

COMPAT_BAR_HTML = """
<div class="compat-bar" role="status">
  <span class="cb-msg" data-cb-i18n="cb.msg">Folder loading needs Chrome or Edge 86+. The built-in demo still works here.</span>
  <a href="https://www.google.com/chrome/" target="_blank" rel="noopener" data-cb-i18n="cb.link">Get Chrome</a>
  <button class="cb-close" type="button" aria-label="Dismiss">×</button>
</div>
"""

COMPAT_DEMO_JS = r"""<script>
(function () {
  'use strict';
  /* ---------- 多语言（与工具内置 7 语一致） ---------- */
  var DICT = {
    'en':      { 'cb.msg':'Local folder loading needs Chrome or Edge 86+. The built-in demo still works here.',
                 'cb.link':'Get Chrome', 'demo.btn':'Preview (3 samples)' },
    'zh-Hans': { 'cb.msg':'加载本地文件夹需要 Chrome / Edge 86+；内置示例音频在这里仍可播放。',
                 'cb.link':'安装 Chrome', 'demo.btn':'先看效果（3 段示例）' },
    'zh-Hant': { 'cb.msg':'載入本機資料夾需要 Chrome / Edge 86+；內建範例音訊在這裡仍可播放。',
                 'cb.link':'安裝 Chrome', 'demo.btn':'先看效果（3 段範例）' },
    'ja':      { 'cb.msg':'ローカルフォルダーの読み込みには Chrome / Edge 86+ が必要です。内蔵デモは再生できます。',
                 'cb.link':'Chrome を入手', 'demo.btn':'まず効果を見る（3 曲）' },
    'ko':      { 'cb.msg':'로컬 폴더 불러오기는 Chrome / Edge 86+ 에서만 됩니다. 내장 데모는 재생됩니다.',
                 'cb.link':'Chrome 설치', 'demo.btn':'먼저 효과 보기 (3개)' },
    'fr':      { 'cb.msg':"Le chargement d'un dossier local nécessite Chrome ou Edge 86+. La démo intégrée fonctionne ici.",
                 'cb.link':'Installer Chrome', 'demo.btn':'Aperçu (3 extraits)' },
    'de':      { 'cb.msg':'Lokale Ordner benötigen Chrome oder Edge 86+. Die eingebaute Demo läuft trotzdem.',
                 'cb.link':'Chrome holen', 'demo.btn':'Vorschau (3 Clips)' }
  };

  /* ---------- 埋点：GA4 事件（未加载 GA 时静默跳过，不影响功能） ---------- */
  function track(name, params) {
    try {
      if (typeof window.gtag === 'function') window.gtag('event', name, params || {});
    } catch (e) {}
  }
  /* 监听文件列表真正出现行数 —— 这是"访客到底用没用起来"的唯一可信信号 */
  function watchLoad(source, timeoutMs) {
    var deadline = Date.now() + (timeoutMs || 20000);
    var timer = setInterval(function () {
      var n = document.querySelectorAll('#fileList .file-row').length;
      if (n > 0) {
        clearInterval(timer);
        track('files_loaded', { source: source, file_count: n });
      } else if (Date.now() > deadline) {
        clearInterval(timer);
        track('files_load_failed', { source: source });
      }
    }, 500);
  }
  /* 给真实的目录选择加埋点：用户点了"允许"还是"取消" */
  function hookRealPicker() {
    if (window.__waPickerHooked) return;
    if (typeof window.showDirectoryPicker !== 'function') return;
    var orig = window.showDirectoryPicker;
    window.showDirectoryPicker = function () {
      var p = orig.apply(window, arguments);
      if (p && typeof p.then === 'function') {
        p.then(function () { track('folder_granted'); watchLoad('folder'); })
         .catch(function () { track('folder_cancelled'); });
      }
      return p;
    };
    window.__waPickerHooked = true;
  }

  function curLang() {
    var sel = document.getElementById('langSelect');
    var code = sel ? sel.value : '';
    if (!code) { try { code = localStorage.getItem('audioBrowser.lang') || ''; } catch (e) {} }
    return DICT[code] ? code : 'en';
  }
  function t2(k) {
    var p = DICT[curLang()] || DICT['en'];
    return p[k] || DICT['en'][k] || '';
  }

  /* ---------- 示例音频 ----------
     第 1 段（鼓 loop）：运行时合成 WAV，零文件、零版权风险；
     第 2、3 段（大提琴 / 诗歌朗读）：真实录音 mp3，点击时才从 demo/ 懒加载，
     页面本身不内嵌音频，不拖慢首屏。
     Credits: 02 "The Swan" (Le Cygne) — perf. Matilda Colliard (cello) & Stefano
     Ligoratti (piano), 2015 (CC BY 4.0, Wikimedia Commons / IMSLP);
     03 "High Flight" by John Gillespie Magee Jr., read by brenlo (LibriVox, public
     domain, librivox.org). */
  var SR = 22050, DUR = 12, N = SR * DUR;

  function toWav(samples) {
    var n = samples.length, buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf), i;
    function tag(off, s) { for (var k = 0; k < s.length; k++) v.setUint8(off + k, s.charCodeAt(k)); }
    tag(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); tag(8, 'WAVE'); tag(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, SR, true); v.setUint32(28, SR * 2, true);
    v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    tag(36, 'data'); v.setUint32(40, n * 2, true);
    for (i = 0; i < n; i++) {
      var s = samples[i];
      if (s > 1) s = 1; else if (s < -1) s = -1;
      v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new Uint8Array(buf);
  }
  function normalize(b, peak) {
    var m = 0, i;
    for (i = 0; i < b.length; i++) { var a = b[i] < 0 ? -b[i] : b[i]; if (a > m) m = a; }
    if (m > 0) { var g = (peak || 0.88) / m; for (i = 0; i < b.length; i++) b[i] *= g; }
    return b;
  }
  function addAt(buf, i0, len, fn) {
    for (var i = 0; i < len; i++) {
      var j = i0 + i;
      if (j < 0 || j >= buf.length) continue;
      buf[j] += fn(i / SR, i);
    }
  }
  /* 一阶低通：削掉刺耳的高频毛刺，听感变暖（人耳对 4k 以上的噪声最敏感） */
  function lowpass(b, fc) {
    var a = 1 - Math.exp(-2 * Math.PI * fc / SR), y = 0;
    for (var i = 0; i < b.length; i++) { y += a * (b[i] - y); b[i] = y; }
    return b;
  }
  /* 1) 鼓组 loop：瞬态密集，波形是尖刺状 */
  function drumLoop() {
    var b = new Float32Array(N), beat = 60 / 100, bar = beat * 4, k;

    /* 底鼓：音高快速下潜 + 轻微饱和，低频更结实 */
    function kick(amp) {
      return function (t) {
        var f = 47 + 64 * Math.exp(-t * 26);
        var body = Math.sin(6.2831853 * f * t) * Math.exp(-t * 7.5);
        var click = Math.exp(-t * 300) * 0.35;
        return Math.tanh((body + click) * 1.6) * amp;
      };
    }
    /* 军鼓：噪声先低通（去掉白噪的"沙沙"刺耳感），再叠 190Hz 鼓腔 */
    var snareNoise = new Float32Array(Math.floor(0.24 * SR));
    for (var sn = 0; sn < snareNoise.length; sn++) snareNoise[sn] = Math.random() * 2 - 1;
    lowpass(snareNoise, 4800);
    function snare(amp) {
      return function (t, i) {
        var body = Math.sin(6.2831853 * 190 * t) * Math.exp(-t * 28) * 0.42;
        var nz = (snareNoise[i] || 0) * Math.exp(-t * 16) * 0.62;
        return (body + nz) * amp;
      };
    }
    /* 闭镲：极短噪声，低通到 8k，清脆但不刺 */
    var hatNoise = new Float32Array(Math.floor(0.07 * SR));
    for (var hn = 0; hn < hatNoise.length; hn++) hatNoise[hn] = Math.random() * 2 - 1;
    lowpass(hatNoise, 8000);
    function hat(amp) {
      return function (t, i) { return (hatNoise[i] || 0) * Math.exp(-t * 80) * amp; };
    }

    for (var bar_i = 0; bar_i * bar < DUR; bar_i++) {
      var b0 = bar_i * bar;
      addAt(b, Math.floor(b0 * SR), Math.floor(0.48 * SR), kick(0.95));
      addAt(b, Math.floor((b0 + beat * 2) * SR), Math.floor(0.48 * SR), kick(0.82));
      for (k = 1; k < 4; k += 2) {
        addAt(b, Math.floor((b0 + beat * k) * SR), Math.floor(0.24 * SR), snare(0.66));
      }
      for (k = 0; k < 8; k++) {
        addAt(b, Math.floor((b0 + beat * 0.5 * k) * SR), Math.floor(0.07 * SR), hat(0.15));
      }
    }
    return normalize(b, 0.9);
  }

  /* 2) 大提琴《天鹅》：真实录音（懒加载）。
     3) 诗歌朗读《High Flight》：真实录音（懒加载）。 */

  /* 懒加载真实录音：合成段即时可用，mp3 段 fetch demo/ 下的文件。
     任一 mp3 加载失败不影响其余段（比如极端网络环境，至少鼓 loop 还能看）。 */
  var DEMO_FILES = null;
  function getDemoFiles(cb) {
    if (DEMO_FILES) { cb(DEMO_FILES); return; }
    var files = [
      { name: '01-drum-loop-100bpm.wav', bytes: toWav(drumLoop()) },
      { name: '02-the-swan-cello.mp3',   bytes: null },
      { name: '03-poem-high-flight.mp3', bytes: null }
    ];
    var paths = ['demo/swan-cello.mp3', 'demo/high-flight-poem.mp3'];
    var pending = paths.length;
    paths.forEach(function (p, i) {
      fetch(p)
        .then(function (res) { if (!res.ok) throw new Error(res.status); return res.arrayBuffer(); })
        .then(function (ab) { files[i + 1].bytes = new Uint8Array(ab); })
        .catch(function () { track('demo_asset_fail', { index: i }); })
        .then(function () { if (--pending === 0) { DEMO_FILES = files; cb(files); } });
    });
  }

  /* ---------- 伪造 FileSystemHandle，喂给工具自己的加载流程 ---------- */
  function fakeFileHandle(name, bytes) {
    var mime = /\.mp3$/i.test(name) ? 'audio/mpeg' : 'audio/wav';
    return {
      kind: 'file',
      name: name,
      getFile: function () {
        return Promise.resolve(new File([bytes], name, { type: mime }));
      }
    };
  }
  function fakeDirHandle(name, files) {
    return {
      kind: 'directory',
      name: name,
      entries: function () {
        var i = 0;
        var it = {
          next: function () {
            if (i < files.length) { var f = files[i++]; return { value: [f.name, f], done: false }; }
            return { value: undefined, done: true };
          }
        };
        it[Symbol.iterator] = function () { return it; };
        return it;
      }
    };
  }

  function runDemo() {
    var btn = document.getElementById('pickFolderBtn');
    if (!btn) return;
    track('demo_click', { lang: curLang() });
    getDemoFiles(function (fs) {
      var files = fs.filter(function (f) { return f.bytes; })
                    .map(function (f) { return fakeFileHandle(f.name, f.bytes); });
      var dir = fakeDirHandle('WaveAtlas demo audio', files);
      var orig = window.showDirectoryPicker;
      var hadOwn = Object.prototype.hasOwnProperty.call(window, 'showDirectoryPicker');

      window.showDirectoryPicker = function () { return Promise.resolve(dir); };
      try { btn.click(); } catch (e) {}
      watchLoad('demo');

      setTimeout(function () {
        if (hadOwn && orig) window.showDirectoryPicker = orig;
        else { try { delete window.showDirectoryPicker; } catch (e) { window.showDirectoryPicker = undefined; } }
      }, 400);
    });
  }

  /* ---------- 兼容横幅 ---------- */
  var ACK_KEY = 'wa.compatAck.v1';
  function canPickFolder() { return typeof window.showDirectoryPicker === 'function'; }
  function isHandheld() { return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent); }

  function syncCompatBar() {
    var bar = document.querySelector('.compat-bar');
    if (!bar) return;
    var acked = false;
    try { acked = localStorage.getItem(ACK_KEY) === '1'; } catch (e) {}
    var need = (!canPickFolder() || isHandheld()) && !acked;
    document.body.classList.toggle('has-compat', need);
    bar.querySelectorAll('[data-cb-i18n]').forEach(function (el) {
      var k = el.getAttribute('data-cb-i18n');
      var v = t2(k);
      if (!v) return;
      el.textContent = v;
      if (el.tagName === 'A') el.title = v;
    });
  }

  /* ---------- 装配 ---------- */
  function mountDemoButton() {
    var toolbar = document.querySelector('.sidebar-toolbar');
    if (!toolbar || document.getElementById('demoBtn')) return;
    var b = document.createElement('button');
    b.id = 'demoBtn';
    b.className = 'demo-btn';
    b.type = 'button';
    b.addEventListener('click', runDemo);
    toolbar.appendChild(b);
  }
  function syncDemoLabel() {
    var b = document.getElementById('demoBtn');
    if (b) { b.textContent = t2('demo.btn'); b.title = t2('demo.btn'); }
  }

  function boot() {
    mountDemoButton();
    syncDemoLabel();
    syncCompatBar();
    hookRealPicker();
    var close = document.querySelector('.compat-bar .cb-close');
    if (close) close.addEventListener('click', function () {
      try { localStorage.setItem(ACK_KEY, '1'); } catch (e) {}
      document.body.classList.remove('has-compat');
    });
    var sel = document.getElementById('langSelect');
    if (sel) sel.addEventListener('change', function () { syncDemoLabel(); syncCompatBar(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
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
    doc = doc.replace("</head>", ANALYTICS + SITE_BAR_STYLE + EXTRA_STYLE + "</head>", 1)

    # 2. 注入站点条 + 兼容横幅（在 <body> 后、工具 .app 之前）
    if "<body>" not in doc:
        raise SystemExit("错误：工具源码找不到 <body>")
    doc = doc.replace("<body>", "<body>" + SITE_BAR_HTML + COMPAT_BAR_HTML, 1)

    # 3. 注入广告预留位 + 示例音频/兼容检测脚本 + 站点条多语言同步脚本（工具脚本执行完之后）
    if "</body>" not in doc:
        raise SystemExit("错误：工具源码找不到 </body>")
    doc = doc.replace("</body>", AD_SLOT + COMPAT_DEMO_JS + SITE_BAR_I18N_JS + "</body>", 1)

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
        # P0：兼容横幅 + 示例音频
        "兼容横幅": doc.count('class="compat-bar"'),
        "兼容横幅七语": doc.count("'cb.msg':"),
        "示例音频按钮": doc.count("'demoBtn'"),
        "示例音频七语": doc.count("'demo.btn':"),
        "示例音频合成": doc.count("function toWav(samples)"),
        "句柄注入": doc.count("window.showDirectoryPicker = function ()"),
        "示例文件名": doc.count("01-drum-loop-100bpm.wav") + doc.count("02-the-swan-cello.mp3") + doc.count("03-poem-high-flight.mp3"),
        "mp3懒加载": doc.count("demo/swan-cello.mp3") + doc.count("demo/high-flight-poem.mp3"),
        # GA4 埋点
        "GA4 脚本": doc.count("googletagmanager.com/gtag/js?id=G-RTZL87DHM4"),
        "GA4 配置": doc.count("'config', 'G-RTZL87DHM4'"),
        "事件发送": doc.count("function track(name, params)"),
        "加载成功事件": doc.count("'files_loaded'"),
        "真实选择埋点": doc.count("__waPickerHooked"),
    }
    print(f"[OK] {OUT.relative_to(ROOT)}  {len(doc.encode('utf-8'))} 字节")
    for name, n in checks.items():
        flag = "OK" if n >= 1 else "缺失!"
        print(f"  [{flag}] {name}: {n}")


if __name__ == "__main__":
    main()
