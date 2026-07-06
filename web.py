#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""热点雷达 Web 服务 - 静态文件版"""

import http.server
import json
import sys
import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# 加入当前目录到path，方便导入 collectors
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collectors

PORT = 8084
INDUSTRY_KEYWORDS = {
    "宠物": ["猫", "狗", "宠物", "铲屎", "喵", "汪", "兽医", "养宠", "猫粮", "狗粮"],
    "民生": ["医疗", "教育", "房价", "就业", "养老", "社保", "医保", "民生", "物价"],
    "科技": ["AI", "人工智能", "芯片", "手机", "电动汽车", "新能源", "科技", "华为", "苹果"],
    "财经": ["股市", "A股", "美股", "基金", "理财", "比特币", "黄金", "财经", "财报"],
    "娱乐": ["明星", "电影", "综艺", "网红", "直播", "娱乐", "电视剧", "音乐"],
    "健康": ["健康", "养生", "减肥", "健身", "疾病", "疫苗", "药品", "医疗"],
}

# ──────────────────────────────────────────────
#  行业分类
# ──────────────────────────────────────────────
def classify_items(all_items):
    result = {}
    for ind, kws in INDUSTRY_KEYWORDS.items():
        hit = [it for it in all_items if any(kw in it.get("title", "") for kw in kws)]
        if hit:
            result[ind] = hit
    return result


# ──────────────────────────────────────────────
#  生成 MD 文本
# ──────────────────────────────────────────────
def generate_md(items, industry="全部"):
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# 热点日报 - " + today)
    lines.append("")
    lines.append("> 自动生成时间：" + now)
    lines.append("> 筛选行业：" + industry)
    lines.append("> 热点总数：" + str(len(items)))
    lines.append("")
    lines.append("---")
    lines.append("")

    platform_items = {}
    for it in items:
        plat = it.get("platform", "未知")
        if plat not in platform_items:
            platform_items[plat] = []
        platform_items[plat].append(it)

    for plat, pitems in platform_items.items():
        lines.append("## " + plat + "（" + str(len(pitems)) + " 条）")
        lines.append("")
        for i, it in enumerate(pitems, 1):
            title = it.get("title", "")
            url = it.get("url", "")
            hot = it.get("hot", "")
            tag = it.get("tag", "")
            if url:
                line = str(i) + ". [" + title + "](" + url + ")"
            else:
                line = str(i) + ". " + title
            if hot:
                line += " 🔥" + hot
            if tag:
                line += " `" + tag + "`"
            lines.append(line)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*由热点雷达自动生成*")
    return "\n".join(lines)


# ──────────────────────────────────────────────
#  Web 请求处理器
# ──────────────────────────────────────────────
class WebHandler(http.server.SimpleHTTPRequestHandler):
    """自定义请求处理器：静态文件 + API 路由"""

    def log_message(self, format, *args):
        """静默日志（避免控制台乱码）"""
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/hot-radar.html" or path == "/index.html":
            self.send_file("hot-radar.html", "text/html; charset=utf-8")
        elif path == "/api/collect":
            self.api_collect()
        else:
            # 尝试服务静态文件
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/prompt":
            self.api_prompt()
        elif path == "/api/export":
            self.api_export()
        else:
            self.send_error(404)

    # ───────── 辅助 ─────────
    def send_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    def send_json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ───────── API ─────────
    def api_collect(self):
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

        # 去重
        seen = set()
        unique_items = []
        for it in all_items:
            key = it["title"]
            if key not in seen:
                seen.add(key)
                unique_items.append(it)

        logs.append("总计: " + str(len(unique_items)) + " 条（去重后）")
        self.send_json({"items": unique_items, "logs": logs})

    def api_prompt(self):
        try:
            body = self._read_body()
            if not body:
                self.send_json({"prompts": []})
                return
            data = json.loads(body)
            # 修复拼写：industries -> industries
            industries = data.get("industries", data.get("industries", []))
            items = data.get("items", [])
            industry_items = classify_items(items)

            prompts = []
            for ind in industries:
                hot_titles = [it["title"] for it in industry_items.get(ind, [])]
                if not hot_titles:
                    hot_titles = [it["title"] for it in items[:10]]
                if not hot_titles:
                    continue
                prompt = build_prompt_text(ind, hot_titles)
                prompts.append({"industry": ind, "prompt": prompt})

            self.send_json({"prompts": prompts})
        except Exception as e:
            print("[ERROR] api_prompt: " + str(e))
            self.send_json({"prompts": [], "error": str(e)})

    def api_export(self):
        try:
            body = self._read_body()
            if not body:
                self.send_json({"md": "", "error": "空请求"})
                return
            data = json.loads(body)
            items = data.get("items", [])
            industry = data.get("industry", "全部")
            md_content = generate_md(items, industry)
            self.send_json({"md": md_content})
        except Exception as e:
            print("[ERROR] api_export: " + str(e))
            self.send_json({"md": "", "error": str(e)})

    def _read_body(self):
        """安全读取请求体，兼容有无 Content-Length"""
        length = self.headers.get("Content-Length")
        if length:
            return self.rfile.read(int(length))
        # 无长度时读取到结束
        return self.rfile.read()


# ──────────────────────────────────────────────
#  构建 AI 提示词文本
# ──────────────────────────────────────────────
def build_prompt_text(industry, hot_titles):
    lines = []
    lines.append("你是资深内容策划专家。以下是今日与「" + industry + "」相关的网络热点：")
    lines.append("")
    for i, t in enumerate(hot_titles[:12], 1):
        lines.append(str(i) + ". " + t)
    lines.append("")
    lines.append("请基于以上热点趋势，为「" + industry + "」垂直领域创作 5 个有传播力的创意话题。")
    lines.append("")
    lines.append("要求：")
    lines.append("1. 每个话题要结合热点趋势，但有独特切入角度")
    lines.append("2. 话题要有话题性、争议性或实用性，适合社交媒体传播")
    lines.append("3. 格式：### 1. 话题标题 / 内容方向：一句话说明")
    lines.append("")
    lines.append("注意：只输出这5个创意话题，不要输出其他任何内容。")
    return "\n".join(lines)


# ──────────────────────────────────────────────
#  启动服务
# ──────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(("0.0.0.0", PORT), WebHandler)
    print("热点雷达 Web 服务已启动")
    print("访问地址：http://localhost:" + str(PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("服务已停止")
