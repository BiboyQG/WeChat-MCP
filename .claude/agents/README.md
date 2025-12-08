# WeChat-MCP 子代理使用指南

本项目包含 5 个专门为 WeChat-MCP 设计的智能子代理（Sub-agents），帮助用户更高效地管理和使用微信聊天功能。

## 📋 子代理列表

<details>
<summary>聊天记录总结器 (chat-summarizer)</summary>

**用途**：总结指定聊天的历史消息，提取重要信息、事实和话题

**使用场景**：

- 快速了解某个聊天的主要内容
- 回顾重要信息和决定
- 查找待办事项和关键日期

**使用方法**：

```
使用 chat-summarizer 总结与 [联系人/群名] 的聊天记录
帮我总结一下和小明最近聊了什么
```

**参数**：

- `chat_name`: 聊天对象或群组名称

</details>

<details>
<summary>自动回复器 (auto-replier)</summary>

**用途**：读取最近消息，理解上下文后自动生成并发送回复

**使用场景**：

- 快速回复某个聊天
- 忙碌时需要及时响应
- 简单的确认或回应

**使用方法**：

```
使用 auto-replier 帮我回复一下 [联系人]
用 auto-replier 自动回复小李的消息
```

**参数**：

- `chat_name`: 需要回复的聊天对象

**特点**：

- 自动获取最近 30 条消息
- 理解对话上下文
- 生成得体的回复
- 遵循安全守则（不做重要承诺）

</details>

<details>
<summary>消息搜索器 (message-searcher)</summary>

**用途**：在聊天历史中搜索特定内容、关键词或话题

**使用场景**：

- 查找之前提到的信息
- 搜索特定话题的讨论
- 找回分享的链接或文件

**使用方法**：

```
使用 message-searcher 在与小明的聊天中搜索 "见面时间"
用 message-searcher 找一下小红分享的那篇文章
```

**参数**：

- `chat_name`: 要搜索的聊天对象
- `search_query`: 搜索关键词或话题

**特点**：

- 支持关键词、话题、人物搜索
- 提供上下文信息
- 相关度评分
- 搜索结果清晰展示

</details>

<details>
<summary>多聊天监控器 (multi-chat-checker)</summary>

**用途**：同时检查多个聊天的最新消息，识别重要和需要回复的内容

**使用场景**：

- 早上查看所有聊天更新
- 快速了解哪些聊天需要关注
- 筛选优先处理的消息

**使用方法**：

```
使用 multi-chat-checker 检查 [小明, 小红, 工作群] 的消息
用 multi-chat-checker 看看哪些聊天需要我回复
```

**参数**：

- `chat_names`: 需要检查的聊天列表
- `priority_keywords`: （可选）优先关注的关键词

**特点**：

- 按紧急程度分类
- 识别需要立即回复的消息
- 过滤群聊无关消息
- 提供行动建议

</details>

<details>
<summary>聊天洞察分析器 (chat-insights)</summary>

**用途**：深入分析聊天模式、关系动态和沟通习惯，提供洞察和建议

**使用场景**：

- 了解某段关系的状态
- 改进沟通方式
- 分析聊天模式

**使用方法**：

```
使用 chat-insights 分析我和小明的聊天
用 chat-insights 看看我和女朋友的聊天怎么样
```

**参数**：

- `chat_name`: 要分析的聊天对象
- `analysis_focus`: （可选）分析重点

**特点**：

- 关系亲密度评估
- 沟通模式分析
- 话题分布统计
- 情感基调识别
- 提供改进建议

</details>

---

## 🚀 快速开始

### 使用方法

在与 Claude 对话时，可以通过以下方式调用子代理：

#### 方法 1：明确指定

```
使用 [子代理名称] 来 [执行任务]
```

#### 方法 2：自然描述

```
帮我总结一下和小明的聊天  # Claude 会自动选择 chat-summarizer
帮我回复一下工作群  # Claude 会自动选择 auto-replier
```

### 示例对话

**场景 1：总结聊天**

```
用户：帮我总结一下和张经理最近聊了什么
Claude：我会使用 chat-summarizer 为你总结...
[调用 chat-summarizer，获取并分析消息]
[返回结构化总结报告]
```

**场景 2：发送消息**

```
用户：帮我给小红发个消息，约她周末一起吃饭
Claude：我会使用 message-composer 帮你撰写消息...
[分析聊天历史]
[生成并发送：]
  消息1: "小红，周末有空吗？"
  消息2: "想约你出来吃个饭聊聊天"
```

