import { useState, useEffect } from 'react'
import './App.css'

type Theme = 'light' | 'dark'
type Language = 'en' | 'zh'

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
}

const translations: Record<Language, Translations> = {
  en: {
    hero: {
      title: 'WeChat MCP',
      subtitle: 'Automate WeChat with AI',
      description: 'Connect your Claude Code and other MCP clients to WeChat. Enable AI-powered messaging automation on macOS with the Model Context Protocol.',
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
          description: 'Clone the repository and set up the MCP server using uv. Grant Accessibility permissions to Python in System Settings.'
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
          description: '克隆仓库并使用 uv 设置 MCP 服务器。在系统设置中授予 Python 辅助功能权限。'
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
    }
  }
}

function App() {
  const [theme, setTheme] = useState<Theme>('dark')
  const [language, setLanguage] = useState<Language>('en')
  const [stars, setStars] = useState<number | null>(null)

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

  const t = translations[language]

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <img src="/WeChat-MCP/wechat.png" alt="WeChat" className="logo-image" />
            <span className="logo-text">WeChat MCP</span>
          </div>

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
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
              </svg>
              {stars !== null && <span className="stars-count">{stars}</span>}
            </a>
          </div>
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <div className="container">
            <h1 className="hero-title">{t.hero.title}</h1>
            <p className="hero-subtitle">{t.hero.subtitle}</p>
            <p className="hero-description">{t.hero.description}</p>
            <div className="hero-actions">
              <a href="https://github.com/BiboyQG/WeChat-MCP#readme" className="button button-primary" target="_blank" rel="noopener noreferrer">
                {t.hero.getStarted}
              </a>
              <a href="https://github.com/BiboyQG/WeChat-MCP" className="button button-secondary" target="_blank" rel="noopener noreferrer">
                {t.hero.learnMore}
              </a>
            </div>
          </div>
        </section>

        <section className="integration">
          <div className="container">
            <div className="integration-content">
              <div className="integration-icon">
                <img
                  src="https://xaviercollantes.dev/articles/claude-cheatsheet"
                  alt="Claude Code"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent) {
                      parent.innerHTML = '<div class="icon-placeholder">Claude Code</div>';
                    }
                  }}
                />
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
