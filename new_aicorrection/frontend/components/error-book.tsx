"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  BookOpen,
  Search,
  Filter,
  RotateCcw,
  CheckCircle,
  XCircle,
  Clock,
  Target,
  TrendingUp,
  Brain,
  Lightbulb,
  Star,
  Calendar,
} from "lucide-react"
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { CompletionAnimation, useCompletionAnimation } from "./completion-animations"

interface ErrorQuestion {
  id: string
  subject: string
  topic: string
  question: string
  userAnswer: string
  correctAnswer: string
  explanation: string
  difficulty: "easy" | "medium" | "hard"
  errorType: "knowledge" | "logic" | "calculation" | "careless"
  dateAdded: string
  attempts: number
  lastAttempt: string
  mastered: boolean
  tags: string[]
}

const mockErrorQuestions: ErrorQuestion[] = [
  {
    id: "1",
    subject: "数学",
    topic: "二次函数",
    question: "求函数 f(x) = x² - 4x + 3 的顶点坐标",
    userAnswer: "(2, 1)",
    correctAnswer: "(2, -1)",
    explanation:
      "二次函数 f(x) = ax² + bx + c 的顶点坐标为 (-b/2a, f(-b/2a))。这里 a=1, b=-4, 所以顶点横坐标为 -(-4)/(2×1) = 2，纵坐标为 f(2) = 4 - 8 + 3 = -1。",
    difficulty: "medium",
    errorType: "calculation",
    dateAdded: "2024-01-15",
    attempts: 2,
    lastAttempt: "2024-01-20",
    mastered: false,
    tags: ["顶点公式", "计算错误"],
  },
  {
    id: "2",
    subject: "英语",
    topic: "语法",
    question: "Choose the correct form: I _____ to the store yesterday.",
    userAnswer: "go",
    correctAnswer: "went",
    explanation: "这是一个过去时态的句子，yesterday 表示过去的时间，所以动词应该用过去式 went。",
    difficulty: "easy",
    errorType: "knowledge",
    dateAdded: "2024-01-14",
    attempts: 1,
    lastAttempt: "2024-01-18",
    mastered: true,
    tags: ["过去时", "动词变位"],
  },
  {
    id: "3",
    subject: "物理",
    topic: "力学",
    question: "一个物体从10m高处自由落下，求落地时的速度（g=10m/s²）",
    userAnswer: "10 m/s",
    correctAnswer: "14.14 m/s",
    explanation:
      "根据自由落体运动公式 v² = 2gh，代入 h=10m, g=10m/s²，得到 v² = 2×10×10 = 200，所以 v = √200 ≈ 14.14 m/s。",
    difficulty: "medium",
    errorType: "logic",
    dateAdded: "2024-01-13",
    attempts: 3,
    lastAttempt: "2024-01-19",
    mastered: false,
    tags: ["自由落体", "公式应用"],
  },
]

const errorTypeData = [
  { name: "知识点错误", value: 35, color: "#ef4444" },
  { name: "逻辑错误", value: 25, color: "#f97316" },
  { name: "计算错误", value: 30, color: "#eab308" },
  { name: "粗心错误", value: 10, color: "#22c55e" },
]

const subjectData = [
  { subject: "数学", errors: 12, mastered: 8 },
  { subject: "英语", errors: 8, mastered: 6 },
  { subject: "物理", errors: 6, mastered: 3 },
  { subject: "化学", errors: 4, mastered: 2 },
]

