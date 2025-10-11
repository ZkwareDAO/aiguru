"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  BarChart3,
  TrendingUp,
  Download,
  Share2,
  Target,
  Clock,
  BookOpen,
  Brain,
  Zap,
  Star,
  AlertTriangle,
  CheckCircle,
} from "lucide-react"
import {
  LineChart,
  Line,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  ComposedChart,
} from "recharts"
import { CompletionAnimation, useCompletionAnimation } from "./completion-animations"

// Mock data for reports
const weeklyScoreData = [
  { week: "第1周", score: 75, assignments: 3, errors: 8 },
  { week: "第2周", score: 78, assignments: 4, errors: 6 },
  { week: "第3周", score: 82, assignments: 5, errors: 5 },
  { week: "第4周", score: 85, assignments: 4, errors: 4 },
  { week: "第5周", score: 88, assignments: 3, errors: 3 },
  { week: "第6周", score: 92, assignments: 5, errors: 2 },
]

const monthlyProgressData = [
  { month: "9月", math: 78, english: 82, physics: 75, chemistry: 80 },
  { month: "10月", math: 82, english: 85, physics: 78, chemistry: 83 },
  { month: "11月", math: 85, english: 88, physics: 82, chemistry: 86 },
  { month: "12月", math: 88, english: 90, physics: 85, chemistry: 88 },
  { month: "1月", math: 92, english: 92, physics: 88, chemistry: 90 },
]

const subjectPerformanceData = [
  { subject: "数学", current: 92, target: 95, improvement: 14 },
  { subject: "英语", current: 88, target: 90, improvement: 10 },
  { subject: "物理", current: 85, target: 88, improvement: 8 },
  { subject: "化学", current: 82, target: 85, improvement: 6 },
  { subject: "生物", current: 86, target: 88, improvement: 12 },
]

const errorTypeDistribution = [
  { name: "知识点错误", value: 35, color: "#ef4444" },
  { name: "计算错误", value: 28, color: "#f97316" },
  { name: "逻辑错误", value: 22, color: "#eab308" },
  { name: "粗心错误", value: 15, color: "#22c55e" },
]

const studyTimeData = [
  { day: "周一", time: 2.5, efficiency: 85 },
  { day: "周二", time: 3.0, efficiency: 88 },
  { day: "周三", time: 2.8, efficiency: 82 },
  { day: "周四", time: 3.2, efficiency: 90 },
  { day: "周五", time: 2.0, efficiency: 75 },
  { day: "周六", time: 4.5, efficiency: 92 },
  { day: "周日", time: 4.0, efficiency: 88 },
]

interface LearningReportsProps {
  userRole: "student" | "teacher" | "parent"
}

