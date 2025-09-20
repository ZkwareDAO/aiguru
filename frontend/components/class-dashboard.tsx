"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ClassManagement } from "@/components/class-management"
import {
  Users,
  Trophy,
  TrendingUp,
  TrendingDown,
  BookOpen,
  Target,
  Award,
  Calendar,
  MessageSquare,
  Download,
  Plus,
  Eye,
  BarChart3,
  Clock,
  Star,
  AlertCircle,
  Settings,
} from "lucide-react"
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
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

interface Student {
  id: string
  name: string
  avatar: string
  score: number
  rank: number
  improvement: number
  assignments: number
  errorCount: number
  subjects: { [key: string]: number }
}

interface ClassData {
  name: string
  studentCount: number
  averageScore: number
  completionRate: number
  topPerformers: Student[]
  recentActivity: any[]
}

const mockStudents: Student[] = [
  {
    id: "1",
    name: "张小明",
    avatar: "/placeholder.svg?height=40&width=40",
    score: 92,
    rank: 1,
    improvement: 5,
    assignments: 15,
    errorCount: 3,
    subjects: { 数学: 95, 英语: 88, 物理: 93 },
  },
  {
    id: "2",
    name: "李小红",
    avatar: "/placeholder.svg?height=40&width=40",
    score: 88,
    rank: 2,
    improvement: 2,
    assignments: 14,
    errorCount: 5,
    subjects: { 数学: 85, 英语: 92, 物理: 87 },
  },
  {
    id: "3",
    name: "王小华",
    avatar: "/placeholder.svg?height=40&width=40",
    score: 85,
    rank: 3,
    improvement: -1,
    assignments: 13,
    errorCount: 8,
    subjects: { 数学: 82, 英语: 87, 物理: 86 },
  },
  {
    id: "4",
    name: "刘小强",
    avatar: "/placeholder.svg?height=40&width=40",
    score: 82,
    rank: 4,
    improvement: 3,
    assignments: 12,
    errorCount: 10,
    subjects: { 数学: 78, 英语: 85, 物理: 83 },
  },
  {
    id: "5",
    name: "陈小美",
    avatar: "/placeholder.svg?height=40&width=40",
    score: 79,
    rank: 5,
    improvement: -2,
    assignments: 11,
    errorCount: 12,
    subjects: { 数学: 75, 英语: 82, 物理: 80 },
  },
]

const classPerformanceData = [
  { week: "第1周", average: 75, myScore: 78 },
  { week: "第2周", average: 77, myScore: 82 },
  { week: "第3周", average: 79, myScore: 85 },
  { week: "第4周", average: 81, myScore: 88 },
  { week: "第5周", average: 83, myScore: 92 },
]

const subjectRadarData = [
  { subject: "数学", fullMark: 100, myScore: 85, classAvg: 78 },
  { subject: "英语", fullMark: 100, myScore: 88, classAvg: 82 },
  { subject: "物理", fullMark: 100, myScore: 92, classAvg: 85 },
  { subject: "化学", fullMark: 100, myScore: 79, classAvg: 80 },
  { subject: "生物", fullMark: 100, myScore: 86, classAvg: 83 },
]

interface ClassDashboardProps {
  userRole: "student" | "teacher" | "parent"
}

