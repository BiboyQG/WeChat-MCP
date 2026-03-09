import { useState, useEffect, useRef, useCallback } from 'react'
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
    points: Array<{ title: string; description: string; icon: string }>
  }
  benefits: {
    title: string
    points: Array<{ title: string; description: string; icon: string }>
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
          description: 'Constantly switching between apps and manually responding to messages disrupts your workflow and productivity.',
          icon: '\u23f1'
        },
        {
          title: 'No programmatic WeChat access',
          description: 'WeChat doesn\'t provide official APIs for macOS, making automation nearly impossible without complex workarounds.',
          icon: '\ud83d\udd12'
        },
        {
          title: 'AI can\'t interact with WeChat',
          description: 'Modern AI assistants have no way to read or send messages in WeChat, limiting their usefulness for communication tasks.',
          icon: '\ud83e\udd16'
        }
      ]
    },
    benefits: {
      title: 'The Solution',
      points: [
        {
          title: 'AI-powered messaging',
          description: 'Let Claude and other AI assistants read, understand, and respond to your WeChat messages with natural, context-aware replies.',
          icon: '\u2728'
        },
        {
          title: 'Seamless automation',
          description: 'Use the Model Context Protocol to integrate WeChat with any MCP-compatible AI client, enabling powerful automation workflows.',
          icon: '\u26a1'
        },
        {
          title: 'Full message history',
          description: 'Automatically scroll and fetch complete conversation history, giving AI the full context needed for intelligent responses.',
          icon: '\ud83d\udcac'
        },
        {
          title: 'Privacy-focused',
          description: 'Everything runs locally on your Mac using Accessibility APIs. No data is sent to external servers.',
          icon: '\ud83d\udee1\ufe0f'
        }
      ]
    },
    howItWorks: {
      title: 'How It Works',
      steps: [
        {
          title: 'Install WeChat MCP',
          description: 'Install the WeChat MCP server from PyPI with pip install wechat-mcp-server. Then grant Accessibility permissions to Python in System Settings.'
        },
        {
          title: 'Connect to Claude Code',
          description: 'Add the MCP server to your Claude Code configuration with a single command: claude mcp add wechat-mcp'
        },
        {
          title: 'Start automating',
          description: 'Ask Claude to read messages, compose replies, or automate any WeChat task. The AI has full access to your conversations.'
        },
        {
          title: 'Enjoy intelligent messaging',
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
          answer: 'WeChat MCP works on macOS systems that support the Accessibility API. You need to grant Accessibility permissions to the Python process in System Settings \u2192 Privacy & Security.'
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
      subtitle: '\u7528 AI \u81ea\u52a8\u5316\u5fae\u4fe1',
      description: '\u5c06\u4f60\u7684 Claude Code \u548c\u5176\u4ed6 MCP \u5ba2\u6237\u7aef\u8fde\u63a5\u5230\u5fae\u4fe1\u3002\u5728 macOS \u4e0a\u901a\u8fc7\u6a21\u578b\u4e0a\u4e0b\u6587\u534f\u8bae\u5b9e\u73b0 AI \u9a71\u52a8\u7684\u6d88\u606f\u81ea\u52a8\u5316\u3002',
      getStarted: '\u5f00\u59cb\u4f7f\u7528',
      learnMore: '\u5728 GitHub \u67e5\u770b'
    },
    integration: {
      title: '\u5c06 Claude Code \u8fde\u63a5\u5230\u5fae\u4fe1',
      description: '\u65e0\u7f1d\u96c6\u6210\u4f60\u7684 AI \u52a9\u624b\u4e0e\u5fae\u4fe1\u3002\u542f\u7528\u667a\u80fd\u5bf9\u8bdd\u5904\u7406\u3001\u81ea\u52a8\u56de\u590d\u548c\u4e0a\u4e0b\u6587\u611f\u77e5\u6d88\u606f\u3002'
    },
    painPoints: {
      title: '\u75db\u70b9',
      points: [
        {
          title: '\u624b\u52a8\u6d88\u606f\u5904\u7406\u8017\u65f6',
          description: '\u5728\u5e94\u7528\u4e4b\u95f4\u4e0d\u65ad\u5207\u6362\u5e76\u624b\u52a8\u56de\u590d\u6d88\u606f\u4f1a\u6253\u65ad\u4f60\u7684\u5de5\u4f5c\u6d41\u7a0b\uff0c\u964d\u4f4e\u751f\u4ea7\u529b\u3002',
          icon: '\u23f1'
        },
        {
          title: '\u65e0\u6cd5\u7a0b\u5e8f\u5316\u8bbf\u95ee\u5fae\u4fe1',
          description: '\u5fae\u4fe1\u6ca1\u6709\u4e3a macOS \u63d0\u4f9b\u5b98\u65b9 API\uff0c\u6ca1\u6709\u590d\u6742\u7684\u53d8\u901a\u65b9\u6cd5\u51e0\u4e4e\u4e0d\u53ef\u80fd\u5b9e\u73b0\u81ea\u52a8\u5316\u3002',
          icon: '\ud83d\udd12'
        },
        {
          title: 'AI \u65e0\u6cd5\u4e0e\u5fae\u4fe1\u4ea4\u4e92',
          description: '\u73b0\u4ee3 AI \u52a9\u624b\u65e0\u6cd5\u5728\u5fae\u4fe1\u4e2d\u8bfb\u53d6\u6216\u53d1\u9001\u6d88\u606f\uff0c\u9650\u5236\u4e86\u5b83\u4eec\u5728\u901a\u4fe1\u4efb\u52a1\u4e2d\u7684\u7528\u5904\u3002',
          icon: '\ud83e\udd16'
        }
      ]
    },
    benefits: {
      title: '\u89e3\u51b3\u65b9\u6848',
      points: [
        {
          title: 'AI \u9a71\u52a8\u7684\u6d88\u606f\u5904\u7406',
          description: '\u8ba9 Claude \u548c\u5176\u4ed6 AI \u52a9\u624b\u9605\u8bfb\u3001\u7406\u89e3\u5e76\u7528\u81ea\u7136\u3001\u4e0a\u4e0b\u6587\u611f\u77e5\u7684\u56de\u590d\u6765\u54cd\u5e94\u4f60\u7684\u5fae\u4fe1\u6d88\u606f\u3002',
          icon: '\u2728'
        },
        {
          title: '\u65e0\u7f1d\u81ea\u52a8\u5316',
          description: '\u4f7f\u7528\u6a21\u578b\u4e0a\u4e0b\u6587\u534f\u8bae\u5c06\u5fae\u4fe1\u4e0e\u4efb\u4f55\u517c\u5bb9 MCP \u7684 AI \u5ba2\u6237\u7aef\u96c6\u6210\uff0c\u5b9e\u73b0\u5f3a\u5927\u7684\u81ea\u52a8\u5316\u5de5\u4f5c\u6d41\u7a0b\u3002',
          icon: '\u26a1'
        },
        {
          title: '\u5b8c\u6574\u6d88\u606f\u5386\u53f2',
          description: '\u81ea\u52a8\u6eda\u52a8\u5e76\u83b7\u53d6\u5b8c\u6574\u7684\u5bf9\u8bdd\u5386\u53f2\uff0c\u4e3a AI \u63d0\u4f9b\u667a\u80fd\u54cd\u5e94\u6240\u9700\u7684\u5b8c\u6574\u4e0a\u4e0b\u6587\u3002',
          icon: '\ud83d\udcac'
        },
        {
          title: '\u6ce8\u91cd\u9690\u79c1',
          description: '\u4e00\u5207\u90fd\u5728\u4f60\u7684 Mac \u4e0a\u672c\u5730\u8fd0\u884c\uff0c\u4f7f\u7528\u8f85\u52a9\u529f\u80fd API\u3002\u6ca1\u6709\u6570\u636e\u53d1\u9001\u5230\u5916\u90e8\u670d\u52a1\u5668\u3002',
          icon: '\ud83d\udee1\ufe0f'
        }
      ]
    },
    howItWorks: {
      title: '\u5de5\u4f5c\u539f\u7406',
      steps: [
        {
          title: '\u5b89\u88c5 WeChat MCP',
          description: '\u901a\u8fc7 pip install wechat-mcp-server \u4ece PyPI \u5b89\u88c5 WeChat MCP \u670d\u52a1\u5668\uff0c\u7136\u540e\u5728\u7cfb\u7edf\u8bbe\u7f6e\u4e2d\u4e3a Python \u6388\u4e88\u8f85\u52a9\u529f\u80fd\u6743\u9650\u3002'
        },
        {
          title: '\u8fde\u63a5\u5230 Claude Code',
          description: '\u4f7f\u7528\u5355\u4e2a\u547d\u4ee4\u5c06 MCP \u670d\u52a1\u5668\u6dfb\u52a0\u5230\u4f60\u7684 Claude Code \u914d\u7f6e\uff1aclaude mcp add wechat-mcp'
        },
        {
          title: '\u5f00\u59cb\u81ea\u52a8\u5316',
          description: '\u8ba9 Claude \u9605\u8bfb\u6d88\u606f\u3001\u64b0\u5199\u56de\u590d\u6216\u81ea\u52a8\u5316\u4efb\u4f55\u5fae\u4fe1\u4efb\u52a1\u3002AI \u53ef\u4ee5\u5b8c\u5168\u8bbf\u95ee\u4f60\u7684\u5bf9\u8bdd\u3002'
        },
        {
          title: '\u4eab\u53d7\u667a\u80fd\u6d88\u606f',
          description: '\u8ba9 AI \u5904\u7406\u5e38\u89c4\u54cd\u5e94\u3001\u603b\u7ed3\u5bf9\u8bdd\u6216\u5e2e\u52a9\u4f60\u9ad8\u6548\u7ba1\u7406\u591a\u4e2a\u804a\u5929\u3002'
        }
      ]
    },
    faqs: {
      title: '\u5e38\u89c1\u95ee\u9898',
      items: [
        {
          question: '\u4ec0\u4e48\u662f MCP\uff1f',
          answer: '\u6a21\u578b\u4e0a\u4e0b\u6587\u534f\u8bae\uff08MCP\uff09\u662f\u4e00\u4e2a\u5f00\u653e\u6807\u51c6\uff0c\u4f7f AI \u52a9\u624b\u80fd\u591f\u5b89\u5168\u5730\u8fde\u63a5\u5230\u5916\u90e8\u6570\u636e\u6e90\u548c\u5de5\u5177\u3002WeChat MCP \u5b9e\u73b0\u4e86\u8fd9\u4e2a\u534f\u8bae\uff0c\u8ba9 AI \u53ef\u4ee5\u8bbf\u95ee\u4f60\u7684\u5fae\u4fe1\u6d88\u606f\u3002'
        },
        {
          question: '\u6211\u7684\u6570\u636e\u5b89\u5168\u5417\uff1f',
          answer: '\u662f\u7684\uff01WeChat MCP \u5b8c\u5168\u5728\u4f60\u7684\u672c\u5730 Mac \u4e0a\u8fd0\u884c\u3002\u5b83\u4f7f\u7528 macOS \u8f85\u52a9\u529f\u80fd API \u4e0e\u5fae\u4fe1\u4ea4\u4e92\u3002\u6ca1\u6709\u6d88\u606f\u6216\u6570\u636e\u53d1\u9001\u5230\u5916\u90e8\u670d\u52a1\u5668\u3002'
        },
        {
          question: '\u652f\u6301\u54ea\u4e9b macOS \u7248\u672c\uff1f',
          answer: 'WeChat MCP \u9002\u7528\u4e8e\u652f\u6301\u8f85\u52a9\u529f\u80fd API \u7684 macOS \u7cfb\u7edf\u3002\u4f60\u9700\u8981\u5728\u7cfb\u7edf\u8bbe\u7f6e \u2192 \u9690\u79c1\u4e0e\u5b89\u5168\u6027\u4e2d\u6388\u4e88 Python \u8fdb\u7a0b\u8f85\u52a9\u529f\u80fd\u6743\u9650\u3002'
        },
        {
          question: '\u6211\u53ef\u4ee5\u4e0e\u5176\u4ed6 AI \u52a9\u624b\u4e00\u8d77\u4f7f\u7528\u5417\uff1f',
          answer: '\u53ef\u4ee5\uff01\u4efb\u4f55\u517c\u5bb9 MCP \u7684\u5ba2\u6237\u7aef\u90fd\u53ef\u4ee5\u4f7f\u7528 WeChat MCP\u3002\u867d\u7136 Claude Code \u662f\u4e3b\u8981\u96c6\u6210\uff0c\u4f46\u670d\u52a1\u5668\u652f\u6301 stdio\u3001HTTP \u548c SSE \u4f20\u8f93\u4ee5\u63d0\u4f9b\u7075\u6d3b\u6027\u3002'
        },
        {
          question: '\u5b83\u652f\u6301\u5fae\u4fe1\u7fa4\u7ec4\u5417\uff1f',
          answer: '\u662f\u7684\uff0cWeChat MCP \u9002\u7528\u4e8e\u4e2a\u4eba\u8054\u7cfb\u4eba\u548c\u7fa4\u804a\u3002\u4f60\u53ef\u4ee5\u83b7\u53d6\u6d88\u606f\u5e76\u5411\u4efb\u4f55\u5bf9\u8bdd\u53d1\u9001\u56de\u590d\u3002'
        }
      ]
    },
    footer: {
      madeWith: '\u4f7f\u7528\u6a21\u578b\u4e0a\u4e0b\u6587\u534f\u8bae\u6784\u5efa'
    },
    changelog: {
      title: '\u66f4\u65b0\u65e5\u5fd7',
      subtitle: 'WeChat MCP \u670d\u52a1\u5668\u7684\u7248\u672c\u66f4\u65b0\u8bb0\u5f55\u3002'
    }
  }
}

