import { useState, useEffect } from 'react'
import './App.css'

type Theme = 'light' | 'dark'
type Language = 'en' | 'zh'
type View = 'overview' | 'changelog'

interface Translations {
  hero: {
    title: string
    subtitle: string
    description: string
    getStarted: string
    learnMore: string
  }
  integration: {
    title: string
    description: string
  }
  painPoints: {
    title: string
    points: Array<{ title: string; description: string }>
  }
  benefits: {
    title: string
    points: Array<{ title: string; description: string }>
  }
  howItWorks: {
    title: string
    steps: Array<{ title: string; description: string }>
  }
  faqs: {
    title: string
    items: Array<{ question: string; answer: string }>
  }
  footer: {
    madeWith: string
  }
  changelog: {
    title: string
    subtitle: string
  }
}

const translations: Record<Language, Translations> = {
  en: {
    hero: {
      title: 'WeChat MCP',
      subtitle: 'Automate WeChat with AI',
      description: 'An MCP-compatible server that lets Claude and other AI assistants read and reply to WeChat messages on macOS using Accessibility APIs.',
      getStarted: 'Get Started',
      learnMore: 'View on GitHub'
    },
    integration: {
      title: 'Connect Claude Code to WeChat',
      description: 'Seamlessly integrate your AI assistant with WeChat. Enable intelligent conversation handling, automated responses, and context-aware messaging.'
    },
    painPoints: {
      title: 'The Problem',
      points: [
        {
          title: 'Manual messaging is time-consuming',
          description: 'Constantly switching between apps and manually responding to messages disrupts your workflow and productivity.'
        },
        {
          title: 'No programmatic WeChat access',
          description: 'WeChat doesn\'t provide official APIs for macOS, making automation nearly impossible without complex workarounds.'
        },
        {
          title: 'AI can\'t interact with WeChat',
          description: 'Modern AI assistants have no way to read or send messages in WeChat, limiting their usefulness for communication tasks.'
        }
      ]
    },
    benefits: {
      title: 'The Solution',
      points: [
        {
          title: 'AI-powered messaging',
          description: 'Let Claude and other AI assistants read, understand, and respond to your WeChat messages with natural, context-aware replies.'
        },
        {
          title: 'Seamless automation',
          description: 'Use the Model Context Protocol to integrate WeChat with any MCP-compatible AI client, enabling powerful automation workflows.'
        },
        {
          title: 'Full message history',
          description: 'Automatically scroll and fetch complete conversation history, giving AI the full context needed for intelligent responses.'
        },
        {
          title: 'Privacy-focused',
          description: 'Everything runs locally on your Mac using Accessibility APIs. No data is sent to external servers.'
        }
      ]
    },
    howItWorks: {
      title: 'How It Works',
      steps: [
        {
          title: '1. Install WeChat MCP',
          description: 'Install the WeChat MCP server from PyPI with pip install wechat-mcp-server. Then grant Accessibility permissions to Python in System Settings.'
        },
        {
          title: '2. Connect to Claude Code',
          description: 'Add the MCP server to your Claude Code configuration with a single command: claude mcp add wechat-mcp'
        },
        {
          title: '3. Start automating',
          description: 'Ask Claude to read messages, compose replies, or automate any WeChat task. The AI has full access to your conversations.'
        },
        {
          title: '4. Enjoy intelligent messaging',
          description: 'Let AI handle routine responses, summarize conversations, or help you manage multiple chats efficiently.'
        }
      ]
    },
    faqs: {
      title: 'Frequently Asked Questions',
      items: [
        {
          question: 'What is MCP?',
          answer: 'The Model Context Protocol (MCP) is an open standard that enables AI assistants to securely connect to external data sources and tools. WeChat MCP implements this protocol to give AI access to your WeChat messages.'
        },
        {
          question: 'Is my data safe?',
          answer: 'Yes! WeChat MCP runs entirely on your local Mac. It uses macOS Accessibility APIs to interact with WeChat. No messages or data are sent to external servers.'
        },
        {
          question: 'What macOS versions are supported?',
          answer: 'WeChat MCP works on macOS systems that support the Accessibility API. You need to grant Accessibility permissions to the Python process in System Settings → Privacy & Security.'
        },
        {
          question: 'Can I use it with other AI assistants?',
          answer: 'Yes! Any MCP-compatible client can use WeChat MCP. While Claude Code is the primary integration, the server supports stdio, HTTP, and SSE transports for flexibility.'
        },
        {
          question: 'Does it work with WeChat groups?',
          answer: 'Yes, WeChat MCP works with both individual contacts and group chats. You can fetch messages and send replies to any conversation.'
        }
      ]
    },
    footer: {
      madeWith: 'Built with the Model Context Protocol'
    },
    changelog: {
      title: 'Changelog',
      subtitle: 'Release notes for the WeChat MCP server.'
    }
  },
  zh: {
    hero: {
      title: 'WeChat MCP',
      subtitle: '用 AI 自动化微信',
      description: '将你的 Claude Code 和其他 MCP 客户端连接到微信。在 macOS 上通过模型上下文协议实现 AI 驱动的消息自动化。',
      getStarted: '开始使用',
      learnMore: '在 GitHub 查看'
    },
    integration: {
      title: '将 Claude Code 连接到微信',
      description: '无缝集成你的 AI 助手与微信。启用智能对话处理、自动回复和上下文感知消息。'
    },
    painPoints: {
      title: '痛点',
      points: [
        {
          title: '手动消息处理耗时',
          description: '在应用之间不断切换并手动回复消息会打断你的工作流程，降低生产力。'
        },
        {
          title: '无法程序化访问微信',
          description: '微信没有为 macOS 提供官方 API，没有复杂的变通方法几乎不可能实现自动化。'
        },
        {
          title: 'AI 无法与微信交互',
          description: '现代 AI 助手无法在微信中读取或发送消息，限制了它们在通信任务中的用处。'
        }
      ]
    },
    benefits: {
      title: '解决方案',
      points: [
        {
          title: 'AI 驱动的消息处理',
          description: '让 Claude 和其他 AI 助手阅读、理解并用自然、上下文感知的回复来响应你的微信消息。'
        },
        {
          title: '无缝自动化',
          description: '使用模型上下文协议将微信与任何兼容 MCP 的 AI 客户端集成，实现强大的自动化工作流程。'
        },
        {
          title: '完整消息历史',
          description: '自动滚动并获取完整的对话历史，为 AI 提供智能响应所需的完整上下文。'
        },
        {
          title: '注重隐私',
          description: '一切都在你的 Mac 上本地运行，使用辅助功能 API。没有数据发送到外部服务器。'
        }
      ]
    },
    howItWorks: {
      title: '工作原理',
      steps: [
        {
          title: '1. 安装 WeChat MCP',
          description: '通过 pip install wechat-mcp-server 从 PyPI 安装 WeChat MCP 服务器，然后在系统设置中为 Python 授予辅助功能权限。'
        },
        {
          title: '2. 连接到 Claude Code',
          description: '使用单个命令将 MCP 服务器添加到你的 Claude Code 配置：claude mcp add wechat-mcp'
        },
        {
          title: '3. 开始自动化',
          description: '让 Claude 阅读消息、撰写回复或自动化任何微信任务。AI 可以完全访问你的对话。'
        },
        {
          title: '4. 享受智能消息',
          description: '让 AI 处理常规响应、总结对话或帮助你高效管理多个聊天。'
        }
      ]
    },
    faqs: {
      title: '常见问题',
      items: [
        {
          question: '什么是 MCP？',
          answer: '模型上下文协议（MCP）是一个开放标准，使 AI 助手能够安全地连接到外部数据源和工具。WeChat MCP 实现了这个协议，让 AI 可以访问你的微信消息。'
        },
        {
          question: '我的数据安全吗？',
          answer: '是的！WeChat MCP 完全在你的本地 Mac 上运行。它使用 macOS 辅助功能 API 与微信交互。没有消息或数据发送到外部服务器。'
        },
        {
          question: '支持哪些 macOS 版本？',
          answer: 'WeChat MCP 适用于支持辅助功能 API 的 macOS 系统。你需要在系统设置 → 隐私与安全性中授予 Python 进程辅助功能权限。'
        },
        {
          question: '我可以与其他 AI 助手一起使用吗？',
          answer: '可以！任何兼容 MCP 的客户端都可以使用 WeChat MCP。虽然 Claude Code 是主要集成，但服务器支持 stdio、HTTP 和 SSE 传输以提供灵活性。'
        },
        {
          question: '它支持微信群组吗？',
          answer: '是的，WeChat MCP 适用于个人联系人和群聊。你可以获取消息并向任何对话发送回复。'
        }
      ]
    },
    footer: {
      madeWith: '使用模型上下文协议构建'
    },
    changelog: {
      title: '更新日志',
      subtitle: 'WeChat MCP 服务器的版本更新记录。'
    }
  }
}

