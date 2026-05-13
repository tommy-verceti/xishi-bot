# 西施 Bot

基于 **Claude Code + cc-connect + NapCatQQ** 的王者荣耀「西施」QQ 角色扮演机器人。

> 最有价值之物，给最珍贵之人~

## 特性

- QQ 私聊角色扮演，西施人格驱动
- **记忆系统**：跨会话记住用户信息（L1-L5 五层记忆）
- **情绪引擎**：好感度评分 + 7 种情绪状态，影响回复风格
- **主动消息**：早安晚安、随机搭话、长时间未回复提醒
- **表情包**：关键词 + 情绪自动匹配西施表情包
- **Web 面板**：开发者监控仪表盘（FastAPI）

## 架构

```
QQ -> NapCat(:3001) -> V2 Engine(:3002) -> cc-connect -> Claude Code
        HTTP :4000          |
        |                   +-- SQLite (记忆/情绪/对话)
        +-------------------+- Scheduler (主动消息)
                            +- Sticker Matcher (表情包)
                            +- FastAPI :8080 (Web 面板)
```

## 快速开始

### 前置条件

- Windows 11 + Python 3.12+
- QQ 账号 (小号)
- Deepseek API 密钥

### 安装

```bash
git clone https://github.com/tommy-verceti/xishi-bot.git
cd xishi-bot
pip install -r requirements.txt
```

### 配置

1. 安装 [NapCatQQ](https://github.com/NapNeko/NapCatQQ) 并扫码登录
2. 安装 [cc-connect](https://github.com/cc-connect/cc-connect)
3. 复制 `cc-connect/config.toml.example` 为 `config.toml`，填入你的路径和密钥
4. 配置环境变量 `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL`

### 启动

```bash
# 1. 启动 NapCat QQ (扫码登录)
# 2. 启动 V2 Engine (替代 proxy.py)
python v2-engine/main.py

# 3. 启动 cc-connect
cc-connect.exe --config cc-connect/config.toml

# 4. 打开 Web 面板
# http://localhost:8080
```

### QQ 命令

| 命令 | 功能 |
|------|------|
| `/记住 <事实>` | 存储一条记忆 |
| `/忘记 <关键词>` | 删除匹配的记忆 |
| `/我是谁` | 查看西施对你的记忆 |
| `/new` | 刷新 Claude 会话 |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v --cov=v2-engine

# 代码质量
ruff check v2-engine/
black v2-engine/ tests/

# 自动修复
ruff check v2-engine/ --fix
black v2-engine/ tests/
```

## 项目结构

```
xishi-bot/
├── v2-engine/          # V2 引擎 (记忆/情绪/调度/Web)
│   ├── router.py       # WS 消息路由核心
│   ├── memory/         # 记忆管理 + AI 摘要
│   ├── emotion/        # 情绪引擎
│   ├── stickers/       # 表情包匹配
│   ├── scheduler/      # 主动消息调度
│   ├── db/             # SQLite 数据库
│   └── web/            # FastAPI 面板
├── xishi-bot/          # 西施人设 Prompt
├── qq-proxy/           # V1 消息代理 (备份)
├── cc-connect/         # IM 桥接配置模板
├── tests/              # 单元测试 (23 tests)
├── V2.md               # V2 版本说明书
├── requirements.txt    # 依赖清单
└── pyproject.toml      # 项目配置
```

## 技术栈

- **AI**: Claude Code (Deepseek v4-pro)
- **桥接**: cc-connect v1.3.2
- **QQ 协议**: NapCatQQ (OneBot v11)
- **后端**: Python asyncio + FastAPI
- **数据库**: SQLite (WAL mode)
- **测试**: pytest (23 tests)

## License

MIT
