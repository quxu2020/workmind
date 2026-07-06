# -*- coding: utf-8 -*-
"""
热点采集模块 - 零依赖（仅标准库）
每个平台一个采集函数，统一返回格式：
  [{"title": str, "url": str, "hot": str, "platform": str}]
失败返回空列表并打印日志，不影响其他平台。
"""
import json
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"

# 关闭证书校验以应对部分环境证书问题
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def _get(url, headers=None, timeout=12):
    """通用GET请求，返回 (status_code, text)"""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


def _hot_str(val):
    """热度值转可读字符串"""
    try:
        n = int(val)
        if n >= 10000_0000:
            return f"{n/10000_0000:.1f}亿"
        if n >= 10000:
            return f"{n/10000:.1f}万"
        return str(n)
    except (ValueError, TypeError):
        return str(val) if val else ""


# ---------- 今日头条 ----------
def collect_toutiao():
    """今日头条官方热榜API（已验证可用）"""
    code, text = _get("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc")
    if code != 200:
        print(f"  [今日头条] 请求失败 code={code}")
        return []
    try:
        data = json.loads(text).get("data", [])
        result = []
        for item in data:
            cid = item.get("ClusterIdStr", "")
            # 生成干净的trending链接，去掉冗长的log_pb参数
            clean_url = f"https://www.toutiao.com/trending/{cid}/" if cid else item.get("Url", "")
            result.append({
                "title": item.get("Title", ""),
                "url": clean_url,
                "hot": _hot_str(item.get("HotValue")),
                "platform": "今日头条",
                "tag": item.get("Label", "")
            })
        print(f"  [今日头条] 采集 {len(result)} 条")
        return result
    except Exception as e:
        print(f"  [今日头条] 解析失败: {e}")
        return []


# ---------- 百度热搜 ----------
def collect_baidu():
    """百度热搜API（已验证可用）"""
    code, text = _get("https://top.baidu.com/api/board?platform=wise&tab=realtime",
                       headers={"User-Agent": UA_MOBILE})
    if code != 200:
        print(f"  [百度热搜] 请求失败 code={code}")
        return []
    try:
        cards = json.loads(text).get("data", {}).get("cards", [])
        result = []
        for card in cards:
            # 百度热搜结构为双层 content 嵌套: cards[].content[].content[]
            for content_group in card.get("content", []):
                if isinstance(content_group, dict):
                    word_list = content_group.get("content", [])
                else:
                    word_list = [content_group]
                for c in word_list:
                    if isinstance(c, dict) and c.get("word"):
                        result.append({
                            "title": c.get("word", ""),
                            "url": c.get("url", ""),
                            "hot": _hot_str(c.get("hotScore")),
                            "platform": "百度热搜"
                        })
        print(f"  [百度热搜] 采集 {len(result)} 条")
        return result
    except Exception as e:
        print(f"  [百度热搜] 解析失败: {e}")
        return []


# ---------- 抖音热榜 ----------
def collect_douyin():
    """抖音热榜API（已验证可用）"""
    code, text = _get("https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/",
                       headers={"User-Agent": UA_MOBILE})
    if code != 200:
        print(f"  [抖音热榜] 请求失败 code={code}")
        return []
    try:
        word_list = json.loads(text).get("word_list", [])
        result = []
        for w in word_list:
            result.append({
                "title": w.get("word", ""),
                "url": f"https://www.douyin.com/search/{urllib.parse.quote(w.get('word', ''))}",
                "hot": _hot_str(w.get("hot_value")),
                "platform": "抖音热榜"
            })
        print(f"  [抖音热榜] 采集 {len(result)} 条")
        return result
    except Exception as e:
        print(f"  [抖音热榜] 解析失败: {e}")
        return []


# ---------- 微博热搜 ----------
def collect_weibo():
    """微博热搜：多策略容错"""
    # 策略1: weibo ajax接口（可能需要cookie）
    code, text = _get("https://weibo.com/ajax/side/hotSearch",
                       headers={"User-Agent": UA, "Accept": "application/json"})
    if code == 200:
        try:
            realtime = json.loads(text).get("data", {}).get("realtime", [])
            if realtime:
                result = []
                for item in realtime:
                    result.append({
                        "title": item.get("word", "") or item.get("note", ""),
                        "url": f"https://s.weibo.com/weibo?q={urllib.parse.quote(item.get('word', ''))}",
                        "hot": _hot_str(item.get("num")),
                        "platform": "微博热搜"
                    })
                print(f"  [微博热搜] 采集 {len(result)} 条")
                return result
        except Exception:
            pass

    # 策略2: 备选聚合接口
    for api_url in [
        "https://tenapi.cn/v2/weibohot",
        "https://api.pearktrue.cn/api/weibo/hot.php",
    ]:
        code, text = _get(api_url, timeout=8)
        if code == 200 and text and text[0] in "{[":
            try:
                obj = json.loads(text)
                items = obj.get("data") or obj.get("list") or obj
                if isinstance(items, list) and items:
                    result = []
                    for item in items[:15]:
                        title = item.get("title") or item.get("word") or item.get("name", "")
                        if title:
                            result.append({
                                "title": title,
                                "url": item.get("url", f"https://s.weibo.com/weibo?q={urllib.parse.quote(title)}"),
                                "hot": _hot_str(item.get("hot") or item.get("num")),
                                "platform": "微博热搜"
                            })
                    if result:
                        print(f"  [微博热搜] 采集 {len(result)} 条（聚合源）")
                        return result
            except Exception:
                continue

    print("  [微博热搜] 采集失败（反爬），已跳过")
    return []


