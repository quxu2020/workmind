# -*- coding: utf-8 -*-
"""
热点采集 + 行业筛选 + AI创意话题 → 生成md
用法:
  python main.py              # 采集所有热点，按所有行业生成md（含AI创意）
  python main.py 宠物          # 只生成宠物行业的md
  python main.py 宠物 民生     # 生成多个行业
  python main.py --no-ai      # 不调用DeepSeek，只出热点md
"""
import sys
import os
import json
import time
import urllib.request
import urllib.error

# 修复 Windows 控制台编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import collectors

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def classify_by_industry(all_items, industries):
    """按行业关键词分类，返回 {行业: [items]}"""
    result = {name: [] for name in industries}
    for item in all_items:
        title = item.get("title", "")
        for name, keywords in industries.items():
            if any(kw in title for kw in keywords):
                result[name].append(item)
    # 去重（同一条可能命中多个关键词，按命中先后归到第一个匹配行业）
    seen = set()
    for name in result:
        deduped = []
        for item in result[name]:
            key = item["title"]
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        result[name] = deduped
    return result


def call_deepseek(prompt, cfg):
    """调用 DeepSeek API 生成创意话题"""
    api_key = cfg.get("deepseek_api_key", "")
    if not api_key:
        print("  [AI创意] 未配置 deepseek_api_key，跳过AI创意生成")
        return None
    base_url = cfg.get("deepseek_base_url", "https://api.deepseek.com/v1")
    model = cfg.get("deepseek_model", "deepseek-chat")
    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.95,
        "max_tokens": 2500
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [AI创意] DeepSeek API错误 {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  [AI创意] 请求失败: {e}")
        return None


def build_creative_prompt(industry, industry_hot, all_hot):
    """构建AI创意话题的提示词（区分行业直接命中 + 全平台趋势）"""
    ind_list = "\n".join(f"- {t}" for t in industry_hot) if industry_hot else "（今日暂无直接命中热点）"
    all_list = "\n".join(f"- {t}" for t in all_hot[:10])
    return f"""你是资深内容策划专家。

【今日与「{industry}」直接相关的热点】
{ind_list}

【今日全平台热点趋势（可借势参考）】
{all_list}

请综合以上信息，为「{industry}」垂直领域创作 5 个有传播力的创意话题。

要求：
1. 优先结合「{industry}」直接相关热点；若无直接命中，则从全平台趋势中找与{industry}的关联切入角度
2. 每个话题要有独特视角，不是简单复述热点
3. 话题要具备话题性、争议性或实用性，适合社交媒体传播
4. 格式如下：

### 1. 话题标题
> 内容方向：一句话说明

（共5个）

只输出这5个创意话题。"""


def export_ai_prompts(target_industries, industry_items, all_items):
    """没有 API Key 时，为每个行业生成一个可直接复制粘贴的提示词文件"""
    today = time.strftime("%Y-%m-%d")
    files = []
    for ind in target_industries:
        items = industry_items.get(ind, [])
        industry_hot = [it["title"] for it in items]
        all_hot = [it["title"] for it in all_items[:12]]
        if not industry_hot and not all_hot:
            continue
        prompt = build_creative_prompt(ind, industry_hot, all_hot)
        fname = f"AI提示词_{ind}_{today}.md"
        fpath = os.path.join(BASE_DIR, "output", fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(f"# AI创意提示词 - {ind} - {today}\n\n")
            f.write("> 👇 复制下方分隔线以内的全部内容，粘贴到 https://chat.deepseek.com\n\n")
            f.write("---复制以下内容---\n\n")
            f.write(prompt)
            f.write("\n\n---复制以上内容---\n")
        files.append({"name": fname, "path": fpath, "industry": ind})
        print(f"  [AI提示词] 已生成 {fname}")
    return files


def generate_md(all_items, industry_items, industries, target_industries, cfg, use_ai=True):
    """生成md文件"""
    today = time.strftime("%Y-%m-%d")
    filename = f"热点日报_{today}.md"
    filepath = os.path.join(BASE_DIR, "output", filename)

    lines = []
    lines.append(f"# 📰 每日热点日报 - {today}\n")
    lines.append(f"> 采集时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    platforms_ok = sorted(set(it["platform"] for it in all_items))
    lines.append(f"> 采集平台：{', '.join(platforms_ok)}\n")

    # ---- Part 1: 全平台热点概览 ----
    lines.append("\n---\n")
    lines.append("## 🔥 全平台热点概览\n")
    # 按平台分组
    by_platform = {}
    for item in all_items:
        by_platform.setdefault(item["platform"], []).append(item)
    max_per = cfg.get("max_items_per_platform", 15)
    for plat in sorted(by_platform.keys()):
        items = by_platform[plat]
        lines.append(f"\n### {plat}（{len(items)}条）\n")
        for i, it in enumerate(items[:max_per], 1):
            hot = f" `{it['hot']}`" if it.get("hot") else ""
            lines.append(f"{i}. [{it['title']}]({it['url']}){hot}")
        if len(items) > max_per:
            lines.append(f"\n_…还有 {len(items)-max_per} 条未显示_\n")

    # ---- Part 2: 行业相关热点 ----
    lines.append("\n---\n")
    lines.append("## 🎯 行业相关热点\n")
    for ind in target_industries:
        items = industry_items.get(ind, [])
        lines.append(f"\n### {ind}（{len(items)}条）\n")
        if not items:
            lines.append("_今日无直接相关热点_\n")
            continue
        for i, it in enumerate(items[:15], 1):
            hot = f" `{it['hot']}`" if it.get("hot") else ""
            lines.append(f"{i}. [{it['title']}]({it['url']}) `{it['platform']}`{hot}")

    # ---- Part 3: AI创意话题 ----
    if use_ai:
        lines.append("\n---\n")
        lines.append("## ✨ AI创意话题\n")
        api_key = cfg.get("deepseek_api_key", "")
        if api_key:
            # 模式A：有 API Key → 自动调用 DeepSeek API
            ai_count = 0
            for ind in target_industries:
                items = industry_items.get(ind, [])
                industry_hot = [it["title"] for it in items]
                all_hot = [it["title"] for it in all_items[:12]]
                if not industry_hot and not all_hot:
                    continue
                print(f"  [AI创意] 正在为「{ind}」生成创意话题...")
                prompt = build_creative_prompt(ind, industry_hot, all_hot)
                result = call_deepseek(prompt, cfg)
                if result:
                    lines.append(f"\n#### {ind}\n")
                    lines.append(result.strip() + "\n")
                    ai_count += 1
                else:
                    lines.append(f"\n#### {ind}\n_（AI生成失败，请检查DeepSeek配置）_\n")
            if ai_count == 0:
                lines.append("\n_API调用未返回结果，请检查 Key 配置_\n")
        else:
            # 模式B：无 API Key → 生成提示词文件，走 DeepSeek 网页版手动流程（免费）
            prompt_files = export_ai_prompts(target_industries, industry_items, all_items)
            lines.append("\n> 💡 **未配置 API Key，已生成手动版提示词文件**\n")
            lines.append("> 用 DeepSeek 网页版（免费）即可，无需充值 API\n")
            lines.append("\n### 📋 操作步骤\n")
            lines.append("\n1. 打开下方提示词文件\n")
            lines.append("2. 复制文件中 `---复制以下内容---` 到 `---复制以上内容---` 之间的全部文字\n")
            lines.append("3. 粘贴到 [DeepSeek 网页版](https://chat.deepseek.com)（登录后直接发）\n")
            lines.append("4. 把返回的创意话题粘贴到本文件下方对应行业\n")
            lines.append("\n### 📎 提示词文件\n")
            for pf in prompt_files:
                lines.append(f"- [{pf['name']}](./{pf['name']})\n")
            lines.append("\n### 创意话题（粘贴区）\n")
            lines.append("_把 DeepSeek 返回的内容粘贴在下方_\n")

    # ---- 写入文件 ----
    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n✅ 已生成：{filepath}")
    print(f"   共 {len(all_items)} 条热点，覆盖 {len(platforms_ok)} 个平台")
    return filepath


def main():
    args = sys.argv[1:]
    use_ai = "--no-ai" not in args
    args = [a for a in args if a != "--no-ai"]

    cfg = load_config()
    industries = cfg.get("industries", {})
    platforms = {k: v for k, v in cfg.get("platforms", {}).items() if v.get("enabled")}

    # 确定目标行业
    if args:
        target_industries = [a for a in args if a in industries]
        unknown = [a for a in args if a not in industries]
        if unknown:
            print(f"⚠️ 未知行业：{unknown}（可选：{list(industries.keys())}）")
        if not target_industries:
            target_industries = list(industries.keys())
    else:
        target_industries = list(industries.keys())

    print(f"📋 目标行业：{', '.join(target_industries)}")
    print(f"📡 启用平台：{', '.join(v['name'] for v in platforms.values())}")
    print(f"🤖 AI创意：{'开启' if use_ai else '关闭'}\n")

    # 采集
    print("=" * 40)
    print("📥 开始采集热点...")
    print("=" * 40)
    all_items = collectors.collect_all(set(platforms.keys()))
    print(f"\n📊 采集完成，共 {len(all_items)} 条\n")

    if not all_items:
        print("❌ 未采集到任何热点，请检查网络")
        return

    # 行业分类
    print("=" * 40)
    print("🏷️ 行业分类...")
    print("=" * 40)
    industry_items = classify_by_industry(all_items, industries)
    for name, items in industry_items.items():
        print(f"  {name}: {len(items)} 条")

    # 生成md
    print("\n" + "=" * 40)
    print("📝 生成报告...")
    print("=" * 40)
    filepath = generate_md(all_items, industry_items, industries,
                           target_industries, cfg, use_ai)
    return filepath


if __name__ == "__main__":
    main()