export function ErrorBook() {
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedSubject, setSelectedSubject] = useState("all")
  const [selectedDifficulty, setSelectedDifficulty] = useState("all")
  const [showMasteredOnly, setShowMasteredOnly] = useState(false)
  const [selectedQuestion, setSelectedQuestion] = useState<ErrorQuestion | null>(null)
  const { animation, showAnimation, hideAnimation } = useCompletionAnimation()

  const filteredQuestions = mockErrorQuestions.filter((question) => {
    const matchesSearch =
      question.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
      question.topic.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesSubject = selectedSubject === "all" || question.subject === selectedSubject
    const matchesDifficulty = selectedDifficulty === "all" || question.difficulty === selectedDifficulty
    const matchesMastered = !showMasteredOnly || question.mastered

    return matchesSearch && matchesSubject && matchesDifficulty && matchesMastered
  })

  const getErrorTypeColor = (type: string) => {
    switch (type) {
      case "knowledge":
        return "bg-red-100 text-red-700"
      case "logic":
        return "bg-orange-100 text-orange-700"
      case "calculation":
        return "bg-yellow-100 text-yellow-700"
      case "careless":
        return "bg-green-100 text-green-700"
      default:
        return "bg-gray-100 text-gray-700"
    }
  }

  const getErrorTypeLabel = (type: string) => {
    switch (type) {
      case "knowledge":
        return "知识点"
      case "logic":
        return "逻辑"
      case "calculation":
        return "计算"
      case "careless":
        return "粗心"
      default:
        return "其他"
    }
  }

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case "easy":
        return "text-green-600"
      case "medium":
        return "text-yellow-600"
      case "hard":
        return "text-red-600"
      default:
        return "text-gray-600"
    }
  }

  const handleQuestionMastery = (questionId: string) => {
    const question = mockErrorQuestions.find((q) => q.id === questionId)
    if (question && !question.mastered) {
      question.mastered = true
      showAnimation("achievement", `恭喜！你已掌握"${question.topic}"知识点！`)
    }
  }

  const handleStartPractice = (type: string, count: number) => {
    showAnimation("progress", `开始${type}练习，共${count}道题！`)
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {animation && (
        <CompletionAnimation type={animation.type} message={animation.message} onComplete={hideAnimation} />
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="hover:scale-105 transition-transform duration-200">
          <CardContent className="p-4 text-center">
            <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center mx-auto mb-2">
              <XCircle className="w-4 h-4 text-red-600" />
            </div>
            <p className="text-2xl font-bold animate-pulse-scale">{mockErrorQuestions.length}</p>
            <p className="text-xs text-muted-foreground">总错题数</p>
          </CardContent>
        </Card>
        <Card className="hover:scale-105 transition-transform duration-200">
          <CardContent className="p-4 text-center">
            <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
            </div>
            <p className="text-2xl font-bold animate-pulse-scale">
              {mockErrorQuestions.filter((q) => q.mastered).length}
            </p>
            <p className="text-xs text-muted-foreground">已掌握</p>
          </CardContent>
        </Card>
        <Card className="hover:scale-105 transition-transform duration-200">
          <CardContent className="p-4 text-center">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Target className="w-4 h-4 text-blue-600" />
            </div>
            <p className="text-2xl font-bold animate-pulse-scale">
              {Math.round((mockErrorQuestions.filter((q) => q.mastered).length / mockErrorQuestions.length) * 100)}%
            </p>
            <p className="text-xs text-muted-foreground">掌握率</p>
          </CardContent>
        </Card>
        <Card className="hover:scale-105 transition-transform duration-200">
          <CardContent className="p-4 text-center">
            <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Clock className="w-4 h-4 text-purple-600" />
            </div>
            <p className="text-2xl font-bold animate-pulse-scale">7</p>
            <p className="text-xs text-muted-foreground">天练习</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="questions" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="questions" className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            错题列表
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            数据分析
          </TabsTrigger>
          <TabsTrigger value="practice" className="flex items-center gap-2">
            <Brain className="w-4 h-4" />
            智能练习
          </TabsTrigger>
        </TabsList>

        <TabsContent value="questions" className="space-y-4">
          <Card className="animate-fade-in-up">
            <CardContent className="p-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                    <Input
                      placeholder="搜索错题或知识点..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <select
                    value={selectedSubject}
                    onChange={(e) => setSelectedSubject(e.target.value)}
                    className="px-3 py-2 border border-border rounded-md text-sm bg-background"
                  >
                    <option value="all">全部科目</option>
                    <option value="数学">数学</option>
                    <option value="英语">英语</option>
                    <option value="物理">物理</option>
                    <option value="化学">化学</option>
                  </select>
                  <select
                    value={selectedDifficulty}
                    onChange={(e) => setSelectedDifficulty(e.target.value)}
                    className="px-3 py-2 border border-border rounded-md text-sm bg-background"
                  >
                    <option value="all">全部难度</option>
                    <option value="easy">简单</option>
                    <option value="medium">中等</option>
                    <option value="hard">困难</option>
                  </select>
                  <Button
                    variant={showMasteredOnly ? "default" : "outline"}
                    size="sm"
                    onClick={() => setShowMasteredOnly(!showMasteredOnly)}
                  >
                    <Filter className="w-4 h-4 mr-1" />
                    已掌握
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-3">
            {filteredQuestions.map((question, index) => (
              <Card
                key={question.id}
                className={`cursor-pointer transition-all duration-300 hover:shadow-md hover:scale-[1.02] animate-fade-in-up ${
                  selectedQuestion?.id === question.id ? "ring-2 ring-primary" : ""
                } ${question.mastered ? "bg-green-50 border-green-200" : ""}`}
                style={{ animationDelay: `${index * 0.1}s` }}
                onClick={() => setSelectedQuestion(selectedQuestion?.id === question.id ? null : question)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-200 ${
                        question.mastered ? "bg-green-100 animate-bounce" : "bg-red-100"
                      }`}
                    >
                      {question.mastered ? (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-600" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="text-xs">
                          {question.subject}
                        </Badge>
                        <Badge variant="secondary" className="text-xs">
                          {question.topic}
                        </Badge>
                        <Badge className={`text-xs ${getErrorTypeColor(question.errorType)}`}>
                          {getErrorTypeLabel(question.errorType)}
                        </Badge>
                        <span className={`text-xs font-medium ${getDifficultyColor(question.difficulty)}`}>
                          {question.difficulty === "easy" ? "简单" : question.difficulty === "medium" ? "中等" : "困难"}
                        </span>
                      </div>
                      <p className="font-medium text-sm mb-1 line-clamp-2">{question.question}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>练习 {question.attempts} 次</span>
                        <span>最后练习: {question.lastAttempt}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {question.mastered && <Star className="w-4 h-4 text-yellow-500 animate-pulse" />}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleStartPractice("重新练习", 1)
                        }}
                        className="hover:scale-110 transition-transform duration-200"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  {selectedQuestion?.id === question.id && (
                    <div className="mt-4 pt-4 border-t border-border animate-fade-in-up">
                      <div className="space-y-3">
                        <div>
                          <p className="text-sm font-medium text-red-600 mb-1">你的答案:</p>
                          <p className="text-sm bg-red-50 p-2 rounded">{question.userAnswer}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-green-600 mb-1">正确答案:</p>
                          <p className="text-sm bg-green-50 p-2 rounded">{question.correctAnswer}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium mb-1">详细解析:</p>
                          <p className="text-sm bg-muted/50 p-3 rounded leading-relaxed">{question.explanation}</p>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {question.tags.map((tag, index) => (
                            <Badge key={index} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                        <div className="flex gap-2 pt-2">
                          <Button
                            size="sm"
                            className="flex-1 hover:scale-105 transition-transform duration-200"
                            onClick={() => handleStartPractice("重新练习", 1)}
                          >
                            <RotateCcw className="w-4 h-4 mr-1" />
                            重新练习
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="flex-1 bg-transparent hover:scale-105 transition-transform duration-200"
                            onClick={() => handleStartPractice("相似题目", 5)}
                          >
                            <Lightbulb className="w-4 h-4 mr-1" />
                            相似题目
                          </Button>
                          {!question.mastered && (
                            <Button
                              size="sm"
                              variant="default"
                              className="flex-1 hover:scale-105 transition-transform duration-200"
                              onClick={() => handleQuestionMastery(question.id)}
                            >
                              <CheckCircle className="w-4 h-4 mr-1" />
                              标记掌握
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="animate-fade-in-up">
              <CardHeader>
                <CardTitle>错误类型分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={errorTypeData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {errorTypeData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-4">
                  {errorTypeData.map((item, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-sm">{item.name}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
              <CardHeader>
                <CardTitle>各科目错题统计</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={subjectData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="subject" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="errors" fill="#ef4444" name="错题数" />
                      <Bar dataKey="mastered" fill="#22c55e" name="已掌握" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="animate-fade-in-up" style={{ animationDelay: "0.4s" }}>
            <CardHeader>
              <CardTitle>学习进度概览</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {subjectData.map((subject, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{subject.subject}</span>
                      <span className="text-muted-foreground">
                        {subject.mastered}/{subject.errors} 已掌握
                      </span>
                    </div>
                    <Progress value={(subject.mastered / subject.errors) * 100} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="practice" className="space-y-4">
          <Card className="animate-fade-in-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5" />
                AI智能练习推荐
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200 hover:scale-105 transition-transform duration-300">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                        <Target className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold">薄弱知识点强化</h3>
                        <p className="text-sm text-muted-foreground">针对二次函数错题</p>
                      </div>
                    </div>
                    <p className="text-sm mb-3">基于你的错题分析，推荐练习二次函数相关题目</p>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">8道题 · 20分钟</Badge>
                      <Button
                        size="sm"
                        onClick={() => handleStartPractice("薄弱知识点强化", 8)}
                        className="hover:scale-110 transition-transform duration-200"
                      >
                        开始练习
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200 hover:scale-105 transition-transform duration-300">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center">
                        <RotateCcw className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold">错题回顾练习</h3>
                        <p className="text-sm text-muted-foreground">复习未掌握题目</p>
                      </div>
                    </div>
                    <p className="text-sm mb-3">重新练习你还未完全掌握的错题</p>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">5道题 · 15分钟</Badge>
                      <Button
                        size="sm"
                        onClick={() => handleStartPractice("错题回顾", 5)}
                        className="hover:scale-110 transition-transform duration-200"
                      >
                        开始复习
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200 hover:scale-105 transition-transform duration-300">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
                        <Lightbulb className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold">相似题型训练</h3>
                        <p className="text-sm text-muted-foreground">扩展练习</p>
                      </div>
                    </div>
                    <p className="text-sm mb-3">练习与你的错题相似的题型，巩固理解</p>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">12道题 · 30分钟</Badge>
                      <Button
                        size="sm"
                        onClick={() => handleStartPractice("相似题型训练", 12)}
                        className="hover:scale-110 transition-transform duration-200"
                      >
                        开始训练
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200 hover:scale-105 transition-transform duration-300">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center">
                        <Calendar className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold">每日错题回顾</h3>
                        <p className="text-sm text-muted-foreground">定期复习计划</p>
                      </div>
                    </div>
                    <p className="text-sm mb-3">制定个性化的错题复习计划</p>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">每天3道题</Badge>
                      <Button
                        size="sm"
                        onClick={() => showAnimation("success", "每日错题回顾提醒已设置！")}
                        className="hover:scale-110 transition-transform duration-200"
                      >
                        设置提醒
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