**场景 3：自动回复**

```
用户：帮我回复一下李总
Claude：我会使用 auto-replier 帮你回复...
[获取最近消息，分析上下文]
[生成并发送合适的回复]
```

**场景 4：搜索消息**

```
用户：在和小明的聊天里找一下我们约的见面时间
Claude：我会使用 message-searcher 搜索...
[搜索相关消息]
[返回匹配结果和上下文]
```

**场景 5：检查多个聊天**

```
用户：看看小明、小红和工作群有什么新消息
Claude：我会使用 multi-chat-checker 检查...
[检查所有聊天]
[返回优先级分类的报告]
```

**场景 6：分析聊天**

```
用户：分析一下我和女朋友的聊天
Claude：我会使用 chat-insights 分析...
[深入分析聊天记录]
[返回洞察报告和改进建议]
```

---

## 🎯 选择合适的子代理

| 需求                   | 推荐子代理         |
| ---------------------- | ------------------ |
| 了解聊天内容           | chat-summarizer    |
| 发送消息但不知道怎么说 | message-composer   |
| 快速回复消息           | auto-replier       |
| 查找历史信息           | message-searcher   |
| 批量检查多个聊天       | multi-chat-checker |
| 了解关系状态或改进沟通 | chat-insights      |

---

## ⚙️ 技术细节

### 工具权限

各子代理使用的 MCP 工具：

- **只读取**：chat-summarizer, message-searcher, multi-chat-checker, chat-insights

  - 工具：`mcp__wechat-mcp__fetch_messages_by_chat`

- **读取+发送**：message-composer, auto-replier
  - 工具：`mcp__wechat-mcp__fetch_messages_by_chat`, `mcp__wechat-mcp__reply_to_messages_by_chat`

### 模型选择

- **Sonnet 模型**：chat-summarizer, message-composer, chat-insights

  - 需要深度理解和复杂推理

- **Haiku 模型**：message-searcher, multi-chat-checker
  - 速度优先，任务相对简单

---

## 📝 注意事项

### 隐私和安全

- 所有子代理都在本地运行，不会上传聊天记录
- 消息内容仅用于当前任务，不会被存储
- 建议定期检查子代理的行为

### 使用建议

1. **首次使用**：先用只读的子代理（如 chat-summarizer）熟悉功能
2. **重要消息**：涉及重要决定时，建议用 message-composer 而非 auto-replier
3. **多轮对话**：可以在同一对话中连续使用多个子代理
4. **自定义调整**：可以编辑 `.claude/agents/` 下的 markdown 文件来调整子代理行为

### 局限性

- 子代理的理解依赖于获取的消息数量（默认 30-100 条）
- 对于很长的聊天历史，可能无法访问所有内容
- 表情、图片、语音等非文本内容可能无法完整分析
- 自动回复和消息撰写基于 AI 推理，请在发送前确认内容合适

---

## 🔧 自定义和扩展

### 修改现有子代理

编辑 `.claude/agents/` 目录下的对应 `.md` 文件：

```bash
# 例如，修改自动回复器的行为
vim .claude/agents/auto-replier.md
```

### 创建新的子代理

1. 在 `.claude/agents/` 创建新的 `.md` 文件
2. 添加 YAML frontmatter 定义名称、描述、工具等
3. 编写详细的系统提示词

参考现有子代理的格式和结构。

---

## 🆘 常见问题

**Q: 如何知道 Claude 选择了哪个子代理？**
A: Claude 会明确告诉你它使用了哪个子代理来完成任务。

**Q: 可以同时使用多个子代理吗？**
A: 可以，例如先用 chat-summarizer 了解情况，再用 message-composer 发送回复。

**Q: 子代理发送的消息可以撤回吗？**
A: 一旦发送就无法通过 Claude 撤回，请确保内容合适后再让子代理发送。

**Q: 如何禁用某个子代理？**
A: 删除或重命名对应的 `.md` 文件即可。

**Q: 子代理支持群聊吗？**
A: 是的，所有子代理都支持个人聊天和群聊。

---

## 📚 更多资源

- [WeChat-MCP 主项目文档](../README.md)
- [Claude Code 子代理文档](https://code.claude.com/docs/en/sub-agents.md)
- [MCP 协议说明](https://modelcontextprotocol.io/)

---

## 🙏 反馈和贡献

如果你有改进建议或发现问题：

1. 提交 Issue 到 GitHub 仓库
2. 分享你自定义的子代理
3. 帮助完善文档

祝你使用愉快！ 🎉
