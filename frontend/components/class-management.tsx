"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  Plus,
  Search,
  Settings,
  UserPlus,
  UserMinus,
  Copy,
  QrCode,
  Download,
  Upload,
  Crown,
  Shield,
  User,
  MoreHorizontal,
  Eye,
  Trash2,
} from "lucide-react"
import { CompletionAnimation, useCompletionAnimation } from "./completion-animations"

interface ClassInfo {
  id: string
  name: string
  description: string
  code: string
  teacherName: string
  studentCount: number
  subject: string
  grade: string
  isOwner: boolean
  role: "owner" | "teacher" | "student"
  createdAt: string
}

interface Student {
  id: string
  name: string
  email: string
  avatar?: string
  studentId: string
  joinDate: string
  lastActive: string
  averageScore: number
  assignmentCount: number
}

interface ClassManagementProps {
  userRole: "student" | "teacher" | "parent"
  currentClasses: ClassInfo[]
  onClassCreate: (classData: any) => void
  onClassJoin: (code: string) => void
  onClassLeave: (classId: string) => void
}

export function ClassManagement({
  userRole,
  currentClasses,
  onClassCreate,
  onClassJoin,
  onClassLeave,
}: ClassManagementProps) {
  const [selectedClass, setSelectedClass] = useState<ClassInfo | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showJoinDialog, setShowJoinDialog] = useState(false)
  const [joinCode, setJoinCode] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const { animation, showAnimation, hideAnimation } = useCompletionAnimation()

  // Mock student data
  const mockStudents: Student[] = [
    {
      id: "1",
      name: "张小明",
      email: "zhang@example.com",
      studentId: "2024001",
      joinDate: "2024-09-01",
      lastActive: "2小时前",
      averageScore: 85.6,
      assignmentCount: 12,
    },
    {
      id: "2",
      name: "李小红",
      email: "li@example.com",
      studentId: "2024002",
      joinDate: "2024-09-01",
      lastActive: "1天前",
      averageScore: 92.3,
      assignmentCount: 15,
    },
    {
      id: "3",
      name: "王小华",
      email: "wang@example.com",
      studentId: "2024003",
      joinDate: "2024-09-02",
      lastActive: "3小时前",
      averageScore: 78.9,
      assignmentCount: 10,
    },
  ]

  const filteredStudents = mockStudents.filter(
    (student) =>
      student.name.toLowerCase().includes(searchTerm.toLowerCase()) || student.studentId.includes(searchTerm),
  )

  const handleCreateClass = (formData: FormData) => {
    const classData = {
      name: formData.get("className"),
      description: formData.get("description"),
      subject: formData.get("subject"),
      grade: formData.get("grade"),
    }
    onClassCreate(classData)
    setShowCreateDialog(false)
    showAnimation("success", `班级"${classData.name}"创建成功！`)
  }

  const handleJoinClass = () => {
    onClassJoin(joinCode)
    setShowJoinDialog(false)
    setJoinCode("")
    showAnimation("success", "成功加入班级！")
  }

  const handleCopyInviteCode = (code: string) => {
    navigator.clipboard.writeText(code)
    showAnimation("success", "邀请码已复制到剪贴板！")
  }

  const handleExportStudents = () => {
    showAnimation("success", "学生名单导出成功！")
  }

  const handleImportStudents = () => {
    showAnimation("progress", "正在批量导入学生...")
  }

  const handleSaveSettings = () => {
    showAnimation("success", "班级设置保存成功！")
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "owner":
        return <Crown className="w-4 h-4 text-yellow-500" />
      case "teacher":
        return <Shield className="w-4 h-4 text-blue-500" />
      default:
        return <User className="w-4 h-4 text-gray-500" />
    }
  }

  const getRoleName = (role: string) => {
    switch (role) {
      case "owner":
        return "班主任"
      case "teacher":
        return "教师"
      default:
        return "学生"
    }
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {animation && (
        <CompletionAnimation type={animation.type} message={animation.message} onComplete={hideAnimation} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">班级管理</h2>
          <p className="text-muted-foreground">管理您的班级和学生</p>
        </div>
        <div className="flex gap-2">
          {userRole === "teacher" && (
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <DialogTrigger asChild>
                <Button className="hover:scale-105 transition-transform duration-200">
                  <Plus className="w-4 h-4 mr-2" />
                  创建班级
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>创建新班级</DialogTitle>
                </DialogHeader>
                <form action={handleCreateClass} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="className">班级名称</Label>
                    <Input id="className" name="className" placeholder="例如：高三(1)班" required />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="subject">科目</Label>
                    <Select name="subject" required>
                      <SelectTrigger>
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
                  <div className="space-y-2">
                    <Label htmlFor="grade">年级</Label>
                    <Select name="grade" required>
                      <SelectTrigger>
                        <SelectValue placeholder="选择年级" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="grade7">初一</SelectItem>
                        <SelectItem value="grade8">初二</SelectItem>
                        <SelectItem value="grade9">初三</SelectItem>
                        <SelectItem value="grade10">高一</SelectItem>
                        <SelectItem value="grade11">高二</SelectItem>
                        <SelectItem value="grade12">高三</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">班级描述</Label>
                    <Textarea id="description" name="description" placeholder="简单描述这个班级..." />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                      取消
                    </Button>
                    <Button type="submit" className="hover:scale-105 transition-transform duration-200">
                      创建班级
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          )}

          <Dialog open={showJoinDialog} onOpenChange={setShowJoinDialog}>
            <DialogTrigger asChild>
              <Button variant="outline" className="hover:scale-105 transition-transform duration-200 bg-transparent">
                <UserPlus className="w-4 h-4 mr-2" />
                加入班级
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>加入班级</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="joinCode">班级邀请码</Label>
                  <Input
                    id="joinCode"
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value)}
                    placeholder="输入6位邀请码"
                    maxLength={6}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowJoinDialog(false)}>
                    取消
                  </Button>
                  <Button
                    onClick={handleJoinClass}
                    disabled={joinCode.length !== 6}
                    className="hover:scale-105 transition-transform duration-200"
                  >
                    加入班级
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Class List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {currentClasses.map((classInfo, index) => (
          <Card
            key={classInfo.id}
            className="cursor-pointer hover:shadow-md hover:scale-105 transition-all duration-300 animate-fade-in-up"
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg">{classInfo.name}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">{classInfo.description}</p>
                </div>
                <Badge className="flex items-center gap-1 animate-pulse-glow">
                  {getRoleIcon(classInfo.role)}
                  {getRoleName(classInfo.role)}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">教师</span>
                  <span className="font-medium">{classInfo.teacherName}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">学生数量</span>
                  <span className="font-medium animate-pulse-scale">{classInfo.studentCount}人</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">科目</span>
                  <Badge variant="outline">{classInfo.subject}</Badge>
                </div>
                <div className="flex gap-2 pt-2">
                  <Button
                    size="sm"
                    className="flex-1 hover:scale-105 transition-transform duration-200"
                    onClick={() => setSelectedClass(classInfo)}
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    查看详情
                  </Button>
                  {classInfo.isOwner && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="hover:scale-110 transition-transform duration-200 bg-transparent"
                    >
                      <Settings className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Class Detail Dialog */}
      {selectedClass && (
        <Dialog open={!!selectedClass} onOpenChange={() => setSelectedClass(null)}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {selectedClass.name}
                <Badge className="flex items-center gap-1 animate-pulse-glow">
                  {getRoleIcon(selectedClass.role)}
                  {getRoleName(selectedClass.role)}
                </Badge>
              </DialogTitle>
            </DialogHeader>

            <Tabs defaultValue="overview" className="space-y-4">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">概览</TabsTrigger>
                <TabsTrigger value="students">学生管理</TabsTrigger>
                <TabsTrigger value="invite">邀请管理</TabsTrigger>
                <TabsTrigger value="settings">班级设置</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card className="animate-fade-in-up">
                    <CardHeader>
                      <CardTitle className="text-lg">班级信息</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">班级名称</span>
                        <span className="font-medium">{selectedClass.name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">科目</span>
                        <Badge variant="outline">{selectedClass.subject}</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">年级</span>
                        <span className="font-medium">{selectedClass.grade}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">创建时间</span>
                        <span className="font-medium">{selectedClass.createdAt}</span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
                    <CardHeader>
                      <CardTitle className="text-lg">统计数据</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">学生总数</span>
                        <span className="font-medium text-2xl animate-pulse-scale">{selectedClass.studentCount}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">平均分</span>
                        <span className="font-medium text-2xl animate-pulse-scale">85.6</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">作业完成率</span>
                        <span className="font-medium text-2xl animate-pulse-scale">92%</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="students" className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="搜索学生姓名或学号..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  {selectedClass.isOwner && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleImportStudents}
                        className="hover:scale-105 transition-transform duration-200 bg-transparent"
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        批量导入
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleExportStudents}
                        className="hover:scale-105 transition-transform duration-200 bg-transparent"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        导出名单
                      </Button>
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  {filteredStudents.map((student, index) => (
                    <Card
                      key={student.id}
                      className="animate-fade-in-up hover:scale-[1.02] transition-transform duration-200"
                      style={{ animationDelay: `${index * 0.1}s` }}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Avatar>
                              <AvatarImage src={student.avatar || "/placeholder.svg"} />
                              <AvatarFallback>{student.name[0]}</AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium">{student.name}</p>
                              <p className="text-sm text-muted-foreground">学号: {student.studentId}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <p className="text-sm font-medium">
                                平均分: <span className="animate-pulse-scale">{student.averageScore}</span>
                              </p>
                              <p className="text-xs text-muted-foreground">作业: {student.assignmentCount}份</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-muted-foreground">最后活跃</p>
                              <p className="text-sm">{student.lastActive}</p>
                            </div>
                            {selectedClass.isOwner && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="hover:scale-110 transition-transform duration-200"
                              >
                                <MoreHorizontal className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="invite" className="space-y-4">
                <Card className="animate-fade-in-up">
                  <CardHeader>
                    <CardTitle>邀请码管理</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium">班级邀请码</p>
                        <p className="text-2xl font-mono font-bold text-primary animate-pulse-glow">
                          {selectedClass.code}
                        </p>
                        <p className="text-sm text-muted-foreground">学生可使用此邀请码加入班级</p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopyInviteCode(selectedClass.code)}
                          className="hover:scale-105 transition-transform duration-200"
                        >
                          <Copy className="w-4 h-4 mr-2" />
                          复制
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="hover:scale-105 transition-transform duration-200 bg-transparent"
                        >
                          <QrCode className="w-4 h-4 mr-2" />
                          二维码
                        </Button>
                      </div>
                    </div>

                    {selectedClass.isOwner && (
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          className="hover:scale-105 transition-transform duration-200 bg-transparent"
                        >
                          重新生成邀请码
                        </Button>
                        <Button
                          variant="outline"
                          className="hover:scale-105 transition-transform duration-200 bg-transparent"
                        >
                          设置邀请限制
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="settings" className="space-y-4">
                {selectedClass.isOwner ? (
                  <div className="space-y-4">
                    <Card className="animate-fade-in-up">
                      <CardHeader>
                        <CardTitle>班级设置</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-2">
                          <Label>班级名称</Label>
                          <Input defaultValue={selectedClass.name} />
                        </div>
                        <div className="space-y-2">
                          <Label>班级描述</Label>
                          <Textarea defaultValue={selectedClass.description} />
                        </div>
                        <Button
                          onClick={handleSaveSettings}
                          className="hover:scale-105 transition-transform duration-200"
                        >
                          保存更改
                        </Button>
                      </CardContent>
                    </Card>

                    <Card className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
                      <CardHeader>
                        <CardTitle className="text-destructive">危险操作</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="destructive" className="hover:scale-105 transition-transform duration-200">
                              <Trash2 className="w-4 h-4 mr-2" />
                              删除班级
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>确认删除班级</AlertDialogTitle>
                              <AlertDialogDescription>
                                此操作将永久删除班级"{selectedClass.name}
                                "及其所有数据，包括学生信息、作业记录等。此操作不可撤销。
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>取消</AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-destructive text-destructive-foreground"
                                onClick={() => {
                                  onClassLeave(selectedClass.id)
                                  setSelectedClass(null)
                                  showAnimation("success", "班级已删除")
                                }}
                              >
                                确认删除
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </CardContent>
                    </Card>
                  </div>
                ) : (
                  <Card className="animate-fade-in-up">
                    <CardHeader>
                      <CardTitle>班级操作</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="destructive" className="hover:scale-105 transition-transform duration-200">
                            <UserMinus className="w-4 h-4 mr-2" />
                            退出班级
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>确认退出班级</AlertDialogTitle>
                            <AlertDialogDescription>
                              您确定要退出班级"{selectedClass.name}"吗？退出后您将无法查看班级内容和作业。
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>取消</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => {
                                onClassLeave(selectedClass.id)
                                setSelectedClass(null)
                                showAnimation("success", "已退出班级")
                              }}
                            >
                              确认退出
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