export function ClassDashboard({ userRole }: ClassDashboardProps) {
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null)
  const [showClassManagement, setShowClassManagement] = useState(false)

  const mockClasses = [
    {
      id: "class-1",
      name: "高三(1)班",
      description: "数学重点班",
      code: "ABC123",
      teacherName: "李老师",
      studentCount: 45,
      subject: "数学",
      grade: "高三",
      isOwner: userRole === "teacher",
      role: userRole === "teacher" ? ("owner" as const) : ("student" as const),
      createdAt: "2024-09-01",
    },
    {
      id: "class-2",
      name: "数学竞赛班",
      description: "数学竞赛培训",
      code: "DEF456",
      teacherName: "王老师",
      studentCount: 25,
      subject: "数学",
      grade: "高三",
      isOwner: false,
      role: "student" as const,
      createdAt: "2024-09-15",
    },
  ]

  const handleClassCreate = (classData: any) => {
    console.log("[v0] Creating class:", classData)
  }

  const handleClassJoin = (code: string) => {
    console.log("[v0] Joining class with code:", code)
  }

  const handleClassLeave = (classId: string) => {
    console.log("[v0] Leaving class:", classId)
  }

  if (showClassManagement) {
    return (
      <div className="animate-fade-in-up space-y-4">
        <Button variant="outline" onClick={() => setShowClassManagement(false)} className="mb-4">
          ← 返回班级仪表板
        </Button>
        <ClassManagement
          userRole={userRole}
          currentClasses={mockClasses}
          onClassCreate={handleClassCreate}
          onClassJoin={handleClassJoin}
          onClassLeave={handleClassLeave}
        />
      </div>
    )
  }

  const renderStudentView = () => (
    <div className="space-y-6">
      {/* Class Overview */}
      <Card className="bg-gradient-to-br from-primary/10 to-accent/10 border-primary/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold mb-2">高三(1)班</h2>
              <p className="text-muted-foreground">班级排名: 第3名 / 45人</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-3xl font-bold text-primary">85.6</div>
                <p className="text-sm text-muted-foreground">我的平均分</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setShowClassManagement(true)}>
                <Settings className="w-4 h-4 mr-2" />
                班级管理
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Comparison */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            成绩对比趋势
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={classPerformanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="average" stroke="#94a3b8" name="班级平均" strokeDasharray="5 5" />
                <Line type="monotone" dataKey="myScore" stroke="#22c55e" name="我的成绩" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Subject Radar */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              各科目表现
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={subjectRadarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} />
                  <Radar name="我的成绩" dataKey="myScore" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                  <Radar name="班级平均" dataKey="classAvg" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.1} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Class Ranking */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="w-5 h-5" />
              班级排行榜
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockStudents.slice(0, 5).map((student, index) => (
                <div key={student.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-bold text-sm">
                    {index + 1}
                  </div>
                  <Avatar className="w-8 h-8">
                    <AvatarImage src={student.avatar || "/placeholder.svg"} />
                    <AvatarFallback>{student.name[0]}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{student.name}</p>
                    <p className="text-xs text-muted-foreground">{student.score}分</p>
                  </div>
                  <div className="flex items-center gap-1">
                    {student.improvement > 0 ? (
                      <TrendingUp className="w-3 h-3 text-green-500" />
                    ) : (
                      <TrendingDown className="w-3 h-3 text-red-500" />
                    )}
                    <span className="text-xs">{Math.abs(student.improvement)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Class Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <Users className="w-6 h-6 mx-auto mb-2 text-blue-500" />
            <p className="text-2xl font-bold">45</p>
            <p className="text-xs text-muted-foreground">班级人数</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <BookOpen className="w-6 h-6 mx-auto mb-2 text-green-500" />
            <p className="text-2xl font-bold">12</p>
            <p className="text-xs text-muted-foreground">本周作业</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Award className="w-6 h-6 mx-auto mb-2 text-yellow-500" />
            <p className="text-2xl font-bold">3</p>
            <p className="text-xs text-muted-foreground">我的排名</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Target className="w-6 h-6 mx-auto mb-2 text-purple-500" />
            <p className="text-2xl font-bold">92%</p>
            <p className="text-xs text-muted-foreground">完成率</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )

  const renderTeacherView = () => (
    <div className="space-y-6">
      {/* Class Overview */}
      <Card className="bg-gradient-to-br from-secondary/10 to-accent/10 border-secondary/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold mb-2">高三(1)班管理</h2>
              <p className="text-muted-foreground">45名学生 · 本周12份作业</p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" className="gap-2">
                <Plus className="w-4 h-4" />
                布置作业
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="gap-2 bg-transparent"
                onClick={() => setShowClassManagement(true)}
              >
                <Settings className="w-4 h-4" />
                班级管理
              </Button>
              <Button size="sm" variant="outline" className="gap-2 bg-transparent">
                <Download className="w-4 h-4" />
                导出报告
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">82.5</div>
              <p className="text-sm text-muted-foreground">班级平均分</p>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">89%</div>
              <p className="text-sm text-muted-foreground">作业完成率</p>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">15</div>
              <p className="text-sm text-muted-foreground">需要关注</p>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">8</div>
              <p className="text-sm text-muted-foreground">优秀学生</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="students" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="students">学生管理</TabsTrigger>
          <TabsTrigger value="analytics">数据分析</TabsTrigger>
          <TabsTrigger value="assignments">作业管理</TabsTrigger>
        </TabsList>

        <TabsContent value="students" className="space-y-4">
          {/* Student List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>学生列表</span>
                <Button size="sm" variant="outline" className="bg-transparent">
                  <Eye className="w-4 h-4 mr-1" />
                  批量查看
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockStudents.map((student) => (
                  <Card
                    key={student.id}
                    className="cursor-pointer hover:shadow-md transition-all duration-200"
                    onClick={() => setSelectedStudent(selectedStudent?.id === student.id ? null : student)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center gap-4">
                        <Avatar className="w-12 h-12">
                          <AvatarImage src={student.avatar || "/placeholder.svg"} />
                          <AvatarFallback>{student.name[0]}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold">{student.name}</h3>
                            <Badge variant="outline" className="text-xs">
                              第{student.rank}名
                            </Badge>
                            {student.improvement > 0 ? (
                              <Badge className="text-xs bg-green-100 text-green-700">↑{student.improvement}</Badge>
                            ) : student.improvement < 0 ? (
                              <Badge className="text-xs bg-red-100 text-red-700">
                                ↓{Math.abs(student.improvement)}
                              </Badge>
                            ) : null}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>平均分: {student.score}</span>
                            <span>作业: {student.assignments}份</span>
                            <span>错题: {student.errorCount}个</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold">{student.score}</div>
                          <Progress value={(student.score / 100) * 100} className="w-20 h-2" />
                        </div>
                      </div>

                      {selectedStudent?.id === student.id && (
                        <div className="mt-4 pt-4 border-t border-border animate-fade-in-up">
                          <div className="grid grid-cols-3 gap-4">
                            {Object.entries(student.subjects).map(([subject, score]) => (
                              <div key={subject} className="text-center p-3 bg-muted/50 rounded-lg">
                                <p className="font-medium">{subject}</p>
                                <p className="text-2xl font-bold text-primary">{score}</p>
                              </div>
                            ))}
                          </div>
                          <div className="flex gap-2 mt-4">
                            <Button size="sm" className="flex-1">
                              <MessageSquare className="w-4 h-4 mr-1" />
                              发送消息
                            </Button>
                            <Button size="sm" variant="outline" className="flex-1 bg-transparent">
                              <BarChart3 className="w-4 h-4 mr-1" />
                              详细报告
                            </Button>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          {/* Class Performance Analytics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>班级成绩分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        { range: "90-100", count: 8 },
                        { range: "80-89", count: 15 },
                        { range: "70-79", count: 12 },
                        { range: "60-69", count: 7 },
                        { range: "0-59", count: 3 },
                      ]}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="range" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="count" fill="#22c55e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>学习趋势分析</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={classPerformanceData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="week" />
                      <YAxis />
                      <Tooltip />
                      <Area type="monotone" dataKey="average" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* AI Insights */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                AI分析洞察
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="font-semibold text-blue-800 mb-2">班级整体表现</h4>
                  <p className="text-sm text-blue-700">
                    本周班级平均分较上周提升2.3分，整体呈上升趋势。数学科目表现突出，英语需要加强关注。
                  </p>
                </div>
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <h4 className="font-semibold text-yellow-800 mb-2">需要关注的学生</h4>
                  <p className="text-sm text-yellow-700">
                    陈小美、王小华等5名学生近期成绩有所下滑，建议加强个别辅导和家长沟通。
                  </p>
                </div>
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <h4 className="font-semibold text-green-800 mb-2">优秀表现</h4>
                  <p className="text-sm text-green-700">
                    张小明、李小红等8名学生表现优异，可以作为学习榜样，建议安排同伴辅导。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="assignments" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>作业管理</span>
                <Button size="sm" className="gap-2">
                  <Plus className="w-4 h-4" />
                  新建作业
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { title: "数学练习册第3章", subject: "数学", dueDate: "2024-01-25", submitted: 42, total: 45 },
                  { title: "英语作文：我的假期", subject: "英语", dueDate: "2024-01-24", submitted: 38, total: 45 },
                  { title: "物理实验报告", subject: "物理", dueDate: "2024-01-23", submitted: 45, total: 45 },
                ].map((assignment, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border border-border rounded-lg">
                    <div>
                      <h4 className="font-semibold">{assignment.title}</h4>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                        <Badge variant="outline">{assignment.subject}</Badge>
                        <span>截止: {assignment.dueDate}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold">
                        {assignment.submitted}/{assignment.total}
                      </div>
                      <Progress value={(assignment.submitted / assignment.total) * 100} className="w-20 h-2" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )

  const renderParentView = () => (
    <div className="space-y-6">
      {/* Child Overview */}
      <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <Avatar className="w-16 h-16">
              <AvatarImage src="/placeholder.svg?height=64&width=64" />
              <AvatarFallback>张</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-1">张小明的学习情况</h2>
              <p className="text-muted-foreground">高三(1)班 · 班级排名第3名</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-3xl font-bold text-blue-600">85.6</div>
                <p className="text-sm text-muted-foreground">平均分</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setShowClassManagement(true)}>
                <Settings className="w-4 h-4 mr-2" />
                班级信息
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <Star className="w-6 h-6 mx-auto mb-2 text-yellow-500" />
            <p className="text-2xl font-bold">3</p>
            <p className="text-xs text-muted-foreground">班级排名</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <TrendingUp className="w-6 h-6 mx-auto mb-2 text-green-500" />
            <p className="text-2xl font-bold">+5</p>
            <p className="text-xs text-muted-foreground">本周进步</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <BookOpen className="w-6 h-6 mx-auto mb-2 text-blue-500" />
            <p className="text-2xl font-bold">15</p>
            <p className="text-xs text-muted-foreground">完成作业</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Clock className="w-6 h-6 mx-auto mb-2 text-purple-500" />
            <p className="text-2xl font-bold">2.5h</p>
            <p className="text-xs text-muted-foreground">日均学习</p>
          </CardContent>
        </Card>
      </div>

      {/* Subject Performance */}
      <Card>
        <CardHeader>
          <CardTitle>各科目表现对比</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Object.entries(mockStudents[0].subjects).map(([subject, score]) => (
              <div key={subject} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{subject}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">班级平均: 78</span>
                    <span className="font-bold">我的成绩: {score}</span>
                  </div>
                </div>
                <div className="relative">
                  <Progress value={78} className="h-3 bg-gray-200" />
                  <Progress value={score} className="h-3 absolute top-0" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* AI Learning Suggestions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            AI学习建议
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <h4 className="font-semibold text-green-800 mb-2">优势科目</h4>
              <p className="text-sm text-green-700">数学和物理表现优秀，建议继续保持，可以适当增加挑战性题目。</p>
            </div>
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h4 className="font-semibold text-yellow-800 mb-2">需要提升</h4>
              <p className="text-sm text-yellow-700">英语成绩相对较弱，建议加强词汇积累和阅读理解练习。</p>
            </div>
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-semibold text-blue-800 mb-2">学习习惯</h4>
              <p className="text-sm text-blue-700">作业完成及时，学习态度认真，建议保持规律的复习计划。</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="w-5 h-5" />
            最近学习动态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { time: "今天 14:30", activity: "完成数学作业", score: "92分", type: "assignment" },
              { time: "昨天 16:45", activity: "英语单词测试", score: "85分", type: "test" },
              { time: "前天 10:20", activity: "物理实验报告", score: "95分", type: "report" },
            ].map((item, index) => (
              <div key={index} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                <div className="w-2 h-2 bg-primary rounded-full" />
                <div className="flex-1">
                  <p className="font-medium text-sm">{item.activity}</p>
                  <p className="text-xs text-muted-foreground">{item.time}</p>
                </div>
                <Badge variant="secondary">{item.score}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )

  return (
    <div className="animate-fade-in-up">
      {userRole === "student" && renderStudentView()}
      {userRole === "teacher" && renderTeacherView()}
      {userRole === "parent" && renderParentView()}
    </div>
  )
}