function App() {
  const [theme, setTheme] = useState<Theme>('dark')
  const [language, setLanguage] = useState<Language>('en')
  const [stars, setStars] = useState<number | null>(null)
  const [view, setView] = useState<View>('overview')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    fetch('https://api.github.com/repos/BiboyQG/WeChat-MCP')
      .then(res => res.json())
      .then(data => setStars(data.stargazers_count))
      .catch(console.error)
  }, [])

  const toggleTheme = () => setTheme(prev => prev === 'light' ? 'dark' : 'light')
  const toggleLanguage = () => setLanguage(prev => prev === 'en' ? 'zh' : 'en')
  const changeView = (next: View) => {
    setView(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const t = translations[language]

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <img
              src="https://cdn-icons-png.flaticon.com/512/3938/3938101.png"
              alt="WeChat icon"
              className="logo-image"
            />
            <span className="logo-text">WeChat MCP</span>
          </div>

          <nav className="nav">
            <button
              className={`nav-link ${view === 'overview' ? 'nav-link-active' : ''}`}
              onClick={() => changeView('overview')}
            >
              {language === 'en' ? 'Overview' : '概览'}
            </button>
            <button
              className={`nav-link ${view === 'changelog' ? 'nav-link-active' : ''}`}
              onClick={() => changeView('changelog')}
            >
              {language === 'en' ? 'Changelog' : '更新日志'}
            </button>
          </nav>

          <div className="header-actions">
            <button className="icon-button" onClick={toggleLanguage} aria-label="Toggle language">
              {language === 'en' ? '中文' : 'EN'}
            </button>
            <button className="icon-button" onClick={toggleTheme} aria-label="Toggle theme">
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
            <a
              href="https://github.com/BiboyQG/WeChat-MCP"
              className="github-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg className="github-icon" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
              </svg>
              {stars !== null && <span className="stars-count">{stars}</span>}
            </a>
          </div>
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <div className="container hero-grid">
            <div className="hero-left">
              <p className="hero-pill">
                <span className="hero-pill-badge">New</span>
                <span>
                  {language === 'en'
                    ? 'v0.2.0 • New tools and packaging fixes on PyPI'
                    : 'v0.2.0 • PyPI 新增工具与安装修复'}
                </span>
              </p>
              <h1 className="hero-title">{t.hero.title}</h1>
              <p className="hero-subtitle">{t.hero.subtitle}</p>
              <p className="hero-description">{t.hero.description}</p>
              <div className="hero-meta">
                <span className="hero-tag">Python 3.12+</span>
                <span className="hero-tag">macOS · Accessibility</span>
                <span className="hero-tag">Model Context Protocol</span>
              </div>
              <div className="hero-actions">
                <a
                  href="https://github.com/BiboyQG/WeChat-MCP#readme"
                  className="button button-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t.hero.getStarted}
                </a>
                <a
                  href="https://github.com/BiboyQG/WeChat-MCP"
                  className="button button-secondary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t.hero.learnMore}
                </a>
              </div>
            </div>
            <div className="hero-right">
              <div className="hero-card">
                <div className="hero-card-header">
                  {language === 'en' ? 'Install via pip' : '通过 pip 安装'}
                </div>
                <pre className="code-snippet">
                  <code>pip install wechat-mcp-server</code>
                </pre>
                <p className="hero-card-meta">
                  {language === 'en'
                    ? 'Installs the wechat-mcp CLI and MCP server on your Mac.'
                    : '在你的 Mac 上安装 wechat-mcp CLI 和 MCP 服务器。'}
                </p>
              </div>
            </div>
          </div>
        </section>

        {view === 'overview' && (
          <>
            <section className="integration">
              <div className="container">
                <div className="integration-content">
                  <div className="integration-icon">
                    <div className="integration-icon-pill">
                      <span className="integration-icon-pill-label">MCP</span>
                      <span className="integration-icon-pill-separator">×</span>
                      <span>WeChat</span>
                    </div>
                  </div>
                  <div className="integration-text">
                    <h2>{t.integration.title}</h2>
                    <p>{t.integration.description}</p>
                  </div>
                </div>
              </div>
            </section>

            <section className="pain-points">
              <div className="container">
                <h2 className="section-title">{t.painPoints.title}</h2>
                <div className="grid">
                  {t.painPoints.points.map((point, index) => (
                    <div key={index} className="card">
                      <h3>{point.title}</h3>
                      <p>{point.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="benefits">
              <div className="container">
                <h2 className="section-title">{t.benefits.title}</h2>
                <div className="grid grid-2x2">
                  {t.benefits.points.map((point, index) => (
                    <div key={index} className="card card-highlight">
                      <h3>{point.title}</h3>
                      <p>{point.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="how-it-works">
              <div className="container">
                <h2 className="section-title">{t.howItWorks.title}</h2>
                <div className="steps">
                  {t.howItWorks.steps.map((step, index) => (
                    <div key={index} className="step">
                      <div className="step-content">
                        <h3>{step.title}</h3>
                        <p>{step.description}</p>
                      </div>
                      {index < t.howItWorks.steps.length - 1 && (
                        <div className="step-connector"></div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="faqs">
              <div className="container">
                <h2 className="section-title">{t.faqs.title}</h2>
                <div className="faq-list">
                  {t.faqs.items.map((item, index) => (
                    <details key={index} className="faq-item">
                      <summary>{item.question}</summary>
                      <p>{item.answer}</p>
                    </details>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}

        {view === 'changelog' && (
          <section className="changelog">
            <div className="container">
              <header className="changelog-header">
                <h2 className="section-title">{t.changelog.title}</h2>
                <p className="changelog-subtitle">{t.changelog.subtitle}</p>
              </header>

              <article className="release-card">
                <header className="release-header">
                  <div>
                    <div className="release-version">v0.2.0</div>
                    <div className="release-label">
                      {language === 'en'
                        ? 'Packaging fix and expanded toolset'
                        : '安装修复与工具扩展'}
                    </div>
                  </div>
                  <div className="release-badges">
                    <span className="release-pill">PyPI • wechat-mcp-server</span>
                    <span className="release-pill release-pill-soft">
                      {language === 'en' ? 'Alpha' : '测试版'}
                    </span>
                  </div>
                </header>

                <p className="release-summary">
                  {language === 'en'
                    ? 'v0.2.0 adds contact and Moments automation while fixing the wheel packaging issue so installed wechat-mcp commands work correctly after pip install.'
                    : 'v0.2.0 新增了联系人与朋友圈自动化能力，并修复了 wheel 打包问题，使通过 pip 安装后的 wechat-mcp 命令可以正常运行。'}
                </p>

                <div className="release-install">
                  <div className="release-install-label">
                    {language === 'en' ? 'Upgrade' : '升级'}
                  </div>
                  <pre className="code-snippet">
                    <code>pip install -U wechat-mcp-server</code>
                  </pre>
                </div>

                <div className="release-section">
                  <h3>{language === 'en' ? 'Highlights' : '亮点'}</h3>
                  <ul>
                    <li>
                      {language === 'en'
                        ? 'Added add_contact_by_wechat_id to search a WeChat ID, open the add-contact flow, and send a friend request with optional remark, tags, and privacy settings.'
                        : '新增 add_contact_by_wechat_id，可按微信号搜索联系人、打开加好友流程，并携带备注、标签和隐私选项发送好友申请。'}
                    </li>
                    <li>
                      {language === 'en'
                        ? 'Added publish_moment_without_media for text-only Moments posts, including a draft-only mode with publish=False.'
                        : '新增 publish_moment_without_media，可发布纯文字朋友圈，并支持通过 publish=False 仅生成草稿。'}
                    </li>
                    <li>
                      {language === 'en'
                        ? 'Fixed the published wheel so pip installs now include the importable wechat_mcp package and a working wechat-mcp CLI.'
                        : '修复已发布 wheel 的内容，使 pip 安装后会正确包含可导入的 wechat_mcp 包和可用的 wechat-mcp 命令。'}
                    </li>
                    <li>
                      {language === 'en'
                        ? 'Improved search clearing, chat selection reliability, and Moments composer timing for more stable automation.'
                        : '改进搜索框清理、聊天选择稳定性和朋友圈编辑器交互时序，提升自动化可靠性。'}
                    </li>
                  </ul>
                </div>

                <div className="release-section">
                  <h3>{language === 'en' ? 'Since v0.1.0' : '相较 v0.1.0'}</h3>
                  <ul>
                    <li>
                      {language === 'en'
                        ? 'Added two user-facing MCP tools: add_contact_by_wechat_id(...) and publish_moment_without_media(...).'
                        : '新增两个面向用户的 MCP 工具：add_contact_by_wechat_id(...) 与 publish_moment_without_media(...).'}
                    </li>
                    <li>
                      {language === 'en'
                        ? 'Expanded setup documentation for Claude Desktop, Codex, and local uv-based development.'
                        : '补充了 Claude Desktop、Codex 与本地 uv 开发的配置文档。'}
                    </li>
                    <li>
                      {language === 'en'
                        ? 'Split smoke scripts by tool and cleaned up test and documentation coverage around the new flows.'
                        : '按工具拆分了 smoke 脚本，并补充了围绕新流程的测试与文档整理。'}
                    </li>
                  </ul>
                </div>
              </article>

              <article className="release-card">
                <header className="release-header">
                  <div>
                    <div className="release-version">v0.1.0</div>
                    <div className="release-label">
                      {language === 'en'
                        ? 'Initial public release'
                        : '首次公开发布'}
                    </div>
                  </div>
                  <div className="release-badges">
                    <span className="release-pill">PyPI • wechat-mcp-server</span>
                    <span className="release-pill release-pill-soft">
                      {language === 'en' ? 'Alpha' : '测试版'}
                    </span>
                  </div>
                </header>

                <p className="release-summary">
                  {language === 'en'
                    ? 'Initial public release of the WeChat MCP server, exposing an MCP-compatible interface for reading and replying to WeChat messages on macOS via Accessibility APIs and screen capture.'
                    : 'WeChat MCP 服务器的首次公开版本，在 macOS 上通过辅助功能 API 和截屏提供读取与回复微信消息的 MCP 接口。'}
                </p>

                <div className="release-install">
                  <div className="release-install-label">
                    {language === 'en' ? 'Install' : '安装'}
                  </div>
                  <pre className="code-snippet">
                    <code>pip install wechat-mcp-server</code>
                  </pre>
                </div>

                <div className="release-section">
                  <h3>Highlights</h3>
                  <ul>
                    <li>
                      MCP server exposing WeChat automation tools over stdio, streamable HTTP, or SSE transports.
                    </li>
                    <li>
                      End-to-end macOS Accessibility integration to locate chats, read message history, and send replies.
                    </li>
                    <li>
                      Screenshot-based sender classification to distinguish messages from you vs. others.
                    </li>
                    <li>
                      Structured logging to both terminal and rotating log files.
                    </li>
                    <li>
                      First official PyPI release of <code>wechat-mcp-server</code>.
                    </li>
                  </ul>
                </div>

                <div className="release-section">
                  <h3>Features</h3>
                  <ul>
                    <li>
                      <strong>MCP server and CLI</strong> via the <code>wechat-mcp</code> console script with stdio, HTTP, and SSE transports.
                    </li>
                    <li>
                      <strong>WeChat tools</strong> for fetching messages by chat and replying to messages, with smart handling of ambiguous chat names.
                    </li>
                    <li>
                      <strong>macOS Accessibility helpers</strong> that drive the WeChat UI, scroll message history, and capture screenshots for sender classification.
                    </li>
                    <li>
                      <strong>Logging and observability</strong> with configurable log directory and verbose debug mode for MCP and HTTP traffic.
                    </li>
                  </ul>
                </div>

                <div className="release-section">
                  <h3>Requirements</h3>
                  <ul>
                    <li>macOS with Accessibility and screen capture permissions granted to your terminal / Python.</li>
                    <li>WeChat installed and running on macOS.</li>
                    <li>Python 3.12+ with <code>pyobjc</code>, <code>Pillow</code>, and <code>mcp[cli]</code> dependencies.</li>
                  </ul>
                </div>

                <div className="release-section">
                  <h3>Known limitations</h3>
                  <ul>
                    <li>Tested only on the standard macOS WeChat client and default Accessibility structure.</li>
                    <li>Sender classification relies on color heuristics and may misclassify in unusual themes or display conditions.</li>
                    <li>Focuses on English / Latin chat names; broader localization is planned.</li>
                    <li>Marked as alpha; APIs and behavior may change in future versions.</li>
                  </ul>
                </div>
              </article>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <div className="container">
          <p>{t.footer.madeWith}</p>
        </div>
      </footer>
    </div>
  )
}

export default App
