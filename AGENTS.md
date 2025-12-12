# Repository Guidelines

## 项目结构与模块组织

- `main.py` 是主入口（Typer CLI），负责解析参数并调度平台爬虫。
- `media_platform/` 按平台拆分爬取逻辑（小红书/抖音/B 站等）。
- `model/` 存放 Pydantic 数据模型；`constant/` 为常量与枚举。
- `config/` 为运行配置（如 `base_config.py`、平台配置）。敏感信息只放本地，不要提交。
- `database/`、`store/` 负责数据落库与导出（Mongo/SQLite/MySQL/Excel 等）。
- `proxy/` 提供代理池与 IP 管理；`tools/`、`base/` 为通用工具与基础设施。
- 文档在 `docs/`（VitePress）；测试在 `test/` 与 `tests/`。

## 构建、测试与开发命令

- 安装依赖：`uv sync`（推荐）或 `pip install -r requirements.txt`。
- 安装浏览器驱动：`uv run playwright install`。
- 本地运行：`uv run main.py --platform xhs --lt qrcode --type search`，更多参数见 `uv run main.py --help`。
- 运行测试：`pytest` 或 `uv run pytest`。
- 本地文档站：`npm install` 后执行 `npm run docs:dev`。

## 代码风格与命名约定

- Python 3.11+，缩进 4 空格；函数/模块使用 `snake_case`，类使用 `PascalCase`，常量全大写。
- 变更前运行 `pre-commit run --all-files`，确保文件头与基础格式检查通过。
- 异步代码保持一致（`async`/`await`），数据模型优先使用 Pydantic 类型声明。

## 测试指南

- 测试框架为 `pytest` + `pytest-asyncio`；测试文件命名 `test_*.py`，共享 fixture 放在 `tests/conftest.py`。
- 新增功能应附带对应单元测试；涉及外部服务时优先 mock 或使用可控的本地环境。

## 提交与 Pull Request 规范

- 提交信息遵循 Conventional Commits：`feat: ...`、`fix: ...`、`docs: ...`、`chore: ...`、`refactor: ...`。
- PR 需说明动机、影响范围与测试结果；若修改爬虫逻辑，请附示例参数或抓取结果截图便于复现。

## 配置与安全提示

- 账号、Cookie、代理密钥等使用本地配置或 `.env` 环境变量管理，不要提交到仓库。
- 抓取行为需遵守目标站点 ToS/robots，合理控制频率与并发。

