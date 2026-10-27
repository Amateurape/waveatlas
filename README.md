# WaveAtlas Audio Browser · 观澜音频浏览器

A single-file, fully local audio waveform browser. Browse waveforms for every audio file in a folder, click anywhere to play, with automatic BPM and mood detection.

单文件、纯本地的音频波形浏览器。浏览文件夹中所有音频的波形图，点击即播，自动识别 BPM 与情绪。

## 日本語 · 日本語简介

**WaveAtlas（観瀾オーディオブラウザ）** — シングルファイルで完全ローカル動作するオーディオ波形ブラウザです。フォルダ内のすべての音源の波形を一覧表示し、波形の好きな位置をクリックすると、その場からすぐ再生。BPM とムード（9 種類）を自動判定します。

- 🌊 波形オーバービュー — 全音源を 1600 ピークの波形で表示
- 🎯 クリック再生 — 波形の任意の位置をクリックして即再生
- 🥁 BPM 自動検出 — テンポ順の並べ替えに対応
- 🎭 ムードタグ — 9 種類の自動分類
- 🌓 ライト / ダークテーマ — アクセントカラーを自由に設定
- 🌐 7 言語 UI（日本語対応）

使い方や詳細は上記の英語・中国語セクションをご覧ください。バグ報告・ご要望は [Issues](../../issues) へどうぞ。

## 한국어 · 한국어 소개

**WaveAtlas（관란 오디오 브라우저）** — 단일 파일로 완전 로컬에서 작동하는 오디오 파형 브라우저입니다. 폴더 안의 모든 오디오 파일의 파형을 한눈에 보고, 원하는 지점을 클릭해 바로 재생할 수 있습니다. BPM과 분위기(9종)도 자동으로 분석합니다.

- 🌊 파형 오버뷰 — 모든 오디오 파일을 1600 피크 파형으로 표시
- 🎯 클릭 재생 — 파형 어느 지점이든 클릭하면 그 지점부터 재생
- 🥁 BPM 자동 감지 — 템포순 정렬 지원
- 🎭 분위기 태그 — 9가지 자동 분류
- 🌓 라이트 / 다크 테마 — 강조 색상 자유 설정
- 🌐 7개 언어 UI（한국어 지원）

사용 방법과 자세한 내용은 위의 영어·중국어 섹션을 참고하세요. 버그 제보 및 기능 제안은 [Issues](../../issues)로 남겨 주세요.

## Features · 特性

- 🌊 **Waveform overview · 波形总览** — every audio file rendered as a 1600-peak waveform
- 🎯 **Click to play · 点击即播** — click anywhere on a waveform to play from that spot
- 🥁 **Automatic BPM detection · BPM 自动检测** — sortable by tempo
- 🎭 **Mood tags · 情绪分类** — 9 automatic mood labels
- ⏩ **Full playback control · 完整播放控制** — 0.5x–2x speed, ±5 s skip
- 🌓 **Light / dark themes · 亮暗双主题** — custom accent colors
- 🌐 **7 UI languages · 七种界面语言** — 简中 / 繁中 / EN / 日 / 韩 / 法 / 德

## Usage · 使用方法

1. Download `WaveAtlasAudioBrowser_v3.05.html` · 下载该 HTML 文件
2. Open it in Chrome / Edge 86+ (desktop) · 用 Chrome 或 Edge 直接打开
3. Click "📂 Select Folder" and grant access · 点击「选择文件夹」并授权

No installation. No internet needed. Nothing ever leaves your computer.

无需安装，无需联网，音频数据一个字节都不会离开你的电脑。

## 维护多语言落地页 · Maintaining the multilingual landing page

落地页五种语言各占一个独立 URL（而不是靠 JS 切换），这样每个语种才能被搜索引擎单独收录：

| 语言 | URL | 生成方式 |
|---|---|---|
| 简体中文 | `/` | `index.html`，**手工维护的母版** |
| 繁体中文 | `/zh-TW/` | 构建脚本生成 |
| 英语 | `/en/` | 构建脚本生成 |
| 日语 | `/ja/` | 构建脚本生成 |
| 韩语 | `/ko/` | 构建脚本生成 |

`en/` `ja/` `ko/` `zh-TW/` 目录下的文件**不要直接编辑**，改动会在下次构建时被覆盖：

```bash
python tools/build_lang_pages.py    # 重新生成四个语言页 + sitemap.xml（含 hreflang 互指）
python tools/check_lang_pages.py    # 交叉校验：lang / title / canonical / hreflang / 译文是否落盘 / 路径
```

改了 `index.html` 或 `i18n.js` 之后**必须重跑**，否则各语言页会停留在旧内容。
要新增语言：在 `i18n.js` 补一套完整字典 → 在 `tools/build_lang_pages.py` 的 `LANGS` 里加一行 → 重跑。

## SEO self-audit · 站点自检

检查的是**线上真实返回**（不是本地文件），覆盖五语页的 lang / title / description / canonical /
hreflang 互指 / OG / JSON-LD / h1，robots.txt 与 sitemap.xml，图标与分享卡尺寸，全站内链死链，
统计与验证代码是否还在，以及页面与图片体积。

```bash
python tools/seo_audit.py                 # 检查线上，简报写入 _local/seo-audit/
python tools/seo_audit.py --no-save       # 只打印，不落盘
python tools/seo_audit.py --out <目录>    # 简报写到指定目录
```

退出码 `0` = 无失败项；`1` = 有 FAIL，需要处理。建议每次改完页面推上去后跑一遍，外加每月一次定期体检。

## Feedback · 反馈

Found a bug or have a suggestion? Open an [Issue](../../issues).

发现问题或有功能建议？欢迎在 [Issues](../../issues) 留言。

---

© 2026 Amateurape · 「观水有术，必观其澜」