function Card3D({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [transform, setTransform] = useState('')
  const [glare, setGlare] = useState({ x: 50, y: 50, opacity: 0 })

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current
    if (!card) return
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    const rotateX = ((y - centerY) / centerY) * -12
    const rotateY = ((x - centerX) / centerX) * 12

    setTransform(`perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.03, 1.03, 1.03)`)
    setGlare({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
      opacity: 0.15,
    })
  }, [])

  const handleMouseLeave = useCallback(() => {
    setTransform('perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)')
    setGlare({ x: 50, y: 50, opacity: 0 })
  }, [])

  return (
    <div
      ref={cardRef}
      className={`card-3d ${className}`}
      style={{ transform }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <div
        className="card-3d-glare"
        style={{
          background: `radial-gradient(circle at ${glare.x}% ${glare.y}%, rgba(255,255,255,${glare.opacity}), transparent 60%)`,
        }}
      />
      {children}
    </div>
  )
}

function CopyButton({ text, language }: { text: string; language: Language }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <button className="copy-button" onClick={handleCopy} aria-label="Copy to clipboard">
      {copied ? (language === 'en' ? 'Copied!' : '\u5df2\u590d\u5236\uff01') : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  )
}

function App() {
  const [theme, setTheme] = useState<Theme>('dark')
  const [language, setLanguage] = useState<Language>('en')
  const [stars, setStars] = useState<number | null>(null)
  const [view, setView] = useState<View>('overview')
  const [showPreviousReleases, setShowPreviousReleases] = useState(false)
  const [openFaqs, setOpenFaqs] = useState<Set<number>>(new Set())

  const toggleFaq = (index: number) => {
    setOpenFaqs(prev => {
      const next = new Set(prev)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

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
      {/* Ambient background blobs */}
      <div className="ambient-bg" aria-hidden="true">
        <div className="ambient-blob ambient-blob-1" />
        <div className="ambient-blob ambient-blob-2" />
        <div className="ambient-blob ambient-blob-3" />
      </div>

      <header className="header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon-wrap">
              <img
                src="https://cdn-icons-png.flaticon.com/512/3938/3938101.png"
                alt="WeChat icon"
                className="logo-image"
              />
            </div>
            <span className="logo-text">WeChat MCP</span>
          </div>

          <nav className="nav">
            <button
              className={`nav-link ${view === 'overview' ? 'nav-link-active' : ''}`}
              onClick={() => changeView('overview')}
            >
              {language === 'en' ? 'Overview' : '\u6982\u89c8'}
            </button>
            <button
              className={`nav-link ${view === 'changelog' ? 'nav-link-active' : ''}`}
              onClick={() => changeView('changelog')}
            >
              {language === 'en' ? 'Changelog' : '\u66f4\u65b0\u65e5\u5fd7'}
            </button>
          </nav>

          <div className="header-actions">
            <button className="icon-button" onClick={toggleLanguage} aria-label="Toggle language">
              {language === 'en' ? '\u4e2d\u6587' : 'EN'}
            </button>
            <button className="icon-button theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
              <span className="theme-icon">{theme === 'light' ? '\ud83c\udf19' : '\u2600\ufe0f'}</span>
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
              {stars !== null && <span className="stars-count">{stars.toLocaleString()}</span>}
            </a>
          </div>
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <div className="container hero-grid">
            <div className="hero-left">
              <p className="hero-pill">
                <span className="hero-pill-dot" />
                <span>
                  {language === 'en'
                    ? 'v0.2.0 \u2014 New tools and packaging fixes'
                    : 'v0.2.0 \u2014 \u65b0\u589e\u5de5\u5177\u4e0e\u5b89\u88c5\u4fee\u590d'}
                </span>
              </p>
              <h1 className="hero-title">{t.hero.title}</h1>
              <p className="hero-subtitle">{t.hero.subtitle}</p>
              <p className="hero-description">{t.hero.description}</p>
              <div className="hero-meta">
                <span className="hero-tag">Python 3.12+</span>
                <span className="hero-tag">macOS</span>
                <span className="hero-tag">MCP</span>
              </div>
              <div className="hero-actions">
                <a
                  href="https://github.com/BiboyQG/WeChat-MCP#readme"
                  className="button button-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t.hero.getStarted}
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
                  </svg>
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
              <Card3D className="hero-card">
                <div className="hero-card-header">
                  <div className="terminal-dots">
                    <span className="dot dot-red" />
                    <span className="dot dot-yellow" />
                    <span className="dot dot-green" />
                  </div>
                  <span className="hero-card-title">
                    {language === 'en' ? 'Terminal' : '\u7ec8\u7aef'}
                  </span>
                </div>
                <div className="code-block">
                  <div className="code-line">
                    <span className="code-prompt">$</span>
                    <code>pip install wechat-mcp-server</code>
                    <CopyButton text="pip install wechat-mcp-server" language={language} />
                  </div>
                </div>
                <div className="code-block code-block-secondary">
                  <div className="code-line">
                    <span className="code-prompt">$</span>
                    <code>claude mcp add wechat-mcp</code>
                    <CopyButton text="claude mcp add wechat-mcp" language={language} />
                  </div>
                </div>
                <p className="hero-card-meta">
                  {language === 'en'
                    ? 'Two commands. That\u2019s all you need.'
                    : '\u4e24\u6761\u547d\u4ee4\uff0c\u5c31\u8fd9\u4e48\u7b80\u5355\u3002'}
                </p>
              </Card3D>
            </div>
          </div>
        </section>

        {view === 'overview' && (
          <>
            <section className="integration">
              <div className="container">
                <div className="integration-content">
                  <div className="integration-visual">
                    <div className="integration-node integration-node-mcp">
                      <span>MCP</span>
                    </div>
                    <div className="integration-connector">
                      <div className="integration-connector-line" />
                      <div className="integration-connector-pulse" />
                    </div>
                    <div className="integration-node integration-node-wechat">
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
                      <div className="card-icon">{point.icon}</div>
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
                      <div className="card-icon">{point.icon}</div>
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
                      <div className="step-number">{index + 1}</div>
                      <div className="step-content">
                        <h3>{step.title}</h3>
                        <p>{step.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="faqs">
              <div className="container">
                <h2 className="section-title">{t.faqs.title}</h2>
                <div className="faq-list">
                  {t.faqs.items.map((item, index) => {
                    const isOpen = openFaqs.has(index)
                    return (
                      <div key={index} className={`faq-item ${isOpen ? 'faq-item-open' : ''}`}>
                        <button className="faq-summary" onClick={() => toggleFaq(index)}>
                          <span>{item.question}</span>
                          <span className="faq-icon">+</span>
                        </button>
                        <div className="faq-panel" aria-hidden={!isOpen}>
                          <div className="faq-panel-inner">
                            <p>{item.answer}</p>
                          </div>
                        </div>
                      </div>
                    )
                  })}
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

              <div className="release-stack">
                <article className="release-card">
                  <header className="release-header">
                    <div>
                      <div className="release-version">v0.2.0</div>
                      <div className="release-label">
                        {language === 'en'
                          ? 'Packaging fix and expanded toolset'
                          : '\u5b89\u88c5\u4fee\u590d\u4e0e\u5de5\u5177\u6269\u5c55'}
                      </div>
                    </div>
                    <div className="release-badges">
                      <span className="release-pill">PyPI</span>
                      <span className="release-pill release-pill-soft">
                        {language === 'en' ? 'Alpha' : '\u6d4b\u8bd5\u7248'}
                      </span>
                    </div>
                  </header>

                  <p className="release-summary">
                    {language === 'en'
                      ? 'v0.2.0 adds contact and Moments automation while fixing the wheel packaging issue so installed wechat-mcp commands work correctly after pip install.'
                      : 'v0.2.0 \u65b0\u589e\u4e86\u8054\u7cfb\u4eba\u4e0e\u670b\u53cb\u5708\u81ea\u52a8\u5316\u80fd\u529b\uff0c\u5e76\u4fee\u590d\u4e86 wheel \u6253\u5305\u95ee\u9898\uff0c\u4f7f\u901a\u8fc7 pip \u5b89\u88c5\u540e\u7684 wechat-mcp \u547d\u4ee4\u53ef\u4ee5\u6b63\u5e38\u8fd0\u884c\u3002'}
                  </p>

                  <div className="release-install">
                    <div className="release-install-label">
                      {language === 'en' ? 'Upgrade' : '\u5347\u7ea7'}
                    </div>
                    <pre className="code-snippet">
                      <code>pip install -U wechat-mcp-server</code>
                    </pre>
                  </div>

                  <div className="release-section">
                    <h3>{language === 'en' ? 'Highlights' : '\u4eae\u70b9'}</h3>
                    <ul>
                      <li>
                        {language === 'en'
                          ? 'Added add_contact_by_wechat_id to search a WeChat ID, open the add-contact flow, and send a friend request with optional remark, tags, and privacy settings.'
                          : '\u65b0\u589e add_contact_by_wechat_id\uff0c\u53ef\u6309\u5fae\u4fe1\u53f7\u641c\u7d22\u8054\u7cfb\u4eba\u3001\u6253\u5f00\u52a0\u597d\u53cb\u6d41\u7a0b\uff0c\u5e76\u643a\u5e26\u5907\u6ce8\u3001\u6807\u7b7e\u548c\u9690\u79c1\u9009\u9879\u53d1\u9001\u597d\u53cb\u7533\u8bf7\u3002'}
                      </li>
                      <li>
                        {language === 'en'
                          ? 'Added publish_moment_without_media for text-only Moments posts, including a draft-only mode with publish=False.'
                          : '\u65b0\u589e publish_moment_without_media\uff0c\u53ef\u53d1\u5e03\u7eaf\u6587\u5b57\u670b\u53cb\u5708\uff0c\u5e76\u652f\u6301\u901a\u8fc7 publish=False \u4ec5\u751f\u6210\u8349\u7a3f\u3002'}
                      </li>
                      <li>
                        {language === 'en'
                          ? 'Fixed the published wheel so pip installs now include the importable wechat_mcp package and a working wechat-mcp CLI.'
                          : '\u4fee\u590d\u5df2\u53d1\u5e03 wheel \u7684\u5185\u5bb9\uff0c\u4f7f pip \u5b89\u88c5\u540e\u4f1a\u6b63\u786e\u5305\u542b\u53ef\u5bfc\u5165\u7684 wechat_mcp \u5305\u548c\u53ef\u7528\u7684 wechat-mcp \u547d\u4ee4\u3002'}
                      </li>
                      <li>
                        {language === 'en'
                          ? 'Improved search clearing, chat selection reliability, and Moments composer timing for more stable automation.'
                          : '\u6539\u8fdb\u641c\u7d22\u6846\u6e05\u7406\u3001\u804a\u5929\u9009\u62e9\u7a33\u5b9a\u6027\u548c\u670b\u53cb\u5708\u7f16\u8f91\u5668\u4ea4\u4e92\u65f6\u5e8f\uff0c\u63d0\u5347\u81ea\u52a8\u5316\u53ef\u9760\u6027\u3002'}
                      </li>
                    </ul>
                  </div>

                  <div className="release-section">
                    <h3>{language === 'en' ? 'Since v0.1.0' : '\u76f8\u8f83 v0.1.0'}</h3>
                    <ul>
                      <li>
                        {language === 'en'
                          ? 'Added two user-facing MCP tools: add_contact_by_wechat_id(...) and publish_moment_without_media(...).'
                          : '\u65b0\u589e\u4e24\u4e2a\u9762\u5411\u7528\u6237\u7684 MCP \u5de5\u5177\uff1aadd_contact_by_wechat_id(...) \u4e0e publish_moment_without_media(...).'}
                      </li>
                      <li>
                        {language === 'en'
                          ? 'Expanded setup documentation for Claude Desktop, Codex, and local uv-based development.'
                          : '\u8865\u5145\u4e86 Claude Desktop\u3001Codex \u4e0e\u672c\u5730 uv \u5f00\u53d1\u7684\u914d\u7f6e\u6587\u6863\u3002'}
                      </li>
                      <li>
                        {language === 'en'
                          ? 'Split smoke scripts by tool and cleaned up test and documentation coverage around the new flows.'
                          : '\u6309\u5de5\u5177\u62c6\u5206\u4e86 smoke \u811a\u672c\uff0c\u5e76\u8865\u5145\u4e86\u56f4\u7ed5\u65b0\u6d41\u7a0b\u7684\u6d4b\u8bd5\u4e0e\u6587\u6863\u6574\u7406\u3002'}
                      </li>
                    </ul>
                  </div>
                </article>

                <section className={`previous-releases ${showPreviousReleases ? 'previous-releases-open' : ''}`}>
                  <button
                    type="button"
                    className="previous-releases-toggle"
                    onClick={() => setShowPreviousReleases(prev => !prev)}
                    aria-expanded={showPreviousReleases}
                  >
                    <span>
                      {language === 'en' ? 'View previous releases' : '\u67e5\u770b\u66f4\u65e9\u7248\u672c'}
                    </span>
                    <span className="previous-releases-meta">
                      {language === 'en' ? 'v0.1.0 and earlier' : 'v0.1.0 \u53ca\u66f4\u65e9\u7248\u672c'}
                    </span>
                  </button>

                  <div className="previous-releases-panel" aria-hidden={!showPreviousReleases}>
                    <div className="previous-releases-inner">
                      <article className="release-card release-card-subtle">
                        <header className="release-header">
                          <div>
                            <div className="release-version">v0.1.0</div>
                            <div className="release-label">
                              {language === 'en'
                                ? 'Initial public release'
                                : '\u9996\u6b21\u516c\u5f00\u53d1\u5e03'}
                            </div>
                          </div>
                          <div className="release-badges">
                            <span className="release-pill">PyPI</span>
                            <span className="release-pill release-pill-soft">
                              {language === 'en' ? 'Alpha' : '\u6d4b\u8bd5\u7248'}
                            </span>
                          </div>
                        </header>

                        <p className="release-summary">
                          {language === 'en'
                            ? 'Initial public release of the WeChat MCP server, exposing an MCP-compatible interface for reading and replying to WeChat messages on macOS via Accessibility APIs and screen capture.'
                            : 'WeChat MCP \u670d\u52a1\u5668\u7684\u9996\u6b21\u516c\u5f00\u7248\u672c\uff0c\u5728 macOS \u4e0a\u901a\u8fc7\u8f85\u52a9\u529f\u80fd API \u548c\u622a\u5c4f\u63d0\u4f9b\u8bfb\u53d6\u4e0e\u56de\u590d\u5fae\u4fe1\u6d88\u606f\u7684 MCP \u63a5\u53e3\u3002'}
                        </p>

                        <div className="release-install">
                          <div className="release-install-label">
                            {language === 'en' ? 'Install' : '\u5b89\u88c5'}
                          </div>
                          <pre className="code-snippet">
                            <code>pip install wechat-mcp-server</code>
                          </pre>
                        </div>

                        <div className="release-section">
                          <h3>{language === 'en' ? 'Highlights' : '\u4eae\u70b9'}</h3>
                          <ul>
                            <li>
                              {language === 'en'
                                ? 'MCP server exposing WeChat automation tools over stdio, streamable HTTP, or SSE transports.'
                                : '\u901a\u8fc7 stdio\u3001streamable HTTP \u548c SSE \u66b4\u9732\u5fae\u4fe1\u81ea\u52a8\u5316 MCP \u5de5\u5177\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'End-to-end macOS Accessibility integration to locate chats, read message history, and send replies.'
                                : '\u5b8c\u6574\u63a5\u5165 macOS \u8f85\u52a9\u529f\u80fd\u80fd\u529b\uff0c\u7528\u4e8e\u5b9a\u4f4d\u804a\u5929\u3001\u8bfb\u53d6\u6d88\u606f\u5386\u53f2\u548c\u53d1\u9001\u56de\u590d\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'Screenshot-based sender classification to distinguish messages from you vs. others.'
                                : '\u901a\u8fc7\u622a\u56fe\u542f\u53d1\u5f0f\u533a\u5206\u81ea\u5df1\u4e0e\u4ed6\u4eba\u7684\u6d88\u606f\u53d1\u9001\u8005\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'Structured logging to both terminal and rotating log files.'
                                : '\u540c\u65f6\u8f93\u51fa\u5230\u7ec8\u7aef\u548c\u65e5\u5fd7\u6587\u4ef6\u7684\u7ed3\u6784\u5316\u65e5\u5fd7\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'First official PyPI release of wechat-mcp-server.'
                                : 'wechat-mcp-server \u7684\u9996\u6b21\u6b63\u5f0f PyPI \u53d1\u5e03\u3002'}
                            </li>
                          </ul>
                        </div>

                        <div className="release-section">
                          <h3>{language === 'en' ? 'Features' : '\u529f\u80fd'}</h3>
                          <ul>
                            <li>
                              {language === 'en'
                                ? 'MCP server and CLI via the wechat-mcp console script with stdio, HTTP, and SSE transports.'
                                : '\u63d0\u4f9b wechat-mcp \u547d\u4ee4\u884c\u5165\u53e3\uff0c\u652f\u6301 stdio\u3001HTTP \u548c SSE \u4f20\u8f93\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'WeChat tools for fetching messages by chat and replying to messages, with smart handling of ambiguous chat names.'
                                : '\u63d0\u4f9b\u6309\u804a\u5929\u8bfb\u53d6\u6d88\u606f\u548c\u53d1\u9001\u56de\u590d\u7684\u5fae\u4fe1\u5de5\u5177\uff0c\u5e76\u80fd\u667a\u80fd\u5904\u7406\u540d\u79f0\u6b67\u4e49\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'macOS Accessibility helpers that drive the WeChat UI, scroll message history, and capture screenshots for sender classification.'
                                : '\u5229\u7528 macOS \u8f85\u52a9\u529f\u80fd\u9a71\u52a8\u5fae\u4fe1\u754c\u9762\u3001\u6eda\u52a8\u6d88\u606f\u5386\u53f2\u5e76\u622a\u56fe\u5224\u65ad\u53d1\u9001\u8005\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'Logging and observability with configurable log directory and verbose debug mode for MCP and HTTP traffic.'
                                : '\u63d0\u4f9b\u53ef\u914d\u7f6e\u65e5\u5fd7\u76ee\u5f55\uff0c\u4ee5\u53ca\u9762\u5411 MCP \u548c HTTP \u4ea4\u4e92\u7684\u8be6\u7ec6\u8c03\u8bd5\u6a21\u5f0f\u3002'}
                            </li>
                          </ul>
                        </div>

                        <div className="release-section">
                          <h3>{language === 'en' ? 'Requirements' : '\u8981\u6c42'}</h3>
                          <ul>
                            <li>
                              {language === 'en'
                                ? 'macOS with Accessibility and screen capture permissions granted to your terminal or Python.'
                                : '\u9700\u8981 macOS\uff0c\u5e76\u5411\u7ec8\u7aef\u6216 Python \u6388\u4e88\u8f85\u52a9\u529f\u80fd\u548c\u622a\u5c4f\u6743\u9650\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'WeChat installed and running on macOS.'
                                : '\u9700\u8981\u5df2\u5b89\u88c5\u5e76\u8fd0\u884c\u7684 macOS \u5fae\u4fe1\u5ba2\u6237\u7aef\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'Python 3.12+ with pyobjc, Pillow, and mcp[cli] dependencies.'
                                : '\u9700\u8981 Python 3.12+\uff0c\u4ee5\u53ca pyobjc\u3001Pillow \u548c mcp[cli] \u4f9d\u8d56\u3002'}
                            </li>
                          </ul>
                        </div>

                        <div className="release-section">
                          <h3>{language === 'en' ? 'Known limitations' : '\u5df2\u77e5\u9650\u5236'}</h3>
                          <ul>
                            <li>
                              {language === 'en'
                                ? 'Tested only on the standard macOS WeChat client and default Accessibility structure.'
                                : '\u4ec5\u5728\u6807\u51c6 macOS \u5fae\u4fe1\u5ba2\u6237\u7aef\u548c\u9ed8\u8ba4\u8f85\u52a9\u529f\u80fd\u7ed3\u6784\u4e0a\u9a8c\u8bc1\u8fc7\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'Sender classification relies on color heuristics and may misclassify in unusual themes or display conditions.'
                                : '\u53d1\u9001\u8005\u8bc6\u522b\u4f9d\u8d56\u989c\u8272\u542f\u53d1\u5f0f\uff0c\u5728\u7279\u6b8a\u4e3b\u9898\u6216\u663e\u793a\u6761\u4ef6\u4e0b\u53ef\u80fd\u8bef\u5224\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'Focuses on English or Latin chat names; broader localization is planned.'
                                : '\u5f53\u524d\u4e3b\u8981\u9762\u5411\u82f1\u6587\u6216\u62c9\u4e01\u5b57\u7b26\u804a\u5929\u540d\uff0c\u66f4\u5e7f\u6cdb\u7684\u672c\u5730\u5316\u4ecd\u5728\u89c4\u5212\u4e2d\u3002'}
                            </li>
                            <li>
                              {language === 'en'
                                ? 'Marked as alpha; APIs and behavior may change in future versions.'
                                : '\u5f53\u524d\u4ecd\u4e3a alpha \u7248\u672c\uff0cAPI \u4e0e\u884c\u4e3a\u5728\u540e\u7eed\u7248\u672c\u4e2d\u53ef\u80fd\u53d8\u5316\u3002'}
                            </li>
                          </ul>
                        </div>
                      </article>
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </section>
        )}
      </main>

      <footer className="footer">
        <div className="container footer-content">
          <p>{t.footer.madeWith}</p>
          <div className="footer-links">
            <a href="https://github.com/BiboyQG/WeChat-MCP" target="_blank" rel="noopener noreferrer">GitHub</a>
            <a href="https://pypi.org/project/wechat-mcp-server/" target="_blank" rel="noopener noreferrer">PyPI</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
