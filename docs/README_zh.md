<div align="center">

# WeChat MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

中文 | [English](../README.md)

</div>

一个基于 macOS 无障碍 API 和屏幕截图的 MCP 服务器，可自动化操作微信。它让 LLM 能够以编程方式与微信聊天进行交互。

> 面向 **macOS 微信 4.x**（在 4.1.13 英文界面上验证）。服务器会在每次调用时检查已安装/正在运行的微信版本，发现升级到未验证版本、升级后未重启、或界面元素缺失时，会在返回结果的 `warnings` / `diagnostics` 中提示。新增工具：`list_chats`（会话列表）、`check_wechat_compatibility`（兼容性报告）；`fetch_messages_by_chat` 现在返回 `sender_name` 与 `kind`，`reply_to_messages_by_chat` 只在确认打开了正确会话后才发送。需同时授予「辅助功能」和「屏幕录制」权限。

## 功能特性

- 📨 获取任何聊天（联系人或群组）的最近消息
- ✍️ 基于聊天历史自动发送回复
- 📷 发布纯文字朋友圈消息，并可设置仅创建草稿
- 👥 通过微信号添加联系人并配置隐私选项
- 🔍 智能聊天搜索，支持精确名称匹配
- 🤖 5 个专门为微信自动化设计的 Claude Code 子代理

## 快速开始

### 安装

```bash
pip install wechat-mcp-server
```

### 在 Claude Code 中配置

```bash
# 如果通过 pip 安装
claude mcp add --transport stdio wechat-mcp -- wechat-mcp

# 如果使用 uv 进行开发
claude mcp add --transport stdio wechat-mcp -- uv --directory $(pwd) run wechat-mcp
```

<details>
<summary>在 Claude Desktop 中配置</summary>

```json
// 如果通过 pip 安装
{
  "mcpServers": {
    "wechat-mcp": {
      "type": "stdio",
      "command": "wechat-mcp"
    }
  }
}

// 如果使用 uv 进行开发
{
  "mcpServers": {
    "wechat-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "{path/to/wechat-mcp}",
        "run",
        "wechat-mcp"
      ],
    }
  }
}
```

</details>

<details>
<summary>在 Codex 中配置</summary>

```bash
# 如果通过 pip 安装
codex mcp add wechat-mcp -- wechat-mcp

# 如果使用 uv 进行开发
codex mcp add wechat-mcp -- uv --directory $(pwd) run wechat-mcp
```

</details>

### macOS 权限设置

⚠️ **重要**：为终端授予无障碍权限：

1. 打开**系统设置 → 隐私与安全性 → 辅助功能**
2. 添加你的终端应用程序（Terminal.app、iTerm2 等）
3. 使用服务器前确保微信正在运行

## 使用方法

### 基本命令

```bash
# 使用默认的 stdio 传输方式运行
wechat-mcp --transport stdio

# 使用 HTTP 传输方式运行
wechat-mcp --transport streamable-http

# 使用 SSE 传输方式运行
wechat-mcp --transport sse
```

### 可用的 MCP 工具

- **`fetch_messages_by_chat`** - 获取聊天的最近消息
- **`reply_to_messages_by_chat`** - 向聊天发送回复
- **`add_contact_by_wechat_id`** - 通过微信号添加联系人并发送好友申请
- **`publish_moment_without_media`** - 发布纯文字朋友圈（无图片或视频），也可以通过 `publish=False` 仅填充草稿而不真正发布

完整的工具规格请查看[详细 API 文档](detailed-guide.md)。

## Claude Code 子代理

本项目包含 5 个专门为微信自动化设计的智能子代理。它们通过 Claude Code 实现对微信的自然语言控制。

### 可用的子代理

1. **聊天记录总结器** - 总结聊天历史并提取关键信息
2. **自动回复器** - 自动生成并发送合适的回复
3. **消息搜索器** - 在聊天历史中搜索特定内容
4. **多聊天监控器** - 监控多个聊天并优先处理消息
5. **聊天洞察分析器** - 分析关系动态和沟通模式

📖 [查看完整的子代理指南](../.claude/agents/README.md)

## 开发

### 使用 uv 进行本地设置

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆并设置
git clone https://github.com/yourusername/WeChat-MCP.git
cd WeChat-MCP
uv sync

# 本地运行
uv run wechat-mcp --transport stdio
```

## 文档

- 📘 [详细指南](detailed-guide.md) - 完整的 API 文档和架构说明
- 🤖 [子代理指南](../.claude/agents/README.md) - 如何使用 Claude Code 子代理

## 系统要求

- macOS（使用无障碍 API）
- 已安装并运行微信 Mac 版
- Python 3.12+
- 终端的无障碍权限

## 贡献

欢迎贡献！请随时提交 Pull Request。

## 许可证

MIT License - 详见 [LICENSE](../LICENSE) 文件