# ---------- 知乎热榜 ----------
def collect_zhihu():
    """知乎热榜：多策略容错"""
    # 策略1: 官方API（带特殊header尝试）
    code, text = _get("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20",
                       headers={"User-Agent": UA, "Referer": "https://www.zhihu.com/hot"})
    if code == 200:
        try:
            data = json.loads(text).get("data", [])
            if data:
                result = []
                for item in data:
                    target = item.get("target", {})
                    title = target.get("title", "")
                    if title:
                        result.append({
                            "title": title,
                            "url": f"https://www.zhihu.com/question/{target.get('id', '')}",
                            "hot": _hot_str(item.get("detail_text", "").replace("万热度", "").strip()) + "热度" if item.get("detail_text") else "",
                            "platform": "知乎热榜"
                        })
                print(f"  [知乎热榜] 采集 {len(result)} 条")
                return result
        except Exception:
            pass

    # 策略2: 备选聚合接口
    for api_url in [
        "https://tenapi.cn/v2/zhihuhot",
        "https://api.pearktrue.cn/api/zhihu/hot.php",
    ]:
        code, text = _get(api_url, timeout=8)
        if code == 200 and text and text[0] in "{[":
            try:
                obj = json.loads(text)
                items = obj.get("data") or obj.get("list") or obj
                if isinstance(items, list) and items:
                    result = []
                    for item in items[:15]:
                        title = item.get("title") or item.get("title_name") or item.get("name", "")
                        if title:
                            result.append({
                                "title": title,
                                "url": item.get("url", f"https://www.zhihu.com/search?q={urllib.parse.quote(title)}"),
                                "hot": _hot_str(item.get("hot")),
                                "platform": "知乎热榜"
                            })
                    if result:
                        print(f"  [知乎热榜] 采集 {len(result)} 条（聚合源）")
                        return result
            except Exception:
                continue

    print("  [知乎热榜] 采集失败（需认证），已跳过")
    return []


# ---------- 小红书 ----------
def collect_xiaohongshu():
    """小红书热点：反爬最强，多策略尝试"""
    # 策略1: 探索页API（大概率需cookie，尝试）
    code, text = _get("https://edith.xiaohongshu.com/api/sns/web/v1/feed",
                       headers={"User-Agent": UA, "Referer": "https://www.xiaohongshu.com/"})
    if code == 200:
        try:
            items = json.loads(text).get("data", {}).get("items", [])
            if items:
                result = []
                for item in items[:15]:
                    note = item.get("note_card", {})
                    title = note.get("display_title", "")
                    if title:
                        result.append({
                            "title": title,
                            "url": f"https://www.xiaohongshu.com/explore/{item.get('id', '')}",
                            "hot": _hot_str(item.get("interact_info", {}).get("liked_count")),
                            "platform": "小红书"
                        })
                if result:
                    print(f"  [小红书] 采集 {len(result)} 条")
                    return result
        except Exception:
            pass

    # 策略2: 备选聚合接口
    for api_url in [
        "https://tenapi.cn/v2/xiaohongshu",
        "https://api.pearktrue.cn/api/xhs/hot.php",
    ]:
        code, text = _get(api_url, timeout=8)
        if code == 200 and text and text[0] in "{[":
            try:
                obj = json.loads(text)
                items = obj.get("data") or obj.get("list") or obj
                if isinstance(items, list) and items:
                    result = []
                    for item in items[:15]:
                        title = item.get("title") or item.get("name", "")
                        if title:
                            result.append({
                                "title": title,
                                "url": item.get("url", f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(title)}"),
                                "hot": _hot_str(item.get("hot")),
                                "platform": "小红书"
                            })
                    if result:
                        print(f"  [小红书] 采集 {len(result)} 条（聚合源）")
                        return result
            except Exception:
                continue

    print("  [小红书] 采集失败（反爬），已跳过")
    return []


# ---------- 汇总入口 ----------
COLLECTORS = {
    "toutiao": collect_toutiao,
    "baidu": collect_baidu,
    "douyin": collect_douyin,
    "weibo": collect_weibo,
    "zhihu": collect_zhihu,
    "xiaohongshu": collect_xiaohongshu,
}


def collect_all(enabled_platforms):
    """采集所有启用的平台，返回汇总列表"""
    all_items = []
    for key, func in COLLECTORS.items():
        if key in enabled_platforms:
            try:
                items = func()
                all_items.extend(items)
            except Exception as e:
                print(f"  [{key}] 异常: {e}")
            time.sleep(0.5)  # 请求间隔，避免过快
    return all_items


if __name__ == "__main__":
    # 快速测试
    print("=== 采集测试 ===")
    for name, func in COLLECTORS.items():
        print(f"\n--- {name} ---")
        items = func()
        for it in items[:3]:
            print(f"  {it['title'][:40]}  {it.get('hot','')}")
