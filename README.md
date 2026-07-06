# 热点雷达 🔥

多平台网络热点采集 & AI 创意话题生成工具。支持今日头条、百度热搜、抖音热榜等平台，按行业智能分类，一键生成 AI 提示词。

## 功能特性

- 📡 **多平台采集**：今日头条、百度热搜、抖音热榜（微博/知乎/小红书容错支持）
- 🏷️ **行业智能分类**：宠物、民生、科技、财经、娱乐、健康
- ✨ **AI 创意提示词**：一键生成，复制粘贴到 DeepSeek 网页版即可使用
- 📊 **可视化仪表盘**：平台分布、热度统计一目了然
- 📥 **导出 MD**：生成带链接的热点日报 Markdown 文件

## 快速开始

### 方式一：网页版（推荐）

```bash
# 1. 启动服务
python web.py

# 2. 浏览器打开
# http://localhost:8080
```

双击 `启动网页版.bat` 也可一键启动（Windows）。

### 方式二：命令行版

```bash
# 采集全部行业，生成 MD 日报
python main.py

# 只看宠物和民生相关热点
python main.py 宠物 民生

# 跳过 AI（无 API Key 时用）
python main.py 宠物 --no-ai
```

## 配置

编辑 `config.json`：

```json
{
  "deepseek_api_key": "sk-你的key",   // 可选，不填也能用（手动模式）
  "deepseek_base_url": "https://api.deepseek.com/v1",
  "deepseek_model": "deepseek-chat"
}
```

> **没有 API Key？** 没关系！工具会以"手动模式"运行：采集热点 → 生成提示词文件 → 复制粘贴到 DeepSeek 网页版（免费）。

## 项目结构

```
hot-trends/
├── web.py              # 网页版服务（推荐）
├── main.py             # 命令行版
├── collectors.py       # 热点采集核心模块
├── config.json         # 配置文件（不提交到 Git）
├── config.example.json # 配置模板
├── 启动网页版.bat      # Windows 一键启动
├── output/             # 生成的日报和提示词
└── README.md
```

## 数据源

| 平台 | 状态 | 说明 |
|------|------|------|
| 今日头条 | ✅ 稳定 | 官方 API |
| 百度热搜 | ✅ 稳定 | 官方 API |
| 抖音热榜 | ✅ 稳定 | 官方 API |
| 微博热搜 | ⏳ 容错 | 需网络环境 |
| 知乎热榜 | ⏳ 容错 | 需网络环境 |
| 小红书 | ⏳ 容错 | 需网络环境 |

## 定时自动化

配合 **WorkBuddy 自动化任务**，每天 8:00 自动采集并推送日报。

## 许可证

MIT License — 自由使用和修改。

## 截图

（待补充 — 启动后访问 http://localhost:8080 查看界面）
