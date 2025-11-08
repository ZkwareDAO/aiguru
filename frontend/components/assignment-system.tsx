"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Switch } from "@/components/ui/switch"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  BookOpen,
  Plus,
  CalendarIcon,
  Clock,
  Users,
  FileText,
  Upload,
  Eye,
  Edit,
  CheckCircle,
  Target,
  Award,
  TrendingUp,
  Search,
  MoreHorizontal,
} from "lucide-react"
import { format } from "date-fns"
import { zhCN } from "date-fns/locale"

interface Assignment {
  id: string
  title: string
  description: string
  subject: string
  dueDate: string
  createdDate: string
  totalPoints: number
  attachments: string[]
  rubric: string
  aiInstructions: string
  classId: string
  className: string
  status: "draft" | "published" | "closed"
  submissionCount: number
  totalStudents: number
  averageScore?: number
}

interface Submission {
  id: string
  assignmentId: string
  studentId: string
  studentName: string
  studentAvatar?: string
  content: string
  attachments: string[]
  submittedAt: string
  score?: number
  feedback?: string
  status: "submitted" | "graded" | "returned"
  aiAnalysis?: {
    strengths: string[]
    weaknesses: string[]
    suggestions: string[]
    knowledgePoints: string[]
  }
}

interface AssignmentSystemProps {
  userRole: "student" | "teacher" | "parent"
  currentUser: {
    id: string
    name: string
    classes: string[]
  }
}

