#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 data/hot-news.json - 供 GitHub Pages 静态页面使用"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collectors

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "hot-news.json")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    all_items = []
    for name, func in [
        ("今日头条", collectors.collect_toutiao),
        ("百度热搜", collectors.collect_baidu),
        ("抖音热榜", collectors.collect_douyin),
    ]:
        try:
            items = func()
            print(f"  [{name}] 采集 {len(items)} 条")
            all_items.extend(items)
        except Exception as e:
            print(f"  [{name}] 失败: {e}")

    # 去重
    seen = set()
    unique_items = []
    for it in all_items:
        key = it["title"]
        if key not in seen:
            seen.add(key)
            unique_items.append(it)

    today = datetime.now().strftime("%Y-%m-%d")
    data = {
        "date": today,
        "updated_at": datetime.now().isoformat(),
        "items": unique_items,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] 已生成 {OUTPUT_FILE}，共 {len(unique_items)} 条热点")


if __name__ == "__main__":
    main()