export function LearningReports({ userRole }: LearningReportsProps) {
  const [selectedPeriod, setSelectedPeriod] = useState("month")
  const [selectedSubject, setSelectedSubject] = useState("all")
  const { animation, showAnimation, hideAnimation } = useCompletionAnimation()

  const handleExportReport = () => {
    showAnimation("success", "学习报告PDF导出成功！")
  }

  const handleShareReport = () => {
    showAnimation("success", "学习报告分享链接已生成！")
  }

  const handleGoalAchievement = (goalType: string) => {
    showAnimation("achievement", `恭喜！${goalType}目标达成！`)
  }

  const handleStartRecommendation = (type: string) => {
    showAnimation("progress", `开始${type}，加油学习！`)
  }

  const renderOverviewStats = () => (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card className="hover:scale-105 transition-transform duration-300">
        <CardContent className="p-4 text-center">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-bold animate-pulse-scale">88.5</p>
          <p className="text-xs text-muted-foreground">平均分</p>
          <div className="flex items-center justify-center gap-1 mt-1">
            <TrendingUp className="w-3 h-3 text-green-500 animate-bounce" />
            <span className="text-xs text-green-600">+5.2</span>
          </div>
        </CardContent>
      </Card>
      <Card className="hover:scale-105 transition-transform duration-300">
        <CardContent className="p-4 text-center">
          <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-2">
            <Target className="w-4 h-4 text-green-600" />
          </div>
          <p className="text-2xl font-bold animate-pulse-scale">92%</p>
          <p className="text-xs text-muted-foreground">目标达成率</p>
          <div className="flex items-center justify-center gap-1 mt-1">
            <TrendingUp className="w-3 h-3 text-green-500 animate-bounce" />
            <span className="text-xs text-green-600">+8%</span>
          </div>
        </CardContent>
      </Card>
      <Card className="hover:scale-105 transition-transform duration-300">
        <CardContent className="p-4 text-center">
          <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-2">
            <BookOpen className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-bold animate-pulse-scale">24</p>
          <p className="text-xs text-muted-foreground">完成作业</p>
          <div className="flex items-center justify-center gap-1 mt-1">
            <CheckCircle className="w-3 h-3 text-green-500 animate-bounce" />
            <span className="text-xs text-green-600">100%</span>
          </div>
        </CardContent>
      </Card>
      <Card className="hover:scale-105 transition-transform duration-300">
        <CardContent className="p-4 text-center">
          <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center mx-auto mb-2">
            <Clock className="w-4 h-4 text-orange-600" />
          </div>
          <p className="text-2xl font-bold animate-pulse-scale">3.2h</p>
          <p className="text-xs text-muted-foreground">日均学习</p>
          <div className="flex items-center justify-center gap-1 mt-1">
            <TrendingUp className="w-3 h-3 text-green-500 animate-bounce" />
            <span className="text-xs text-green-600">+0.5h</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderScoreTrends = () => (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            成绩趋势分析
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={selectedPeriod === "week" ? "default" : "outline"}
              onClick={() => setSelectedPeriod("week")}
              className="hover:scale-105 transition-transform duration-200"
            >
              周报
            </Button>
            <Button
              size="sm"
              variant={selectedPeriod === "month" ? "default" : "outline"}
              onClick={() => setSelectedPeriod("month")}
              className="hover:scale-105 transition-transform duration-200"
            >
              月报
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            {selectedPeriod === "week" ? (
              <ComposedChart data={weeklyScoreData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="score"
                  fill="#22c55e"
                  fillOpacity={0.3}
                  stroke="#22c55e"
                />
                <Bar yAxisId="right" dataKey="errors" fill="#ef4444" />
                <Line yAxisId="left" type="monotone" dataKey="score" stroke="#22c55e" strokeWidth={3} />
              </ComposedChart>
            ) : (
              <LineChart data={monthlyProgressData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="math" stroke="#3b82f6" name="数学" strokeWidth={2} />
                <Line type="monotone" dataKey="english" stroke="#ef4444" name="英语" strokeWidth={2} />
                <Line type="monotone" dataKey="physics" stroke="#8b5cf6" name="物理" strokeWidth={2} />
                <Line type="monotone" dataKey="chemistry" stroke="#f59e0b" name="化学" strokeWidth={2} />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )

  const renderSubjectAnalysis = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="animate-fade-in-up">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            各科目表现
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {subjectPerformanceData.map((subject, index) => (
              <div key={index} className="space-y-2 animate-fade-in-up" style={{ animationDelay: `${index * 0.1}s` }}>
                <div className="flex justify-between items-center">
                  <span className="font-medium">{subject.subject}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      目标: {subject.target}
                    </Badge>
                    <span className="font-bold animate-pulse-scale">{subject.current}分</span>
                  </div>
                </div>
                <div className="relative">
                  <Progress value={(subject.current / 100) * 100} className="h-3" />
                  <div
                    className="absolute top-0 h-3 bg-muted-foreground/20 rounded-full"
                    style={{ width: `${subject.target}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>当前: {subject.current}分</span>
                  <span className="text-green-600 animate-bounce">较上月 +{subject.improvement}分</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            错误类型分析
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={errorTypeDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {errorTypeDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {errorTypeDistribution.map((item, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-sm">{item.name}</span>
                <span className="text-xs text-muted-foreground">{item.value}%</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderStudyHabits = () => (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          学习习惯分析
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={studyTimeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Bar yAxisId="left" dataKey="time" fill="#3b82f6" name="学习时长(小时)" />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="efficiency"
                stroke="#22c55e"
                name="学习效率(%)"
                strokeWidth={2}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )

  const renderAIInsights = () => (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="w-5 h-5 animate-pulse" />
          AI智能分析报告
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg animate-fade-in-up hover:scale-[1.02] transition-transform duration-200">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-5 h-5 text-green-600 animate-bounce" />
              <h4 className="font-semibold text-green-800">学习优势</h4>
            </div>
            <p className="text-sm text-green-700">
              数学和物理科目表现优异，解题思路清晰，基础知识扎实。建议继续保持，可适当增加挑战性题目。
            </p>
          </div>

          <div
            className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg animate-fade-in-up hover:scale-[1.02] transition-transform duration-200"
            style={{ animationDelay: "0.1s" }}
          >
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-5 h-5 text-yellow-600 animate-pulse" />
              <h4 className="font-semibold text-yellow-800">需要改进</h4>
            </div>
            <p className="text-sm text-yellow-700">
              英语科目相对薄弱，主要问题集中在词汇量和语法应用。建议加强日常积累，多做阅读理解练习。
            </p>
          </div>

          <div
            className="p-4 bg-blue-50 border border-blue-200 rounded-lg animate-fade-in-up hover:scale-[1.02] transition-transform duration-200"
            style={{ animationDelay: "0.2s" }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-5 h-5 text-blue-600 animate-pulse" />
              <h4 className="font-semibold text-blue-800">学习建议</h4>
            </div>
            <p className="text-sm text-blue-700">
              学习时间分配合理，但周五效率偏低。建议调整学习计划，在精力充沛时安排重点科目。
            </p>
          </div>

          <div
            className="p-4 bg-purple-50 border border-purple-200 rounded-lg animate-fade-in-up hover:scale-[1.02] transition-transform duration-200"
            style={{ animationDelay: "0.3s" }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Star className="w-5 h-5 text-purple-600 animate-pulse" />
              <h4 className="font-semibold text-purple-800">进步表现</h4>
            </div>
            <p className="text-sm text-purple-700">
              本月整体成绩提升明显，错误率下降15%。保持当前学习节奏，预计下月可达到90分以上。
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )

  const renderGoalsAndRecommendations = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="animate-fade-in-up">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            学习目标设定
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 border border-border rounded-lg hover:scale-[1.02] transition-transform duration-200">
              <div className="flex justify-between items-center mb-2">
                <h4 className="font-semibold">短期目标 (本月)</h4>
                <Badge variant="secondary" className="animate-pulse">
                  进行中
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">各科平均分达到90分以上</p>
              <Progress value={85} className="mb-2" />
              <p className="text-xs text-muted-foreground">当前进度: 85% (88.5/90分)</p>
              <Button
                size="sm"
                className="mt-2 w-full hover:scale-105 transition-transform duration-200"
                onClick={() => handleGoalAchievement("短期")}
              >
                查看详情
              </Button>
            </div>

            <div className="p-4 border border-border rounded-lg hover:scale-[1.02] transition-transform duration-200">
              <div className="flex justify-between items-center mb-2">
                <h4 className="font-semibold">中期目标 (本学期)</h4>
                <Badge variant="outline">计划中</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">班级排名进入前5名</p>
              <Progress value={60} className="mb-2" />
              <p className="text-xs text-muted-foreground">当前进度: 60% (第8名/45人)</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 w-full bg-transparent hover:scale-105 transition-transform duration-200"
                onClick={() => handleGoalAchievement("中期")}
              >
                制定计划
              </Button>
            </div>

            <div className="p-4 border border-border rounded-lg hover:scale-[1.02] transition-transform duration-200">
              <div className="flex justify-between items-center mb-2">
                <h4 className="font-semibold">长期目标 (本学年)</h4>
                <Badge variant="outline">规划中</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">高考目标分数650分以上</p>
              <Progress value={75} className="mb-2" />
              <p className="text-xs text-muted-foreground">预估达成率: 75%</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 w-full bg-transparent hover:scale-105 transition-transform duration-200"
                onClick={() => handleGoalAchievement("长期")}
              >
                调整目标
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-5 h-5" />
            个性化推荐
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg hover:scale-[1.02] transition-transform duration-200">
              <h4 className="font-medium text-blue-800 mb-1">推荐练习</h4>
              <p className="text-sm text-blue-700">英语阅读理解专项训练 - 15道题</p>
              <Button
                size="sm"
                className="mt-2 w-full hover:scale-105 transition-transform duration-200"
                onClick={() => handleStartRecommendation("英语阅读理解专项训练")}
              >
                开始练习
              </Button>
            </div>

            <div className="p-3 bg-green-50 border border-green-200 rounded-lg hover:scale-[1.02] transition-transform duration-200">
              <h4 className="font-medium text-green-800 mb-1">复习计划</h4>
              <p className="text-sm text-green-700">数学二次函数错题回顾 - 8道题</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 w-full bg-transparent hover:scale-105 transition-transform duration-200"
                onClick={() => handleStartRecommendation("数学二次函数错题回顾")}
              >
                查看详情
              </Button>
            </div>

            <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg hover:scale-[1.02] transition-transform duration-200">
              <h4 className="font-medium text-purple-800 mb-1">学习资源</h4>
              <p className="text-sm text-purple-700">物理实验视频课程推荐</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 w-full bg-transparent hover:scale-105 transition-transform duration-200"
                onClick={() => handleStartRecommendation("物理实验视频课程")}
              >
                观看视频
              </Button>
            </div>

            <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg hover:scale-[1.02] transition-transform duration-200">
              <h4 className="font-medium text-orange-800 mb-1">时间管理</h4>
              <p className="text-sm text-orange-700">优化学习时间分配建议</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2 w-full bg-transparent hover:scale-105 transition-transform duration-200"
                onClick={() => handleStartRecommendation("学习时间分配优化")}
              >
                制定计划
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  return (
    <div className="space-y-6 animate-fade-in-up">
      {animation && (
        <CompletionAnimation type={animation.type} message={animation.message} onComplete={hideAnimation} />
      )}

      <Card className="bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20 animate-fade-in-up">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold mb-2">学习报告分析</h2>
              <p className="text-muted-foreground">
                {userRole === "student" && "个人学习数据分析与进步追踪"}
                {userRole === "teacher" && "班级整体学习情况分析"}
                {userRole === "parent" && "孩子学习情况详细报告"}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-2 bg-transparent hover:scale-105 transition-transform duration-200"
                onClick={handleExportReport}
              >
                <Download className="w-4 h-4" />
                导出PDF
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-2 bg-transparent hover:scale-105 transition-transform duration-200"
                onClick={handleShareReport}
              >
                <Share2 className="w-4 h-4" />
                分享报告
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">总览</TabsTrigger>
          <TabsTrigger value="trends">趋势分析</TabsTrigger>
          <TabsTrigger value="subjects">科目详情</TabsTrigger>
          <TabsTrigger value="goals">目标规划</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {renderOverviewStats()}
          {renderScoreTrends()}
          {renderAIInsights()}
        </TabsContent>

        <TabsContent value="trends" className="space-y-6">
          {renderOverviewStats()}
          {renderScoreTrends()}
          {renderStudyHabits()}
        </TabsContent>

        <TabsContent value="subjects" className="space-y-6">
          {renderSubjectAnalysis()}
          {renderStudyHabits()}
        </TabsContent>

        <TabsContent value="goals" className="space-y-6">
          {renderGoalsAndRecommendations()}
          {renderAIInsights()}
        </TabsContent>
      </Tabs>
    </div>
  )
}
