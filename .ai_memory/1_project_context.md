# 项目记忆

## 项目目标

MediaCrawler 是一个功能强大的**多平台自媒体数据采集工具**，支持小红书、抖音、快手、B站、微博、贴吧、知乎等主流平台的公开信息抓取。

## 技术架构

- **语言**：Python 3.11
- **框架**：Playwright（浏览器自动化）+ httpx（HTTP客户端）
- **数据库**：SQLite / MySQL / MongoDB（可选）
- **核心原理**：利用 Playwright 保留登录态，通过 JS 表达式获取签名参数，无需逆向复杂加密算法

## 核心规范

### 目录结构
```
MediaCrawler/
├── main.py                 # 程序入口
├── config/                 # 配置目录
│   ├── base_config.py      # 基础配置（平台选择、爬取模式等）
│   └── xhs_config.py       # 各平台专属配置
├── media_platform/         # 平台爬虫实现
│   ├── xhs/                # 小红书模块
│   │   ├── core.py         # 爬虫核心逻辑
│   │   ├── client.py       # API客户端
│   │   └── login.py        # 登录逻辑
│   └── ...                 # 其他平台类似结构
├── store/                  # 数据存储层
├── model/                  # 数据模型定义
├── tools/                  # 工具类
├── proxy/                  # 代理IP池
└── database/               # 数据库ORM
```

### 运行命令
```bash
# 关键词搜索爬取
uv run main.py --platform xhs --lt qrcode --type search

# 帖子详情爬取
uv run main.py --platform xhs --lt qrcode --type detail

# 查看帮助
uv run main.py --help
```

### 支持的平台
| 平台代号 | 平台名称 |
|---------|---------|
| xhs     | 小红书   |
| dy      | 抖音     |
| ks      | 快手     |
| bili    | B站      |
| wb      | 微博     |
| tieba   | 贴吧     |
| zhihu   | 知乎     |
