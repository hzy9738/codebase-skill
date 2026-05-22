# codebase-skill

语言： [English](README.md) | **简体中文**

> 一个轻量级的 Node.js CLI 工具，为你的终端带来深度代码检索能力 —— 无需 Python，运行时零 MCP 协议。

`codebase-skill` 将官方 [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp) 引擎封装成一个简单的 `codebase` 命令，索引存于项目目录下，会话自动识别，一切通过命令行搞定。

快速导航：[安装](#安装) · [快速开始](#快速开始) · [可选 skill 安装](#可选-skill-安装) · [开发](#开发) · [GitHub 发布](#github-发布)

## 一目了然

| 项目 | 方案 |
| --- | --- |
| 开发语言 | Node.js（零 Python 依赖） |
| 索引存储 | 项目目录内的 `.codebase/<uuid>/` |
| 运行时模型 | 本地 CLI，不走 MCP 协议 |
| 底层引擎 | `DeusData/codebase-memory-mcp` |
| 主入口 | `codebase` 命令 |
| Agent 集成 | 可选安装到 `~/.agents/skills/codebase/` |
| 适用场景 | Codex、Claude Code、OpenCode、Copilot、终端 |

## 你能得到什么

- 一个全局可用的 `codebase` 命令
- 项目本地索引，数据放在 `.codebase/<uuid>/`
- 为 Agent 优化的默认命令：`func`、`calls`、`snippet`、`search-code`、`detect-changes`、`refresh`
- 可选的多工具 skill 安装
- 不依赖 git、不依赖 MCP 运行时、不依赖 Python

## 与上游的关系

`codebase-memory-mcp` 仍然是实际负责索引和图查询的核心引擎。这个仓库提供的是：

- 项目内本地索引存储约定
- 更适合 Agent 直接调用的 CLI 工作流
- 刷新元数据
- 一个轻量级的 skill stub，支持 Claude Code、Codex、OpenCode 等工具

如果想直接使用上游原始能力，可以调用官方工具；如果想用更务实的本地代码检索方案，就用这个仓库。

## 为什么做这个项目

面向想要代码索引效果、但又不想每次查询都走 MCP 往返的团队和个人：

- 索引留在项目本地，而不是散落到外部目录
- Agent 直接调用稳定的 `codebase` 命令，不依赖协议层
- 提示词保持简单：优先 `codebase`，再降级到 `rg`
- 复用上游引擎能力，但避开 MCP 运行时开销

## 安装

### 前置条件

需要 Node.js >= 19。选择你喜欢的方式安装：

```bash
# macOS
brew install node

# Linux (Ubuntu)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# 或者用 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
nvm install 22
```

### 一行安装

```bash
curl -fsSL https://raw.githubusercontent.com/hzy9738/codebase-skill/main/scripts/install.sh | bash
```

安装脚本会做以下事情：

- 检查 Node.js >= 19 是否可用
- 将 `codebase` CLI 复制到 `~/.local/bin/codebase`
- 如果尚未安装，自动安装上游 `codebase-memory-mcp`
- 可选：提示是否安装 Agent skill 文件

### 从本地克隆安装

```bash
git clone https://github.com/hzy9738/codebase-skill.git
cd codebase-skill
bash scripts/install.sh
```

## 快速开始

```bash
codebase index --mode moderate   # 首次使用：构建索引
codebase func login              # 搜索名为 "login" 的函数
codebase calls login --direction both  # 查看调用者和被调用者
codebase snippet login           # 查看函数源码
codebase search-code redis --file-pattern '*.go'  # 文本搜索
codebase detect-changes          # 上次索引以来有什么变化？
codebase refresh                 # 增量刷新索引
```

常用诊断命令：

```bash
codebase self-check              # 检查环境配置是否正确
codebase status                  # 查看当前会话索引状态
codebase --version               # 应该显示 v0.6.1
```

## 在项目里怎么工作

`codebase` 将索引写入当前工作目录：

```text
<project>/.codebase/
  d0f7ca83-c52c-450e-8cc0-4f4f2f3313b8/
    index/*.db
    metadata.json
  019da154-2915-7413-852c-230622b512f4/
    index/*.db
    metadata.json
```

典型工作流：

1. 新项目首次运行 `codebase index`
2. 用 `codebase func` 查找候选函数或方法
3. 定位到目标符号后，用 `codebase calls` 和 `codebase snippet` 深入了解
4. 用 `codebase search-code` 进行文本搜索
5. 后续用 `codebase refresh` 增量更新，而非反复全量重建

会话机制说明：

- 索引数据按会话隔离，存储在 `<project>/.codebase/<uuid>/`
- 会话 UUID 通过 PID 查找自动识别父级 Agent 进程（Claude Code、Codex、OpenCode）
- 可通过 `codebase --session <id> ...` 或 `CODEBASE_SESSION=<id>` 手动指定
- 首次使用不会自动下载运行环境 —— 请先用 `codebase install-runtime` 一次性安装

## 可选 skill 安装

skill 文件能告诉 AI Agent（Claude Code、Codex、OpenCode）如何调用 `codebase` CLI。安装器会在设置过程中提示，也可以手动安装：

```bash
bash scripts/install-skill.sh
```

### 支持的安装路径

| 工具 | 默认路径 |
| --- | --- |
| 通用 | `~/.agents/skills/codebase/` |
| Claude Code | `~/.claude/skills/codebase/` |
| Codex | `~/.codex/skills/codebase/` |
| OpenCode | `~/.opencode/skills/codebase/` |

安装后，Agent 会获得一个 skill stub，包含：

- CLI 命令示例（`func`、`calls`、`snippet`、`refresh` 等）
- 优先使用 `codebase`，降级到 `rg` 的指引
- 会话和索引工作流说明

## 进阶用法

```bash
# 检查上游健康状态
codebase index-status

# 查看架构概览
codebase architecture

# 执行原生图查询
codebase query-graph

# 导入运行时追踪数据
codebase ingest-traces traces.json
```

## 开发

```bash
git clone https://github.com/hzy9738/codebase-skill.git
cd codebase-skill

# 本地运行
node bin/codebase --version
node bin/codebase --help

# 从本地副本安装
bash scripts/install.sh

# 运行冒烟测试
bash tests/smoke_test.sh
```

### 项目结构

```text
bin/codebase          # CLI 入口（独立 Node.js 脚本）
src/cli.js            # 模块化 CLI 实现
scripts/install.sh    # 一行安装脚本
scripts/install-skill.sh  # Skill 安装脚本
skill/SKILL.md        # Agent skill 定义
tests/                # 冒烟测试
```

## GitHub 发布

> 详细发布指南请参考 [GITHUB_PUBLICATION.md](GITHUB_PUBLICATION.md)

快速清单：

- [ ] 更新 `package.json` 中的 `version`
- [ ] 打标签发布：`git tag v0.6.1 && git push origin v0.6.1`
- [ ] 验证安装器：`curl -fsSL .../install.sh | bash`

## 发布流程

完整发布流程请参考 [RELEASING.md](RELEASING.md)。

## 参与贡献

欢迎贡献！请参考 [CONTRIBUTING.md](CONTRIBUTING.md) 了解准则。

## 许可证

[MIT](LICENSE)