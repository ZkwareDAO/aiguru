"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Bot,
  Send,
  Mic,
  MicOff,
  Paperclip,
  BookOpen,
  Calculator,
  Globe,
  Lightbulb,
  Target,
  Clock,
  User,
  Loader2,
} from "lucide-react"

interface Message {
  id: string
  type: "user" | "assistant"
  content: string
  timestamp: Date
  suggestions?: string[]
  attachments?: { name: string; type: string }[]
}

interface QuickAction {
  id: string
  label: string
  icon: React.ReactNode
  description: string
  prompt: string
}

const quickActions: QuickAction[] = [
  {
    id: "explain",
    label: "解释题目",
    icon: <BookOpen className="w-4 h-4" />,
    description: "帮我解释这道题的解题思路",
    prompt: "请帮我解释这道题目的解题思路和关键知识点",
  },
  {
    id: "calculate",
    label: "计算步骤",
    icon: <Calculator className="w-4 h-4" />,
    description: "详细的计算过程分析",
    prompt: "请提供详细的计算步骤和过程分析",
  },
  {
    id: "translate",
    label: "英语翻译",
    icon: <Globe className="w-4 h-4" />,
    description: "翻译英语句子或段落",
    prompt: "请帮我翻译这段英语内容，并解释重点语法",
  },
  {
    id: "suggest",
    label: "学习建议",
    icon: <Lightbulb className="w-4 h-4" />,
    description: "获取个性化学习建议",
    prompt: "根据我的学习情况，给我一些个性化的学习建议",
  },
  {
    id: "plan",
    label: "制定计划",
    icon: <Target className="w-4 h-4" />,
    description: "制定学习计划和目标",
    prompt: "帮我制定一个合理的学习计划和目标",
  },
  {
    id: "review",
    label: "复习指导",
    icon: <Clock className="w-4 h-4" />,
    description: "复习方法和重点指导",
    prompt: "请给我一些有效的复习方法和重点指导",
  },
]

const mockResponses = {
  greeting:
    "你好！我是你的AI学习助手，很高兴为你服务！我可以帮你解答学习问题、分析错题、制定学习计划等。有什么我可以帮助你的吗？",
  explain: "我来帮你分析这道题目。首先，我们需要理解题目的核心概念...",
  calculate: "让我为你详细分解计算步骤：\n\n第一步：确定已知条件\n第二步：选择合适的公式\n第三步：代入数值计算...",
  translate: "这句话的翻译是：...\n\n重点语法解析：\n1. 时态使用\n2. 词汇搭配\n3. 句型结构",
  suggest: "根据你的学习数据分析，我建议：\n\n1. 加强数学基础练习\n2. 提高英语词汇量\n3. 规律复习物理公式",
  plan: "为你制定以下学习计划：\n\n本周目标：\n- 完成数学练习20题\n- 背诵英语单词100个\n- 复习物理第3章",
  review: "有效的复习方法包括：\n\n1. 间隔重复法\n2. 主动回忆\n3. 错题本整理\n4. 知识点关联",
}

