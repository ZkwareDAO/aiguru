"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  XCircle,
  AlertTriangle,
  BookOpen,
  Lightbulb,
  Download,
  Share2,
  RefreshCw,
  Target,
  Award,
  Brain,
  CheckCircle,
  TrendingUp,
  Eye,
  Zap,
  Star,
  Clock,
  BarChart3,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts"

interface ErrorItem {
  id: string
  type: "grammar" | "logic" | "knowledge" | "calculation" | "format"
  content: string
  suggestion: string
  position: { start: number; end: number }
  severity: "high" | "medium" | "low"
  knowledgePoint?: string
  correctAnswer?: string
}

interface KnowledgePoint {
  name: string
  mastery: number
  importance: "high" | "medium" | "low"
  relatedErrors: string[]
}

interface GradingResultProps {
  score: number
  totalScore: number
  grade: string
  subject: string
  errors: ErrorItem[]
  suggestions: string[]
  originalText: string
  knowledgePoints?: KnowledgePoint[]
  timeSpent?: number
  difficulty?: "easy" | "medium" | "hard"
  classAverage?: number
  previousScores?: number[]
}

export function GradingResult({
  score = 78,
  totalScore = 100,
  grade = "B+",
  subject = "数学作业",
  errors = [
    {
      id: "1",
      type: "knowledge",
      content: "二次函数的顶点公式应用错误",
      suggestion: "顶点坐标为(-b/2a, (4ac-b²)/4a)，请重新计算",
      position: { start: 45, end: 67 },
      severity: "high",
      knowledgePoint: "二次函数",
      correctAnswer: "顶点坐标为(-1, -4)",
    },
    {
      id: "2",
      type: "logic",
      content: "解题步骤跳跃，缺少中间过程",
      suggestion: "建议补充从第2步到第4步的详细推导过程",
      position: { start: 120, end: 145 },
      severity: "medium",
      knowledgePoint: "解题规范",
    },
    {
      id: "3",
      type: "calculation",
      content: "计算错误：3×4应该等于12，不是14",
      suggestion: "请仔细检查基础运算，建议使用草稿纸验算",
      position: { start: 200, end: 210 },
      severity: "low",
      knowledgePoint: "基础运算",
      correctAnswer: "12",
    },
  ],
  suggestions = ["加强二次函数基础概念的理解", "多练习顶点式与一般式的转换", "注意解题步骤的完整性"],
  originalText = "这是一道关于二次函数的题目，求函数f(x)=x²+2x-3的顶点坐标。\n\n解：\n设f(x)=x²+2x-3\n根据顶点公式，顶点坐标为...\n\n（此处省略具体解题过程）",
  knowledgePoints = [
    { name: "二次函数", mastery: 75, importance: "high", relatedErrors: ["1"] },
    { name: "函数图像", mastery: 85, importance: "medium", relatedErrors: [] },
    { name: "解题规范", mastery: 60, importance: "high", relatedErrors: ["2"] },
    { name: "基础运算", mastery: 90, importance: "medium", relatedErrors: ["3"] },
  ],
  timeSpent = 25,
  difficulty = "medium",
  classAverage = 82,
  previousScores = [65, 72, 78, 85, 78],
}: GradingResultProps) {
  const [selectedError, setSelectedError] = useState<string | null>(null)
  const [highlightedText, setHighlightedText] = useState<string>(originalText)

  const percentage = Math.round((score / totalScore) * 100)

  const getGradeColor = (grade: string) => {
    if (grade.startsWith("A")) return "text-green-600"
    if (grade.startsWith("B")) return "text-blue-600"
    if (grade.startsWith("C")) return "text-yellow-600"
    return "text-red-600"
  }

  const getScoreColor = (score: number, total: number) => {
    const percentage = (score / total) * 100
    if (percentage >= 90) return "text-green-600"
    if (percentage >= 80) return "text-blue-600"
    if (percentage >= 70) return "text-yellow-600"
    return "text-red-600"
  }

  const getErrorIcon = (type: string) => {
    switch (type) {
      case "grammar":
        return <AlertTriangle className="w-4 h-4" />
      case "logic":
        return <Brain className="w-4 h-4" />
      case "knowledge":
        return <BookOpen className="w-4 h-4" />
      case "calculation":
        return <Target className="w-4 h-4" />
      case "format":
        return <Eye className="w-4 h-4" />
      default:
        return <XCircle className="w-4 h-4" />
    }
  }

  const getErrorTypeLabel = (type: string) => {
    switch (type) {
      case "grammar":
        return "语法错误"
      case "logic":
        return "逻辑问题"
      case "knowledge":
        return "知识点错误"
      case "calculation":
        return "计算错误"
      case "format":
        return "格式问题"
      default:
        return "其他错误"
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "destructive"
      case "medium":
        return "secondary"
      case "low":
        return "outline"
      default:
        return "outline"
    }
  }

  const performanceData =
    previousScores?.map((score, index) => ({
      attempt: `第${index + 1}次`,
      score: score,
    })) || []

  const knowledgeRadarData =
    knowledgePoints?.map((point) => ({
      knowledge: point.name,
      mastery: point.mastery,
      fullMark: 100,
    })) || []

  const highlightErrors = (text: string) => {
    let highlightedText = text
    errors.forEach((error, index) => {
      const errorClass =
        error.severity === "high"
          ? "bg-red-100 border-b-2 border-red-500"
          : error.severity === "medium"
            ? "bg-yellow-100 border-b-2 border-yellow-500"
            : "bg-blue-100 border-b-2 border-blue-500"

      // Simple highlighting - in a real app, you'd use proper text positioning
      if (error.content.length > 0) {
        highlightedText = highlightedText.replace(
          new RegExp(error.content.split(" ")[0], "g"),
          `<span class="${errorClass} cursor-pointer" data-error-id="${error.id}">${error.content.split(" ")[0]}</span>`,
        )
      }
    })
    return highlightedText
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Enhanced Score Header */}
      <Card className="bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20 overflow-hidden relative">
        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -translate-y-16 translate-x-16" />
        <CardContent className="p-8 relative">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
            <div className="text-center md:text-left">
              <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center mx-auto md:mx-0 mb-4 animate-pulse-glow">
                <Award className="w-10 h-10 text-primary-foreground" />
              </div>
              <h2 className="text-4xl font-bold mb-2">
                <span className={getScoreColor(score, totalScore)}>{score}</span>
                <span className="text-muted-foreground">/{totalScore}</span>
              </h2>
              <Badge variant="secondary" className="text-lg px-4 py-1">
                {grade} 等级
              </Badge>
            </div>

            <div className="space-y-4">
              <div className="text-center">
                <Progress value={percentage} className="w-full h-3 mb-2" />
                <p className="text-sm text-muted-foreground">完成度 {percentage}%</p>
              </div>
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-blue-600">{timeSpent}min</p>
                  <p className="text-xs text-muted-foreground">用时</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-purple-600">{difficulty}</p>
                  <p className="text-xs text-muted-foreground">难度</p>
                </div>
              </div>
            </div>

            <div className="text-center md:text-right space-y-2">
              <div className="flex items-center justify-center md:justify-end gap-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                <span className="text-sm">{score > (classAverage || 0) ? "高于" : "低于"}班级平均</span>
              </div>
              <p className="text-sm text-muted-foreground">班级平均: {classAverage}分</p>
              <p className="text-xs text-muted-foreground">{subject} - AI智能批改</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Enhanced Main Content Tabs */}
      <Tabs defaultValue="errors" className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="errors" className="flex items-center gap-2">
            <XCircle className="w-4 h-4" />
            错误分析
          </TabsTrigger>
          <TabsTrigger value="knowledge" className="flex items-center gap-2">
            <Brain className="w-4 h-4" />
            知识掌握
          </TabsTrigger>
          <TabsTrigger value="suggestions" className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4" />
            改进建议
          </TabsTrigger>
          <TabsTrigger value="original" className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            原文对照
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            数据分析
          </TabsTrigger>
        </TabsList>

        <TabsContent value="errors" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>发现 {errors.length} 个问题</span>
                  <div className="flex gap-2">
                    <Badge variant="destructive" className="text-xs">
                      {errors.filter((e) => e.severity === "high").length} 重要
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      {errors.filter((e) => e.severity === "medium").length} 中等
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {errors.filter((e) => e.severity === "low").length} 轻微
                    </Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-96">
                  <div className="space-y-3">
                    {errors.map((error) => (
                      <Card
                        key={error.id}
                        className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                          selectedError === error.id ? "ring-2 ring-primary" : ""
                        }`}
                        onClick={() => setSelectedError(selectedError === error.id ? null : error.id)}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <div
                              className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                                error.type === "grammar"
                                  ? "bg-yellow-100 text-yellow-600"
                                  : error.type === "logic"
                                    ? "bg-blue-100 text-blue-600"
                                    : error.type === "calculation"
                                      ? "bg-purple-100 text-purple-600"
                                      : error.type === "format"
                                        ? "bg-green-100 text-green-600"
                                        : "bg-red-100 text-red-600"
                              }`}
                            >
                              {getErrorIcon(error.type)}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <Badge variant={getSeverityColor(error.severity)} className="text-xs">
                                  {getErrorTypeLabel(error.type)}
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                  {error.severity === "high" ? "重要" : error.severity === "medium" ? "中等" : "轻微"}
                                </Badge>
                                {error.knowledgePoint && (
                                  <Badge variant="secondary" className="text-xs">
                                    {error.knowledgePoint}
                                  </Badge>
                                )}
                              </div>
                              <p className="font-medium text-sm mb-1">{error.content}</p>
                              {selectedError === error.id && (
                                <div className="mt-3 space-y-3 animate-fade-in-up">
                                  <div className="p-3 bg-muted/50 rounded-lg">
                                    <p className="text-sm text-muted-foreground mb-2">AI建议：</p>
                                    <p className="text-sm">{error.suggestion}</p>
                                  </div>
                                  {error.correctAnswer && (
                                    <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                                      <p className="text-sm text-green-800 mb-1">正确答案：</p>
                                      <p className="text-sm font-medium text-green-900">{error.correctAnswer}</p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  错误类型分布
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(
                    errors.reduce(
                      (acc, error) => {
                        acc[error.type] = (acc[error.type] || 0) + 1
                        return acc
                      },
                      {} as Record<string, number>,
                    ),
                  ).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getErrorIcon(type)}
                        <span className="text-sm">{getErrorTypeLabel(type)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Progress value={(count / errors.length) * 100} className="w-20 h-2" />
                        <span className="text-sm font-medium">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="knowledge" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="w-5 h-5" />
                  知识点掌握情况
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {knowledgePoints?.map((point, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{point.name}</span>
                          <Badge
                            variant={
                              point.importance === "high"
                                ? "destructive"
                                : point.importance === "medium"
                                  ? "secondary"
                                  : "outline"
                            }
                            className="text-xs"
                          >
                            {point.importance === "high" ? "重点" : point.importance === "medium" ? "一般" : "了解"}
                          </Badge>
                        </div>
                        <span className="text-sm font-bold">{point.mastery}%</span>
                      </div>
                      <Progress value={point.mastery} className="h-2" />
                      {point.relatedErrors.length > 0 && (
                        <p className="text-xs text-muted-foreground">相关错误: {point.relatedErrors.length} 个</p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>知识掌握雷达图</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={knowledgeRadarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="knowledge" />
                      <PolarRadiusAxis angle={90} domain={[0, 100]} />
                      <Radar name="掌握程度" dataKey="mastery" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="suggestions" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lightbulb className="w-5 h-5" />
                  AI学习建议
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {suggestions.map((suggestion, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                      <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-xs font-medium text-primary">{index + 1}</span>
                      </div>
                      <p className="text-sm">{suggestion}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5" />
                  推荐练习
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <Button variant="outline" className="w-full justify-start h-auto p-4 bg-transparent">
                    <div className="text-left">
                      <p className="font-medium">二次函数专项练习</p>
                      <p className="text-xs text-muted-foreground">15道题 · 预计30分钟 · 针对错误1</p>
                    </div>
                  </Button>
                  <Button variant="outline" className="w-full justify-start h-auto p-4 bg-transparent">
                    <div className="text-left">
                      <p className="font-medium">解题步骤规范训练</p>
                      <p className="text-xs text-muted-foreground">10道题 · 预计20分钟 · 针对错误2</p>
                    </div>
                  </Button>
                  <Button variant="outline" className="w-full justify-start h-auto p-4 bg-transparent">
                    <div className="text-left">
                      <p className="font-medium">基础运算强化</p>
                      <p className="text-xs text-muted-foreground">20道题 · 预计15分钟 · 针对错误3</p>
                    </div>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Star className="w-5 h-5" />
                个性化学习路径
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 border border-blue-200 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold text-blue-800 mb-2">第一阶段</h4>
                  <p className="text-sm text-blue-700 mb-3">巩固基础概念</p>
                  <div className="space-y-1">
                    <p className="text-xs text-blue-600">• 二次函数定义复习</p>
                    <p className="text-xs text-blue-600">• 基础公式记忆</p>
                  </div>
                </div>
                <div className="p-4 border border-yellow-200 bg-yellow-50 rounded-lg">
                  <h4 className="font-semibold text-yellow-800 mb-2">第二阶段</h4>
                  <p className="text-sm text-yellow-700 mb-3">强化应用练习</p>
                  <div className="space-y-1">
                    <p className="text-xs text-yellow-600">• 顶点公式应用</p>
                    <p className="text-xs text-yellow-600">• 解题步骤规范</p>
                  </div>
                </div>
                <div className="p-4 border border-green-200 bg-green-50 rounded-lg">
                  <h4 className="font-semibold text-green-800 mb-2">第三阶段</h4>
                  <p className="text-sm text-green-700 mb-3">综合能力提升</p>
                  <div className="space-y-1">
                    <p className="text-xs text-green-600">• 复杂问题求解</p>
                    <p className="text-xs text-green-600">• 知识点综合应用</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="original" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>原文内容</span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Eye className="w-4 h-4 mr-1" />
                    显示错误标注
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="bg-muted/50 p-4 rounded-lg">
                  <pre className="text-sm leading-relaxed whitespace-pre-wrap font-sans">{originalText}</pre>
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>错误位置标注</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {errors.map((error, index) => (
                  <div key={error.id} className="flex items-center gap-3 p-2 bg-muted/30 rounded">
                    <Badge variant={getSeverityColor(error.severity)} className="text-xs">
                      错误 {index + 1}
                    </Badge>
                    <span className="text-sm flex-1">{error.content}</span>
                    <Button variant="ghost" size="sm" onClick={() => setSelectedError(error.id)}>
                      定位
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  成绩趋势
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={performanceData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="attempt" />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="score" stroke="#22c55e" strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>详细统计</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-blue-50 rounded-lg">
                      <p className="text-2xl font-bold text-blue-600">{timeSpent}</p>
                      <p className="text-xs text-blue-700">用时(分钟)</p>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                      <p className="text-2xl font-bold text-green-600">{Math.round((score / totalScore) * 100)}%</p>
                      <p className="text-xs text-green-700">正确率</p>
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">班级排名</span>
                      <span className="font-medium">前25%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">相比上次</span>
                      <span className="font-medium text-green-600">+7分</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">预计提升空间</span>
                      <span className="font-medium text-blue-600">15-20分</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                AI深度分析
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <h4 className="font-semibold text-green-800 mb-2 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    优势分析
                  </h4>
                  <ul className="text-sm text-green-700 space-y-1">
                    <li>• 基础概念掌握扎实</li>
                    <li>• 解题思路清晰</li>
                    <li>• 计算能力较强</li>
                  </ul>
                </div>
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <h4 className="font-semibold text-yellow-800 mb-2 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    待改进点
                  </h4>
                  <ul className="text-sm text-yellow-700 space-y-1">
                    <li>• 公式应用需加强</li>
                    <li>• 解题步骤需规范</li>
                    <li>• 细心程度待提高</li>
                  </ul>
                </div>
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="font-semibold text-blue-800 mb-2 flex items-center gap-2">
                    <Lightbulb className="w-4 h-4" />
                    学习建议
                  </h4>
                  <ul className="text-sm text-blue-700 space-y-1">
                    <li>• 多做专项练习</li>
                    <li>• 注重解题规范</li>
                    <li>• 定期复习巩固</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Enhanced Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <Button variant="outline" className="gap-2 bg-transparent">
          <Download className="w-4 h-4" />
          下载详细报告
        </Button>
        <Button variant="outline" className="gap-2 bg-transparent">
          <Share2 className="w-4 h-4" />
          分享给家长
        </Button>
        <Button variant="outline" className="gap-2 bg-transparent">
          <Clock className="w-4 h-4" />
          查看历史记录
        </Button>
        <Button className="gap-2">
          <RefreshCw className="w-4 h-4" />
          开始针对练习
        </Button>
      </div>
    </div>
  )
}