export function AssignmentSystem({ userRole, currentUser }: AssignmentSystemProps) {
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showSubmissionDialog, setShowSubmissionDialog] = useState(false)
  const [selectedDate, setSelectedDate] = useState<Date>()
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [searchTerm, setSearchTerm] = useState("")

  // Mock data
  const mockAssignments: Assignment[] = [
    {
      id: "assign-1",
      title: "二次函数综合练习",
      description: "完成教材第5章的所有练习题，重点关注函数图像和性质分析",
      subject: "数学",
      dueDate: "2024-01-30",
      createdDate: "2024-01-20",
      totalPoints: 100,
      attachments: ["练习题.pdf", "参考答案.pdf"],
      rubric: "按照解题步骤、计算准确性、图像绘制等维度评分",
      aiInstructions: "重点检查解题步骤的逻辑性，计算过程的准确性，以及对函数性质的理解程度",
      classId: "class-1",
      className: "高三(1)班",
      status: "published",
      submissionCount: 42,
      totalStudents: 45,
      averageScore: 85.6,
    },
    {
      id: "assign-2",
      title: "英语作文：我的理想",
      description: "写一篇关于个人理想的英语作文，不少于150词",
      subject: "英语",
      dueDate: "2024-01-28",
      createdDate: "2024-01-18",
      totalPoints: 100,
      attachments: ["写作要求.docx"],
      rubric: "语法准确性30%，词汇丰富度25%，内容深度25%，结构清晰度20%",
      aiInstructions: "检查语法错误，评估词汇使用的准确性和多样性，分析文章结构和内容的逻辑性",
      classId: "class-1",
      className: "高三(1)班",
      status: "published",
      submissionCount: 38,
      totalStudents: 45,
      averageScore: 78.2,
    },
    {
      id: "assign-3",
      title: "物理实验报告：自由落体运动",
      description: "根据实验数据分析自由落体运动规律，提交完整的实验报告",
      subject: "物理",
      dueDate: "2024-02-05",
      createdDate: "2024-01-25",
      totalPoints: 100,
      attachments: ["实验指导书.pdf", "数据记录表.xlsx"],
      rubric: "实验数据准确性40%，分析过程30%，结论合理性20%，报告格式10%",
      aiInstructions: "检查实验数据的合理性，评估分析过程的科学性，验证结论的正确性",
      classId: "class-1",
      className: "高三(1)班",
      status: "published",
      submissionCount: 35,
      totalStudents: 45,
    },
  ]

  const mockSubmissions: Submission[] = [
    {
      id: "sub-1",
      assignmentId: "assign-1",
      studentId: "student-1",
      studentName: "张小明",
      content: "这是我的数学作业答案...",
      attachments: ["我的答案.pdf"],
      submittedAt: "2024-01-29 14:30",
      score: 92,
      feedback: "解题思路清晰，计算准确，图像绘制规范。建议在函数性质分析部分更加深入。",
      status: "graded",
      aiAnalysis: {
        strengths: ["解题步骤完整", "计算准确", "图像绘制规范"],
        weaknesses: ["函数性质分析不够深入", "部分解释过于简单"],
        suggestions: ["加强对函数单调性的分析", "完善极值点的求解过程"],
        knowledgePoints: ["二次函数", "函数图像", "函数性质", "极值问题"],
      },
    },
    {
      id: "sub-2",
      assignmentId: "assign-1",
      studentId: "student-2",
      studentName: "李小红",
      content: "数学作业提交内容...",
      attachments: ["作业答案.jpg"],
      submittedAt: "2024-01-28 16:45",
      score: 88,
      status: "graded",
    },
  ]

  const filteredAssignments = mockAssignments.filter((assignment) => {
    const matchesSearch =
      assignment.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      assignment.subject.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterStatus === "all" || assignment.status === filterStatus
    return matchesSearch && matchesFilter
  })

  const handleCreateAssignment = (formData: FormData) => {
    const assignmentData = {
      title: formData.get("title"),
      description: formData.get("description"),
      subject: formData.get("subject"),
      dueDate: formData.get("dueDate"),
      totalPoints: formData.get("totalPoints"),
      rubric: formData.get("rubric"),
      aiInstructions: formData.get("aiInstructions"),
    }
    console.log("[v0] Creating assignment:", assignmentData)
    setShowCreateDialog(false)
  }

  const renderTeacherView = () => (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">作业管理</h2>
          <p className="text-muted-foreground">创建、管理和批改学生作业</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              布置作业
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-[95vw] sm:max-w-2xl max-h-[85vh] overflow-y-auto mx-2">
            <DialogHeader>
              <DialogTitle className="text-lg sm:text-xl">布置新作业</DialogTitle>
            </DialogHeader>
            <form action={handleCreateAssignment} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="title" className="text-sm">
                    作业标题
                  </Label>
                  <Input id="title" name="title" placeholder="例如：数学练习册第3章" required className="text-sm" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="subject" className="text-sm">
                    科目
                  </Label>
                  <Select name="subject" required>
                    <SelectTrigger className="text-sm">
                      <SelectValue placeholder="选择科目" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="math">数学</SelectItem>
                      <SelectItem value="chinese">语文</SelectItem>
                      <SelectItem value="english">英语</SelectItem>
                      <SelectItem value="physics">物理</SelectItem>
                      <SelectItem value="chemistry">化学</SelectItem>
                      <SelectItem value="biology">生物</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description" className="text-sm">
                  作业描述
                </Label>
                <Textarea
                  id="description"
                  name="description"
                  placeholder="详细描述作业要求..."
                  rows={3}
                  className="text-sm"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="dueDate" className="text-sm">
                    截止日期
                  </Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-start text-left font-normal bg-transparent text-sm"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {selectedDate ? format(selectedDate, "PPP", { locale: zhCN }) : "选择日期"}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0">
                      <Calendar mode="single" selected={selectedDate} onSelect={setSelectedDate} initialFocus />
                    </PopoverContent>
                  </Popover>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="totalPoints" className="text-sm">
                    总分
                  </Label>
                  <Input
                    id="totalPoints"
                    name="totalPoints"
                    type="number"
                    placeholder="100"
                    defaultValue="100"
                    className="text-sm"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="rubric" className="text-sm">
                  评分标准
                </Label>
                <Textarea
                  id="rubric"
                  name="rubric"
                  placeholder="描述评分标准和权重分配..."
                  rows={2}
                  className="text-sm"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="aiInstructions" className="text-sm">
                  AI批改指示
                </Label>
                <Textarea
                  id="aiInstructions"
                  name="aiInstructions"
                  placeholder="为AI批改系统提供具体的评分指导..."
                  rows={3}
                  className="text-sm"
                />
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-sm">附件</Label>
                  <Button type="button" variant="outline" size="sm" className="text-xs bg-transparent">
                    <Upload className="w-3 h-3 mr-1" />
                    上传文件
                  </Button>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch id="auto-grade" />
                  <Label htmlFor="auto-grade" className="text-sm">
                    启用AI自动批改
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch id="allow-late" />
                  <Label htmlFor="allow-late" className="text-sm">
                    允许逾期提交
                  </Label>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)} className="text-sm">
                  保存草稿
                </Button>
                <Button type="submit" className="text-sm">
                  发布作业
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="relative flex-1 max-w-full sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="搜索作业..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 text-sm"
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-full sm:w-32 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部</SelectItem>
            <SelectItem value="draft">草稿</SelectItem>
            <SelectItem value="published">已发布</SelectItem>
            <SelectItem value="closed">已截止</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Assignment List */}
      <div className="grid gap-3 sm:gap-4">
        {filteredAssignments.map((assignment) => (
          <Card key={assignment.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-4 sm:p-6">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-4 gap-3">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <h3 className="text-base sm:text-lg font-semibold">{assignment.title}</h3>
                    <Badge variant={assignment.status === "published" ? "default" : "secondary"} className="text-xs">
                      {assignment.status === "published" ? "已发布" : assignment.status === "draft" ? "草稿" : "已截止"}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {assignment.subject}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground text-xs sm:text-sm mb-3 line-clamp-2">{assignment.description}</p>
                  <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <CalendarIcon className="w-3 h-3 sm:w-4 sm:h-4" />
                      截止: {assignment.dueDate}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3 sm:w-4 sm:h-4" />
                      {assignment.submissionCount}/{assignment.totalStudents}
                    </span>
                    <span className="flex items-center gap-1">
                      <Target className="w-3 h-3 sm:w-4 sm:h-4" />
                      {assignment.totalPoints}分
                    </span>
                    {assignment.averageScore && (
                      <span className="flex items-center gap-1">
                        <Award className="w-3 h-3 sm:w-4 sm:h-4" />
                        平均: {assignment.averageScore}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-row sm:flex-col lg:flex-row gap-1 sm:gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedAssignment(assignment)}
                    className="text-xs flex-1 sm:flex-none"
                  >
                    <Eye className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
                    <span className="hidden sm:inline">查看详情</span>
                    <span className="sm:hidden">详情</span>
                  </Button>
                  <Button variant="outline" size="sm" className="text-xs flex-1 sm:flex-none bg-transparent">
                    <Edit className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
                    <span className="hidden sm:inline">编辑</span>
                    <span className="sm:hidden">编辑</span>
                  </Button>
                  <Button variant="outline" size="sm" className="text-xs bg-transparent">
                    <MoreHorizontal className="w-3 h-3 sm:w-4 sm:h-4" />
                  </Button>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <Progress
                  value={(assignment.submissionCount / assignment.totalStudents) * 100}
                  className="flex-1 mr-3 sm:mr-4"
                />
                <span className="text-xs sm:text-sm font-medium">
                  {Math.round((assignment.submissionCount / assignment.totalStudents) * 100)}%
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Assignment Detail Dialog */}
      {selectedAssignment && (
        <Dialog open={!!selectedAssignment} onOpenChange={() => setSelectedAssignment(null)}>
          <DialogContent className="max-w-[95vw] sm:max-w-4xl max-h-[85vh] overflow-y-auto mx-2">
            <DialogHeader>
              <DialogTitle className="flex flex-wrap items-center gap-2 text-base sm:text-lg">
                {selectedAssignment.title}
                <Badge
                  variant={selectedAssignment.status === "published" ? "default" : "secondary"}
                  className="text-xs"
                >
                  {selectedAssignment.status === "published"
                    ? "已发布"
                    : selectedAssignment.status === "draft"
                      ? "草稿"
                      : "已截止"}
                </Badge>
              </DialogTitle>
            </DialogHeader>

            <Tabs defaultValue="overview" className="space-y-4">
              <TabsList className="grid w-full grid-cols-3 text-xs sm:text-sm">
                <TabsTrigger value="overview">概览</TabsTrigger>
                <TabsTrigger value="submissions">提交</TabsTrigger>
                <TabsTrigger value="analytics">分析</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">作业信息</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">科目</span>
                        <Badge variant="outline">{selectedAssignment.subject}</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">总分</span>
                        <span className="font-medium">{selectedAssignment.totalPoints}分</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">截止时间</span>
                        <span className="font-medium">{selectedAssignment.dueDate}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">创建时间</span>
                        <span className="font-medium">{selectedAssignment.createdDate}</span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">提交统计</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">已提交</span>
                        <span className="font-medium text-2xl">{selectedAssignment.submissionCount}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">未提交</span>
                        <span className="font-medium text-2xl">
                          {selectedAssignment.totalStudents - selectedAssignment.submissionCount}
                        </span>
                      </div>
                      {selectedAssignment.averageScore && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">平均分</span>
                          <span className="font-medium text-2xl">{selectedAssignment.averageScore}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>作业描述</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">{selectedAssignment.description}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>评分标准</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">{selectedAssignment.rubric}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>AI批改指示</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">{selectedAssignment.aiInstructions}</p>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="submissions" className="space-y-4">
                <div className="space-y-3">
                  {mockSubmissions
                    .filter((sub) => sub.assignmentId === selectedAssignment.id)
                    .map((submission) => (
                      <Card key={submission.id}>
                        <CardContent className="p-4 sm:p-6">
                          <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-4 gap-3">
                            <div className="flex items-center gap-3">
                              <Avatar>
                                <AvatarImage src={submission.studentAvatar || "/placeholder.svg"} />
                                <AvatarFallback>{submission.studentName[0]}</AvatarFallback>
                              </Avatar>
                              <div>
                                <p className="font-medium">{submission.studentName}</p>
                                <p className="text-sm text-muted-foreground">提交时间: {submission.submittedAt}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              {submission.score && (
                                <div className="text-right">
                                  <p className="text-lg sm:text-xl font-bold">{submission.score}分</p>
                                  <Badge
                                    variant={submission.status === "graded" ? "default" : "secondary"}
                                    className="text-xs"
                                  >
                                    {submission.status === "graded"
                                      ? "已批改"
                                      : submission.status === "submitted"
                                        ? "待批改"
                                        : "已返回"}
                                  </Badge>
                                </div>
                              )}
                              <Button variant="outline" size="sm" className="text-xs bg-transparent">
                                <Eye className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
                                查看详情
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              </TabsContent>

              <TabsContent value="analytics" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>成绩分布</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {[
                          { range: "90-100分", count: 8, color: "bg-green-500" },
                          { range: "80-89分", count: 15, color: "bg-blue-500" },
                          { range: "70-79分", count: 12, color: "bg-yellow-500" },
                          { range: "60-69分", count: 5, color: "bg-orange-500" },
                          { range: "60分以下", count: 2, color: "bg-red-500" },
                        ].map((item, index) => (
                          <div key={index} className="flex items-center gap-3">
                            <div className={`w-4 h-4 rounded ${item.color}`} />
                            <span className="flex-1">{item.range}</span>
                            <span className="font-medium">{item.count}人</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>AI分析洞察</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                          <h4 className="font-semibold text-green-800 text-sm">优秀表现</h4>
                          <p className="text-xs text-green-700">大部分学生掌握了基本概念，解题思路清晰</p>
                        </div>
                        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                          <h4 className="font-semibold text-yellow-800 text-sm">需要关注</h4>
                          <p className="text-xs text-yellow-700">部分学生在计算准确性方面需要加强练习</p>
                        </div>
                        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <h4 className="font-semibold text-blue-800 text-sm">教学建议</h4>
                          <p className="text-xs text-blue-700">建议增加相关练习题，巩固薄弱知识点</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )

  const renderStudentView = () => (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">我的作业</h2>
          <p className="text-muted-foreground">查看和提交作业</p>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <Card>
          <CardContent className="p-3 sm:p-4 text-center">
            <BookOpen className="w-5 h-5 sm:w-6 sm:h-6 mx-auto mb-2 text-blue-500" />
            <p className="text-xl sm:text-2xl font-bold">5</p>
            <p className="text-xs text-muted-foreground">待完成</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 sm:p-4 text-center">
            <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 mx-auto mb-2 text-green-500" />
            <p className="text-xl sm:text-2xl font-bold">12</p>
            <p className="text-xs text-muted-foreground">已提交</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 sm:p-4 text-center">
            <Award className="w-5 h-5 sm:w-6 sm:h-6 mx-auto mb-2 text-yellow-500" />
            <p className="text-xl sm:text-2xl font-bold">85.6</p>
            <p className="text-xs text-muted-foreground">平均分</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 sm:p-4 text-center">
            <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 mx-auto mb-2 text-purple-500" />
            <p className="text-xl sm:text-2xl font-bold">+3.2</p>
            <p className="text-xs text-muted-foreground">本周提升</p>
          </CardContent>
        </Card>
      </div>

      {/* Assignment List */}
      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3 text-xs sm:text-sm">
          <TabsTrigger value="pending">待完成</TabsTrigger>
          <TabsTrigger value="submitted">已提交</TabsTrigger>
          <TabsTrigger value="graded">已批改</TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="space-y-3 sm:space-y-4">
          {mockAssignments.slice(0, 2).map((assignment) => (
            <Card key={assignment.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-4 gap-3">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <h3 className="text-base sm:text-lg font-semibold">{assignment.title}</h3>
                      <Badge variant="outline" className="text-xs">
                        {assignment.subject}
                      </Badge>
                      <Badge variant="destructive" className="text-xs">
                        <Clock className="w-3 h-3 mr-1" />
                        {assignment.dueDate}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground text-xs sm:text-sm mb-3 line-clamp-2">
                      {assignment.description}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-muted-foreground">
                      <span>总分: {assignment.totalPoints}分</span>
                      <span>班级: {assignment.className}</span>
                    </div>
                  </div>
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button className="text-xs sm:text-sm w-full sm:w-auto">
                        <Upload className="w-3 h-3 sm:w-4 sm:h-4 mr-2" />
                        提交作业
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-[95vw] sm:max-w-2xl mx-2">
                      <DialogHeader>
                        <DialogTitle className="text-base sm:text-lg">提交作业: {assignment.title}</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <Label className="text-sm">作业内容</Label>
                          <Textarea placeholder="输入您的作业答案..." rows={6} className="text-sm" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-sm">附件</Label>
                          <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-4 sm:p-6 text-center">
                            <Upload className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-2 text-muted-foreground" />
                            <p className="text-xs sm:text-sm text-muted-foreground">点击或拖拽文件到此处上传</p>
                          </div>
                        </div>
                        <div className="flex flex-col sm:flex-row justify-end gap-2">
                          <Button variant="outline" className="text-sm bg-transparent">
                            保存草稿
                          </Button>
                          <Button className="text-sm">提交作业</Button>
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="submitted" className="space-y-3 sm:space-y-4">
          <Card>
            <CardContent className="p-6 text-center">
              <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">暂无已提交的作业</h3>
              <p className="text-muted-foreground">您提交的作业将在这里显示</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="graded" className="space-y-3 sm:space-y-4">
          {mockSubmissions.map((submission) => (
            <Card key={submission.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between mb-4 gap-3">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <h3 className="text-base sm:text-lg font-semibold">二次函数综合练习</h3>
                      <Badge variant="outline" className="text-xs">
                        数学
                      </Badge>
                      <Badge variant="default" className="text-xs">
                        已批改
                      </Badge>
                    </div>
                    <p className="text-muted-foreground text-xs sm:text-sm mb-3">提交时间: {submission.submittedAt}</p>
                    <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm">
                      <span className="font-medium">得分: {submission.score}/100</span>
                      <span className="text-muted-foreground">班级平均: 85.6分</span>
                    </div>
                  </div>
                  <div className="text-center sm:text-right">
                    <div className="text-2xl sm:text-3xl font-bold text-primary mb-1">{submission.score}</div>
                    <Button variant="outline" size="sm" className="text-xs bg-transparent">
                      <Eye className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
                      查看详情
                    </Button>
                  </div>
                </div>

                {submission.feedback && (
                  <div className="mt-4 p-3 sm:p-4 bg-muted/50 rounded-lg">
                    <h4 className="font-semibold mb-2 text-sm">教师反馈</h4>
                    <p className="text-xs sm:text-sm text-muted-foreground">{submission.feedback}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  )

  return (
    <div className="animate-fade-in-up">
      {userRole === "teacher" && renderTeacherView()}
      {userRole === "student" && renderStudentView()}
      {userRole === "parent" && renderStudentView()}
    </div>
  )
}