export function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "assistant",
      content: mockResponses.greeting,
      timestamp: new Date(),
      suggestions: ["我有数学问题", "帮我分析错题", "制定学习计划", "英语翻译"],
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: content.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")
    setIsLoading(true)

    // Simulate AI response
    setTimeout(() => {
      const responseContent = getAIResponse(content)
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: responseContent,
        timestamp: new Date(),
        suggestions: getRandomSuggestions(),
      }

      setMessages((prev) => [...prev, assistantMessage])
      setIsLoading(false)
    }, 1500)
  }

  const getAIResponse = (input: string): string => {
    const lowerInput = input.toLowerCase()
    if (lowerInput.includes("数学") || lowerInput.includes("计算")) {
      return mockResponses.calculate
    }
    if (lowerInput.includes("英语") || lowerInput.includes("翻译")) {
      return mockResponses.translate
    }
    if (lowerInput.includes("建议") || lowerInput.includes("怎么")) {
      return mockResponses.suggest
    }
    if (lowerInput.includes("计划") || lowerInput.includes("目标")) {
      return mockResponses.plan
    }
    if (lowerInput.includes("复习") || lowerInput.includes("方法")) {
      return mockResponses.review
    }
    if (lowerInput.includes("解释") || lowerInput.includes("题目")) {
      return mockResponses.explain
    }
    return "我理解你的问题。让我为你详细分析一下这个问题的解决方案..."
  }

  const getRandomSuggestions = (): string[] => {
    const allSuggestions = ["继续解释", "给个例题", "相关知识点", "练习推荐", "复习重点", "学习方法"]
    return allSuggestions.slice(0, 3)
  }

  const handleQuickAction = (action: QuickAction) => {
    handleSendMessage(action.prompt)
  }

  const handleSuggestionClick = (suggestion: string) => {
    handleSendMessage(suggestion)
  }

  const toggleVoiceInput = () => {
    setIsListening(!isListening)
    // Here you would implement actual voice recognition
  }

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] animate-fade-in-up">
      {/* Chat Header */}
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center animate-pulse-glow">
              <Bot className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">AI学习助手</h3>
              <p className="text-sm text-muted-foreground">智能解答 · 个性化指导 · 24小时在线</p>
            </div>
            <div className="ml-auto">
              <Badge variant="secondary" className="bg-green-100 text-green-700">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse" />
                在线
              </Badge>
            </div>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Quick Actions */}
      <Card className="mb-4">
        <CardContent className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
            {quickActions.map((action) => (
              <Button
                key={action.id}
                variant="outline"
                size="sm"
                className="h-auto p-3 flex flex-col gap-1 bg-transparent hover:bg-primary/5"
                onClick={() => handleQuickAction(action)}
              >
                {action.icon}
                <span className="text-xs">{action.label}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Chat Messages */}
      <Card className="flex-1 flex flex-col">
        <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex gap-3 ${message.type === "user" ? "justify-end" : ""}`}>
                {message.type === "assistant" && (
                  <Avatar className="w-8 h-8 flex-shrink-0">
                    <AvatarFallback className="bg-primary text-primary-foreground">
                      <Bot className="w-4 h-4" />
                    </AvatarFallback>
                  </Avatar>
                )}

                <div className={`max-w-[80%] ${message.type === "user" ? "order-first" : ""}`}>
                  <div
                    className={`p-3 rounded-lg ${
                      message.type === "user"
                        ? "bg-primary text-primary-foreground ml-auto"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                  </div>

                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span>{message.timestamp.toLocaleTimeString()}</span>
                  </div>

                  {message.suggestions && message.suggestions.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {message.suggestions.map((suggestion, index) => (
                        <Button
                          key={index}
                          variant="outline"
                          size="sm"
                          className="h-6 px-2 text-xs bg-transparent"
                          onClick={() => handleSuggestionClick(suggestion)}
                        >
                          {suggestion}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>

                {message.type === "user" && (
                  <Avatar className="w-8 h-8 flex-shrink-0">
                    <AvatarFallback>
                      <User className="w-4 h-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3">
                <Avatar className="w-8 h-8 flex-shrink-0">
                  <AvatarFallback className="bg-primary text-primary-foreground">
                    <Bot className="w-4 h-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="bg-muted p-3 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">AI正在思考中...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="border-t border-border p-4">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="输入你的问题..."
                className="pr-20"
                onKeyPress={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage(inputValue)
                  }
                }}
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 w-6 p-0"
                  onClick={toggleVoiceInput}
                  disabled={isLoading}
                >
                  {isListening ? <MicOff className="w-3 h-3" /> : <Mic className="w-3 h-3" />}
                </Button>
                <Button size="sm" variant="ghost" className="h-6 w-6 p-0" disabled={isLoading}>
                  <Paperclip className="w-3 h-3" />
                </Button>
              </div>
            </div>
            <Button
              onClick={() => handleSendMessage(inputValue)}
              disabled={!inputValue.trim() || isLoading}
              className="gap-2"
            >
              <Send className="w-4 h-4" />
              发送
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            AI助手可能会出错，请核实重要信息。按Enter发送，Shift+Enter换行
          </p>
        </div>
      </Card>
    </div>
  )
}
