# codebase-skill

语言： [English](README.md) | **简体中文**

> 面向各类 agent 工作流的本地代码索引 CLI，底层基于 `codebase-memory-mcp`。

`codebase-skill` 是一个本地 CLI 工具，并额外提供一个可选的 Codex skill 封装；底层使用官方 [`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp) 作为索引和图查询引擎。

它会把索引存到当前项目的 `.codebase/` 下，对外提供全局 `codebase` 命令，并且在日常使用时不依赖 MCP 协议。

快速导航：[安装](#安装) · [快速开始](#快速开始) · [Codex skill 集成](#codex-skill-集成) · [开发](#开发) · [GitHub 发布](#github-发布)

## 一眼看懂

| 项目 | 方案 |
| --- | --- |
| 索引存储位置 | 项目目录内的 `.codebase/<uuid>/` |
| 运行时模型 | 本地 CLI，不走 MCP 协议 |
| 底层引擎 | `DeusData/codebase-memory-mcp` |
| 主入口 | `codebase` 命令 |
| Agent 集成 | 可选安装到 `~/.codex/skills/codebase/SKILL.md` |
| 目标场景 | Codex、Claude Code、OpenCode、Copilot、本地 CLI |

## 你能得到什么

- 项目本地索引，数据放在 `.codebase/<uuid>/`
- 一个普通 shell 命令：`codebase`
- 可选的 Codex skill 安装
- 更适合 agent 工作流的默认命令：`func`、`calls`、`snippet`、`search-code`、`detect-changes`、`refresh`
- 不依赖 git，不要求运行时 MCP server

## 它和上游的关系

`codebase-memory-mcp` 仍然是实际负责索引和图查询的核心引擎；这个仓库提供的是：

- 项目内本地索引存储约定
- 更适合 agent 直接调用的 CLI 工作流
- 刷新元数据
- 一个很小的可选 skill stub，供 Codex 用户接入

如果你想直接使用上游原始能力，可以直接调用上游工具；如果你想要更务实的本地代码检索工作流，就用这个仓库。

## 为什么做这个

这个项目面向的是想要 code-index 类效果、但又不想每次检索都走一层 MCP 往返的人。

- 把索引留在项目本地，而不是散落到外部状态目录。
- 让 agent 直接调用稳定的 `codebase` 命令，而不是依赖协议层。
- 让项目说明或 agent 提示保持简单：优先 `codebase`，再降级到 `rg`。
- 复用上游图引擎能力，但避免 MCP 运行时开销。

## 安装

### 前置依赖（macOS）

```bash
brew install python
```

### 前置依赖（Ubuntu 24.04）

```bash
sudo apt update
sudo apt install -y curl python3 python3-pip
```

### 一行安装

```bash
curl -fsSL https://raw.githubusercontent.com/hzy9738/codebase-skill/main/scripts/install.sh | bash
```

安装脚本会做这些事：

- 使用 `python3 -m pip install --user` 安装当前包
- 在遇到 PEP 668 风格环境时自动尝试 `--break-system-packages`
- 把可执行命令安装到 `~/.local/bin/codebase`
- 在安装阶段尽量把 `codebase-memory-mcp` 一起装好

### 从本地 clone 安装

```bash
git clone https://github.com/hzy9738/codebase-skill.git
cd codebase-skill
bash scripts/install.sh
```

## 快速开始

```bash
codebase index --mode moderate
codebase func login
codebase calls login --direction both
codebase snippet login
codebase search-code redis --file-pattern '*.go'
codebase detect-changes
codebase refresh
```

常用诊断命令：

```bash
codebase self-check
codebase status
codebase --version
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

1. 新项目先执行一次 `codebase index`。
2. 用 `codebase func` 找函数或方法。
3. 用 `codebase calls` 和 `codebase snippet` 看调用关系和源码。
4. 用 `codebase search-code` 做偏文本的检索。
5. 日常更新时优先用 `codebase refresh`，不要反复全量重建。

会话行为：

- 索引按 session 隔离，路径是 `<project>/.codebase/<uuid>/`。
- Session UUID 通过遍历父进程 PID 自动检测（Claude Code 读取 `~/.claude/sessions/<pid>.json`；Codex/OpenCode 从命令行提取），检测不到则自动生成随机 UUID。
- 也可以手动用 `codebase --session <id> ...` 或 `CODEBASE_SESSION=<id>` 覆盖。
- 首次正常使用时不会自动联网下载运行时；如果缺少 `codebase-memory-mcp`，请显式执行 `codebase install-runtime`。

## 可选 skill 安装

`codebase` 本质上是 CLI-first，任何能执行 shell 命令的 agent 都能直接调用。skill 封装是可选的，且刻意保持很小。

交互式安装 skill 文件：

```bash
bash scripts/install-skill.sh
```

运行后会提示选择安装目录：

- `~/.agent/skills`（默认）
- `~/.claude/skills`（Claude Code）
- `~/.codex/skills`（Codex）
- `~/.opencode/skills`（OpenCode）
- `~/.cc-switch/skills`（cc-switch）
- 或手动输入路径

也可以直接传参指定：

```bash
bash scripts/install-skill.sh ~/.claude/skills
```

推荐写进项目 `AGENTS.md` 的规则：

```md
- 内部代码和文档检索优先使用 `codebase` skill，不可用或无结果时再降级到 `rg`、`fd` 或其他命令。
```

## 命令列表

- `status`：查看项目、缓存、元数据和索引状态
- `install-runtime`：显式把 `codebase-memory-mcp` 安装到 `~/.local/bin`
- `index`：构建或重建本地索引
- `refresh`：仅在索引缺失或模式变化时重建
- `projects`：列出当前本地缓存里的索引项目
- `reset`：删除 `.codebase`
- `self-check`：检查 PATH、依赖、session 识别和工具连通性
- `func`：搜索已索引的函数和方法
- `calls`：查看某个符号的调用方和被调用方
- `snippet`：打印某个符号对应的源码片段
- `search-code`：带图排序能力的文本/代码搜索
- `search-graph`：直接包装上游 `search_graph`
- `trace-path`：直接包装上游 `trace_path`
- `query-graph`：直接包装上游 `query_graph`
- `detect-changes`：查看变更文件和受影响符号
- `architecture`：输出架构摘要
- `schema`：输出图 schema 摘要
- `index-status`：查看上游索引状态
- `adr`：通过上游 `manage_adr` 获取或更新 ADR
- `ingest-traces`：通过上游 `ingest_traces` 注入运行时 trace

运行时查找顺序：

1. `CBM_CODEBASE_MEMORY_BIN`
2. `PATH` 里的 `codebase-memory-mcp`
3. `~/.local/bin/codebase-memory-mcp`

## 开发

本地检查：

```bash
bash tests/smoke_test.sh
```

不安装、直接运行包装器：

```bash
bin/codebase --help
```

贡献和发布流程：

- 见 `CONTRIBUTING.md`
- 见 `RELEASING.md`

## GitHub 发布

仓库 About、topics、首个 release 文案等可直接复用的内容放在 `GITHUB_PUBLICATION.md`。

## 限制

- 索引质量和图行为仍然依赖 `DeusData/codebase-memory-mcp`
- 首次建索引的主要成本仍然来自上游索引器
- `ingest-traces` 仍受上游 runtime edge 能力限制
- 它不是 `rg` 的替代品，而是优先使用的索引检索层

## 许可证

MIT
