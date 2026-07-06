#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热点雷达 - 网络热点采集 & AI创意工具 (Web版)
浏览器访问 http://localhost:8080 使用
"""

import json
import sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collectors

PORT = 8080

INDUSTRY_KEYWORDS = {
    "宠物": ["猫", "狗", "宠物", "铲屎", "喵", "汪", "兽医", "养宠", "宠物医院", "宠物食品"],
    "民生": ["医疗", "教育", "房价", "就业", "养老", "社保", "医保", "低保", "民生", "物价", "消费", "收入"],
    "科技": ["AI", "人工智能", "芯片", "手机", "电动汽车", "新能源", "5G", "量子", "科技", "算力", "自动驾驶"],
    "财经": ["股市", "A股", "美股", "基金", "理财", "比特币", "黄金", "油价", "通胀", "财报", "IPO", "上市"],
    "娱乐": ["明星", "电影", "电视剧", "综艺", "票房", "演唱会", "网红", "直播", "娱乐圈", "塌房"],
    "健康": ["健康", "养生", "减肥", "健身", "疾病", "疫苗", "药品", "医疗", "饮食", "睡眠"],
}

PLATFORM_COLORS = {
    "今日头条": "#ff4444",
    "百度热搜": "#3385ff",
    "抖音热榜": "#010101",
    "微博热搜": "#ff8200",
    "知乎热榜": "#0066ff",
    "小红书": "#ff2442",
}

INDUSTRY_EMOJI = {
    "全部": "🌐", "宠物": "🐾", "民生": "🏘️",
    "科技": "💻", "财经": "💰", "娱乐": "🎬", "健康": "🏥",
}


def classify_items(all_items):
    industry_items = {k: [] for k in INDUSTRY_KEYWORDS}
    for item in all_items:
        title = item.get("title", "")
        for ind, kws in INDUSTRY_KEYWORDS.items():
            if any(kw in title for kw in kws):
                industry_items[ind].append(item)
                break
    return industry_items


def build_prompt(industry, industry_items, all_items):
    items = industry_items.get(industry, [])
    hot_titles = [it["title"] for it in items]
    if len(hot_titles) < 5:
        seen = set(hot_titles)
        for it in all_items[:15]:
            if it["title"] not in seen:
                hot_titles.append(it["title"])
                seen.add(it["title"])
            if len(hot_titles) >= 12:
                break
    if not hot_titles:
        return ""
    industry_part = "\n".join("- " + t for t in hot_titles)
    all_part = "\n".join("- " + it["title"] for it in all_items[:8])
    return (
        "你是资深内容策划专家。请基于今日网络热点，"
        "为「" + industry + "」垂直领域创作 5 个有传播力的创意话题。\n\n"
        "## 今日与「" + industry + "」直接相关的热点：\n" + industry_part + "\n\n"
        "## 今日全平台热点趋势（供参考）：\n" + all_part + "\n\n"
        "要求：\n"
        "1. 每个话题要结合热点趋势，但有独特切入角度\n"
        "2. 话题要有话题性、争议性或实用性，适合社交媒体传播\n"
        "3. 格式：### 序号. 话题标题（随后一行 > 内容方向：一句话说明）\n"
        "4. 共输出5个\n\n"
        "只输出这5个创意话题，不要输出其他任何内容。"
    )


def run_collect():
    all_items = []
    logs = []
    for name, func in [
        ("今日头条", collectors.collect_toutiao),
        ("百度热搜", collectors.collect_baidu),
        ("抖音热榜", collectors.collect_douyin),
        ("微博热搜", collectors.collect_weibo),
        ("知乎热榜", collectors.collect_zhihu),
        ("小红书", collectors.collect_xiaohongshu),
    ]:
        try:
            items = func()
            logs.append("[" + name + "] 采集 " + str(len(items)) + " 条")
            all_items.extend(items)
        except Exception as e:
            logs.append("[" + name + "] 失败: " + str(e))
    seen = set()
    unique_items = []
    for it in all_items:
        key = it["title"]
        if key not in seen:
            seen.add(key)
            unique_items.append(it)
    logs.append("总计: " + str(len(unique_items)) + " 条（去重后）")
    return unique_items, logs


HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>热点雷达 - 网络热点采集 & AI创意工具</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#f0f2f5; --card:#fff; --text:#1a1a2e; --text2:#555;
  --accent:#4361ee; --accent2:#3a0ca3; --green:#06d6a0;
  --orange:#f8961e; --red:#ef233c; --gray:#adb5bd;
  --radius:16px; --shadow:0 2px 12px rgba(0,0,0,0.06);
}
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'Inter',-apple-system,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }

.header {
  background:linear-gradient(135deg,#1a1a2e 0%,#16213e 40%,#0f3460 100%);
  color:#fff; padding:32px 0 28px; position:relative; overflow:hidden;
}
.header::before {
  content:''; position:absolute; top:-60%; right:-10%;
  width:500px; height:500px; border-radius:50%;
  background:radial-gradient(circle,rgba(67,97,238,0.25),transparent 70%);
  pointer-events:none;
}
.header-inner { max-width:1100px; margin:0 auto; padding:0 24px; position:relative; z-index:1; }
.header h1 { font-size:28px; font-weight:800; letter-spacing:-0.5px; }
.header h1 span { color:#4cc9f0; }
.header p { color:rgba(255,255,255,0.65); font-size:14px; margin-top:6px; }

.container { max-width:1100px; margin:0 auto; padding:24px; }

.stats-row {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:14px; margin-top:-36px; position:relative; z-index:2;
}
.stat-card {
  background:var(--card); border-radius:var(--radius); padding:20px 18px;
  box-shadow:var(--shadow); text-align:center; transition:transform 0.2s;
}
.stat-card:hover { transform:translateY(-3px); }
.stat-icon { font-size:28px; margin-bottom:8px; }
.stat-num { font-size:32px; font-weight:800; color:var(--accent); line-height:1; }
.stat-label { font-size:12px; color:var(--gray); margin-top:4px; text-transform:uppercase; letter-spacing:0.5px; }

.card { background:var(--card); border-radius:var(--radius); padding:24px; box-shadow:var(--shadow); margin-top:20px; }
.card-title { font-size:16px; font-weight:700; margin-bottom:16px; display:flex; align-items:center; gap:8px; }

.btn {
  display:inline-flex; align-items:center; gap:6px;
  padding:10px 22px; border:none; border-radius:10px;
  font-size:14px; font-weight:600; cursor:pointer; transition:all 0.2s; font-family:inherit;
}
.btn-primary { background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#fff; }
.btn-primary:hover { opacity:0.92; transform:translateY(-1px); box-shadow:0 4px 14px rgba(67,97,238,0.35); }
.btn-primary:disabled { opacity:0.6; cursor:not-allowed; transform:none; box-shadow:none; }
.btn-outline { background:transparent; color:var(--accent); border:1.5px solid var(--accent); }
.btn-outline:hover { background:var(--accent); color:#fff; }
.btn-ghost { background:#f0f2f5; color:var(--text2); }
.btn-ghost:hover { background:#e2e6ea; }

.tag-row { display:flex; flex-wrap:wrap; gap:8px; }
.tag {
  padding:7px 16px; border-radius:20px; border:1.5px solid #e0e0e0;
  background:#fff; cursor:pointer; font-size:13px; font-weight:500;
  transition:all 0.2s; user-select:none; display:inline-flex; align-items:center; gap:4px;
}
.tag:hover { border-color:var(--accent); color:var(--accent); }
.tag.active { background:var(--accent); color:#fff; border-color:var(--accent); }

.hot-list-wrap { max-height:520px; overflow-y:auto; padding-right:4px; }
.hot-list-wrap::-webkit-scrollbar { width:5px; }
.hot-list-wrap::-webkit-scrollbar-thumb { background:#d0d0d0; border-radius:10px; }
.hot-item { display:flex; align-items:center; gap:12px; padding:12px 14px; border-radius:10px; transition:background 0.15s; }
.hot-item:hover { background:#f7f8fc; }
.rank { width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; flex-shrink:0; }
.rank.top1 { background:linear-gradient(135deg,#ffd700,#ffaa00); color:#fff; }
.rank.top2 { background:linear-gradient(135deg,#c0c0c0,#a0a0a0); color:#fff; }
.rank.top3 { background:linear-gradient(135deg,#cd7f32,#b06500); color:#fff; }
.rank.normal { background:#f0f2f5; color:#999; }
.hot-title { flex:1; font-size:14px; line-height:1.5; }
.hot-title a { color:var(--text); text-decoration:none; }
.hot-title a:hover { color:var(--accent); }
.hot-meta { display:flex; align-items:center; gap:8px; flex-shrink:0; }
.hot-hot { font-size:11px; color:var(--orange); font-weight:600; min-width:50px; text-align:right; }

.platform-bar-wrap { margin:16px 0; }
.platform-bar-label { display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px; }
.platform-bar { height:8px; border-radius:4px; background:#eee; overflow:hidden; }
.platform-bar-fill { height:100%; border-radius:4px; transition:width 0.6s ease; }

.prompt-box {
  background:#f8f9fc; border:1px solid #e8eaf0; border-radius:12px;
  padding:18px; font-size:13px; line-height:1.7; white-space:pre-wrap;
  max-height:320px; overflow-y:auto; position:relative;
}
.prompt-box::before {
  content:'AI PROMPT'; position:absolute; top:8px; right:12px;
  font-size:9px; font-weight:700; color:var(--accent); opacity:0.35; letter-spacing:1px;
}

.toast {
  position:fixed; bottom:30px; left:50%; transform:translateX(-50%) translateY(80px);
  background:#1a1a2e; color:#fff; padding:12px 24px; border-radius:10px;
  font-size:14px; font-weight:500; z-index:999;
  opacity:0; transition:all 0.35s cubic-bezier(.4,0,.2,1);
  pointer-events:none; display:flex; align-items:center; gap:8px;
}
.toast.show { opacity:1; transform:translateX(-50%) translateY(0); }

.status-bar {
  display:none; padding:14px 18px; border-radius:12px; font-size:13px;
  margin-top:14px; align-items:center; gap:10px;
}
.status-bar.show { display:flex; }
.status-bar.loading { background:#eef2ff; color:var(--accent); }
.status-bar.success { background:#ecfdf5; color:#059669; }
.status-bar.error { background:#fef2f2; color:#dc2626; }
.spinner {
  width:16px; height:16px; border:2px solid rgba(67,97,238,0.2);
  border-top-color:var(--accent); border-radius:50%;
  animation:spin 0.7s linear infinite; flex-shrink:0;
}
@keyframes spin { to { transform:rotate(360deg); } }
@keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }

.two-col { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
@media(max-width:700px) { .two-col { grid-template-columns:1fr; } }

.empty-state { text-align:center; padding:48px 20px; color:var(--gray); }
.empty-state .icon { font-size:48px; margin-bottom:12px; }

.search-box {
  width:100%; padding:10px 14px 10px 38px; border:1.5px solid #e0e0e0;
  border-radius:10px; font-size:13px; outline:none; transition:border-color 0.2s;
  background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23999' viewBox='0 0 16 16'%3E%3Cpath d='M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85zm-5.44.22a5 5 0 1 1 0-10 5 5 0 0 1 0 10z'/%3E%3C/svg%3E") 12px center no-repeat;
  font-family:inherit;
}
.search-box:focus { border-color:var(--accent); }
.search-wrap { position:relative; margin-bottom:14px; }

.progress-dots { display:inline-flex; gap:4px; }
.progress-dots span {
  width:6px; height:6px; border-radius:50%; background:var(--accent); opacity:0.3;
  animation:pulse 1.2s infinite;
}
.progress-dots span:nth-child(2) { animation-delay:0.2s; }
.progress-dots span:nth-child(3) { animation-delay:0.4s; }
@keyframes pulse { 0%,100% { opacity:0.3; } 50% { opacity:1; } }
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <h1>热点<span>雷达</span></h1>
    <p>多平台热点采集 · 行业智能分类 · AI 创意话题生成</p>
  </div>
</div>

<div class="container">
  <div class="stats-row" id="statsRow">
    <div class="stat-card">
      <div class="stat-icon">📡</div>
      <div class="stat-num" id="statTotal">0</div>
      <div class="stat-label">热点总数</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">📱</div>
      <div class="stat-num" id="statPlatform">0</div>
      <div class="stat-label">覆盖平台</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">🏷️</div>
      <div class="stat-num" id="statIndustry">0</div>
      <div class="stat-label">命中行业</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">⏰</div>
      <div class="stat-num" style="font-size:18px;" id="statTime">--</div>
      <div class="stat-label">更新时间</div>
    </div>
  </div>

  <div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
      <div>
        <button class="btn btn-primary" id="btnCollect">⚡ 采集今日热点</button>
        <span style="margin-left:14px; font-size:13px; color:#999;" id="lastUpdate"></span>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-ghost" id="btnExport" style="display:none;">📥 导出 MD</button>
      </div>
    </div>
    <div class="status-bar" id="statusBar">
      <div class="spinner" id="statusSpinner" style="display:none;"></div>
      <span id="statusText"></span>
    </div>
    <div id="platformBreakdown" style="margin-top:16px; display:none;">
      <div style="font-size:12px; color:#999; margin-bottom:10px; font-weight:600;">平台分布</div>
      <div id="platformBars"></div>
    </div>
  </div>

  <div class="two-col">
    <div>
      <div class="card">
        <div class="card-title">📋 热点列表</div>
        <div class="search-wrap">
          <input class="search-box" id="searchBox" placeholder="搜索热点关键词..." disabled>
        </div>
        <div class="tag-row" id="industryTags" style="margin-bottom:14px;">
          <div class="tag active" data-ind="全部">🌐 全部</div>
          <div class="tag" data-ind="宠物">🐾 宠物</div>
          <div class="tag" data-ind="民生">🏘️ 民生</div>
          <div class="tag" data-ind="科技">💻 科技</div>
          <div class="tag" data-ind="财经">💰 财经</div>
          <div class="tag" data-ind="娱乐">🎬 娱乐</div>
          <div class="tag" data-ind="健康">🏥 健康</div>
        </div>
        <div class="hot-list-wrap" id="hotList">
          <div class="empty-state">
            <div class="icon">📡</div>
            <div>点击「采集今日热点」开始</div>
          </div>
        </div>
      </div>
    </div>

    <div>
      <div class="card" id="promptCard" style="display:none;">
        <div class="card-title">✨ AI 创意话题</div>
        <p style="font-size:13px; color:#777; margin-bottom:16px;">
          复制提示词 → 粘贴到 <a href="https://chat.deepseek.com" target="_blank" style="color:var(--accent);">DeepSeek 网页版</a> → 获取创意话题
        </p>
        <div id="promptContent"></div>
        <button class="btn btn-outline" id="btnGenPrompt" style="margin-top:14px; width:100%; justify-content:center;">
          ✨ 生成 AI 提示词
        </button>
      </div>
      <div class="card" id="promptPlaceholder" style="display:flex; align-items:center; justify-content:center; min-height:300px;">
        <div style="text-align:center; color:#bbb;">
          <div style="font-size:48px; margin-bottom:12px;">✨</div>
          <div style="font-size:14px;">采集热点后，可生成 AI 创意提示词</div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
var allItems = [];
var currentIndustry = "全部";
var PROMPTS_DATA = {};

function toast(msg) {
  var el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(function(){ el.classList.remove("show"); }, 2200);
}

/* Industry tags */
document.querySelectorAll("#industryTags .tag").forEach(function(tag) {
  tag.addEventListener("click", function() {
    document.querySelectorAll("#industryTags .tag").forEach(function(t){ t.classList.remove("active"); });
    tag.classList.add("active");
    currentIndustry = tag.dataset.ind;
    renderList();
    if (allItems.length) document.getElementById("btnGenPrompt").style.display = "";
  });
});

/* Collect */
document.getElementById("btnCollect").addEventListener("click", function() {
  var btn = document.getElementById("btnCollect");
  var sb = document.getElementById("statusBar");
  var sp = document.getElementById("statusSpinner");
  btn.disabled = true;
  btn.textContent = "⏳ 采集中...";
  sb.className = "status-bar show loading";
  sp.style.display = "";
  document.getElementById("statusText").textContent = "正在从各平台采集热点...";
  document.getElementById("hotList").innerHTML = '<div class="empty-state"><div class="icon"><div class="progress-dots"><span></span><span></span><span></span></div></div><div>采集中，请稍候</div></div>';

  fetch("/api/collect").then(function(r){ return r.json(); }).then(function(data) {
    allItems = data.items;
    renderStats(data);
    renderPlatformBars(data);
    renderList();
    document.getElementById("searchBox").disabled = false;
    document.getElementById("btnGenPrompt").style.display = "";
    document.getElementById("btnExport").style.display = "";
    document.getElementById("promptCard").style.display = "none";
    document.getElementById("promptPlaceholder").style.display = "flex";
    sb.className = "status-bar show success";
    sp.style.display = "none";
    document.getElementById("statusText").textContent = "✅ 采集完成！共 " + allItems.length + " 条热点";
    toast("采集完成，共 " + allItems.length + " 条");
  }).catch(function(e) {
    sb.className = "status-bar show error";
    sp.style.display = "none";
    document.getElementById("statusText").textContent = "采集失败：" + e.message;
    toast("采集失败");
  }).finally(function() {
    btn.disabled = false;
    btn.textContent = "⚡ 重新采集";
  });
});

/* Stats */
function renderStats(data) {
  var items = data.items;
  document.getElementById("statTotal").textContent = items.length;
  var platforms = new Set(items.map(function(it){ return it.platform; }));
  document.getElementById("statPlatform").textContent = platforms.size;
  var indHits = new Set();
  var kws = {"宠物":["猫","狗","宠物"],"民生":["医疗","教育","房价"],"科技":["AI","芯片","手机"],"财经":["股市","基金","A股"],"娱乐":["明星","电影","综艺"],"健康":["健康","养生","减肥"]};
  items.forEach(function(it) {
    Object.entries(kws).forEach(function(entry) {
      var ind = entry[0], ws = entry[1];
      if (ws.some(function(w){ return it.title.includes(w); })) { indHits.add(ind); }
    });
  });
  document.getElementById("statIndustry").textContent = indHits.size;
  var now = new Date();
  document.getElementById("statTime").textContent =
    (now.getHours()+"").padStart(2,"0") + ":" + (now.getMinutes()+"").padStart(2,"0");
  document.getElementById("lastUpdate").textContent = "刚刚更新";
}

/* Platform bars */
function renderPlatformBars(data) {
  var counts = {};
  data.items.forEach(function(it) { counts[it.platform] = (counts[it.platform]||0) + 1; });
  var total = data.items.length || 1;
  var colors = {"今日头条":"#ff4444","百度热搜":"#3385ff","抖音热榜":"#010101","微博热搜":"#ff8200","知乎热榜":"#0066ff","小红书":"#ff2442"};
  var html = "";
  Object.entries(counts).forEach(function(entry) {
    var plat = entry[0], cnt = entry[1];
    html += '<div class="platform-bar-wrap"><div class="platform-bar-label"><span>' + escHtml(plat) + '</span><span>' + cnt + ' 条</span></div><div class="platform-bar"><div class="platform-bar-fill" style="width:' + Math.round(cnt/total*100) + '%;background:' + (colors[plat]||"#4361ee") + '"></div></div></div>';
  });
  document.getElementById("platformBars").innerHTML = html;
  document.getElementById("platformBreakdown").style.display = "";
}

/* Render list */
function renderList() {
  var items = allItems.slice();
  if (currentIndustry !== "全部") {
    var kwsMap = {"宠物":["猫","狗","宠物","铲屎","喵","汪","兽医","养宠"],"民生":["医疗","教育","房价","就业","养老","社保","医保"],"科技":["AI","人工智能","芯片","手机","电动汽车","新能源","科技"],"财经":["股市","A股","美股","基金","理财","比特币","黄金"],"娱乐":["明星","电影","综艺","网红","直播","娱乐"],"健康":["健康","养生","减肥","健身","疾病","疫苗","药品"]};
    var ws = kwsMap[currentIndustry] || [];
    items = allItems.filter(function(it) { return ws.some(function(w){ return it.title.includes(w); }); });
  }
  var q = document.getElementById("searchBox").value.trim().toLowerCase();
  if (q) items = items.filter(function(it) { return it.title.toLowerCase().includes(q); });

  var wrap = document.getElementById("hotList");
  if (!items.length) {
    wrap.innerHTML = '<div class="empty-state"><div class="icon">🔍</div><div>暂无匹配热点</div></div>';
    return;
  }

  var pColors = {"今日头条":"#ff4444","百度热搜":"#3385ff","抖音热榜":"#010101","微博热搜":"#ff8200","知乎热榜":"#0066ff","小红书":"#ff2442"};
  var html = "";
  items.forEach(function(it, i) {
    var rCls = i===0?"top1":i===1?"top2":i===2?"top3":"normal";
    var pColor = pColors[it.platform] || "#999";
    var titleHtml = it.url ? '<a href="' + escHtml(it.url) + '" target="_blank">' + escHtml(it.title) + '</a>' : escHtml(it.title);
    html += '<div class="hot-item" style="animation:fadeUp 0.3s ' + (i*0.03) + 's both"><div class="rank ' + rCls + '">' + (i+1) + '</div><div class="hot-title">' + titleHtml + '</div><div class="hot-meta"><span class="platform-pill" style="background:' + pColor + '15;color:' + pColor + ';padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">' + escHtml(it.platform) + '</span><span class="hot-hot">' + escHtml(it.hot||"") + '</span></div></div>';
  });
  wrap.innerHTML = html;
}

/* Search */
document.getElementById("searchBox").addEventListener("input", renderList);

/* Generate prompt */
document.getElementById("btnGenPrompt").addEventListener("click", function() {
  if (!allItems.length) { toast("请先采集热点"); return; }
  var sb = document.getElementById("statusBar");
  sb.className = "status-bar show loading";
  document.getElementById("statusSpinner").style.display = "";
  document.getElementById("statusText").textContent = "正在生成 AI 提示词...";

  var industries = currentIndustry === "全部" ? ["宠物","民生","科技","财经","娱乐","健康"] : [currentIndustry];

  fetch("/api/prompt", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({industries: industries, items: allItems})
  }).then(function(r){ return r.json(); }).then(function(data) {
    renderPrompts(data.prompts);
    sb.className = "status-bar show success";
    document.getElementById("statusSpinner").style.display = "none";
    document.getElementById("statusText").textContent = "✅ 已生成 " + industries.length + " 个行业的 AI 提示词";
    toast("AI 提示词已生成");
    document.getElementById("promptCard").scrollIntoView({behavior:"smooth", block:"start"});
  }).catch(function(e) {
    sb.className = "status-bar show error";
    document.getElementById("statusSpinner").style.display = "none";
    document.getElementById("statusText").textContent = "生成失败：" + e.message;
  });
});

function renderPrompts(prompts) {
  var card = document.getElementById("promptCard");
  var placeholder = document.getElementById("promptPlaceholder");
  card.style.display = "block";
  placeholder.style.display = "none";
  PROMPTS_DATA = {};
  var html = "";
  prompts.forEach(function(p, idx) {
    PROMPTS_DATA[idx] = p.prompt;
    html += '<div style="margin-bottom:20px;"><div style="font-weight:700;font-size:14px;margin-bottom:8px;color:var(--accent);">' + escHtml(p.industry) + ' 提示词</div><div class="prompt-box">' + escHtml(p.prompt) + '</div><button class="btn btn-outline copy-btn" style="margin-top:8px;font-size:12px;padding:7px 16px;" onclick="copyPrompt(' + idx + ')">📋 复制提示词</button></div>';
  });
  document.getElementById("promptContent").innerHTML = html;
}

function copyPrompt(idx) {
  var text = PROMPTS_DATA[idx];
  if (!text) return;
  navigator.clipboard.writeText(text).then(function() {
    var btn = event.target;
    btn.textContent = "✅ 已复制";
    setTimeout(function(){ btn.textContent = "📋 复制提示词"; }, 1800);
    toast("提示词已复制到剪贴板");
  });
}

function escHtml(s) {
  return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
</script>
</body>
</html>"""


class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.serve_index()
        elif parsed.path == "/api/collect":
            self.api_collect()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/prompt":
            self.api_prompt()
        else:
            self.send_error(404)

    def serve_index(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def api_collect(self):
        items, logs = run_collect()
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        body = json.dumps({"items": items, "logs": logs}, ensure_ascii=False)
        self.wfile.write(body.encode("utf-8"))

    def api_prompt(self):
        length = int(self.headers["Content-Length"])
        data = json.loads(self.rfile.read(length))
        industries = data.get("industries", [])
        all_items = data.get("items", [])
        industry_items = classify_items(all_items)
        prompts = []
        for ind in industries:
            p = build_prompt(ind, industry_items, all_items)
            if p:
                prompts.append({"industry": ind, "prompt": p})
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        body = json.dumps({"prompts": prompts}, ensure_ascii=False)
        self.wfile.write(body.encode("utf-8"))


def main():
    server = HTTPServer(("localhost", PORT), WebHandler)
    import codecs
    import sys
    # 避免 Windows 控制台编码问题
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")
    print("[热点雷达] 服务已启动")
    print("[热点雷达] 浏览器打开: http://localhost:" + str(PORT))
    print("[热点雷达] 按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[热点雷达] 服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
