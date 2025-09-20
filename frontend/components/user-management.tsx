"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  User,
  Bell,
  Shield,
  Palette,
  Download,
  Upload,
  UserCheck,
  GraduationCap,
  Users,
  Eye,
  EyeOff,
} from "lucide-react"

interface UserProfile {
  id: string
  name: string
  email: string
  avatar?: string
  role: "student" | "teacher" | "parent"
  classes: string[]
  school?: string
  grade?: string
}

interface UserManagementProps {
  currentUser: UserProfile
  onRoleChange: (role: "student" | "teacher" | "parent") => void
  onProfileUpdate: (profile: Partial<UserProfile>) => void
}

export function UserManagement({ currentUser, onRoleChange, onProfileUpdate }: UserManagementProps) {
  const [showPassword, setShowPassword] = useState(false)
  const [notifications, setNotifications] = useState({
    assignments: true,
    grades: true,
    reminders: true,
    classUpdates: true,
  })

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "student":
        return <GraduationCap className="w-4 h-4" />
      case "teacher":
        return <UserCheck className="w-4 h-4" />
      case "parent":
        return <Users className="w-4 h-4" />
      default:
        return <User className="w-4 h-4" />
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case "student":
        return "bg-chart-2/10 text-chart-2"
      case "teacher":
        return "bg-chart-1/10 text-chart-1"
      case "parent":
        return "bg-chart-4/10 text-chart-4"
      default:
        return "bg-muted text-muted-foreground"
    }
  }

  return (
    <div className="space-y-6">
      {/* Profile Header */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <Avatar className="w-20 h-20">
              <AvatarImage src={currentUser.avatar || "/placeholder.svg"} />
              <AvatarFallback className="text-lg font-semibold">
                {currentUser.name
                  .split(" ")
                  .map((n) => n[0])
                  .join("")}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <h2 className="text-2xl font-bold">{currentUser.name}</h2>
              <p className="text-muted-foreground">{currentUser.email}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge className={getRoleColor(currentUser.role)}>
                  {getRoleIcon(currentUser.role)}
                  {currentUser.role === "student" ? "学生" : currentUser.role === "teacher" ? "教师" : "家长"}
                </Badge>
                {currentUser.school && <Badge variant="outline">{currentUser.school}</Badge>}
              </div>
            </div>
            <Button variant="outline" size="sm">
              <Upload className="w-4 h-4 mr-2" />
              更换头像
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="profile">个人信息</TabsTrigger>
          <TabsTrigger value="roles">角色管理</TabsTrigger>
          <TabsTrigger value="settings">系统设置</TabsTrigger>
          <TabsTrigger value="security">安全设置</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                基本信息
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">姓名</Label>
                  <Input id="name" defaultValue={currentUser.name} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">邮箱</Label>
                  <Input id="email" type="email" defaultValue={currentUser.email} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="school">学校</Label>
                  <Input id="school" defaultValue={currentUser.school} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="grade">年级/班级</Label>
                  <Input id="grade" defaultValue={currentUser.grade} />
                </div>
              </div>
              <Button>保存更改</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>加入的班级</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {currentUser.classes.map((className, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div>
                      <p className="font-medium">{className}</p>
                      <p className="text-sm text-muted-foreground">活跃班级</p>
                    </div>
                    <Button variant="outline" size="sm">
                      管理
                    </Button>
                  </div>
                ))}
                <Button variant="outline" className="w-full bg-transparent">
                  <Users className="w-4 h-4 mr-2" />
                  加入新班级
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                角色切换
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">您可以在不同角色之间切换，每个角色都有不同的功能和界面。</p>
              <div className="grid gap-4">
                {[
                  { role: "student", name: "学生模式", desc: "上传作业、查看批改结果、管理错题本" },
                  { role: "teacher", name: "教师模式", desc: "管理班级、布置作业、查看学生数据" },
                  { role: "parent", name: "家长模式", desc: "监控孩子学习、查看学习报告" },
                ].map((item) => (
                  <Card
                    key={item.role}
                    className={`cursor-pointer transition-all ${
                      currentUser.role === item.role ? "ring-2 ring-primary" : "hover:bg-muted/50"
                    }`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-10 h-10 rounded-lg flex items-center justify-center ${getRoleColor(item.role)}`}
                          >
                            {getRoleIcon(item.role)}
                          </div>
                          <div>
                            <h3 className="font-semibold">{item.name}</h3>
                            <p className="text-sm text-muted-foreground">{item.desc}</p>
                          </div>
                        </div>
                        <Button
                          variant={currentUser.role === item.role ? "default" : "outline"}
                          onClick={() => onRoleChange(item.role as any)}
                        >
                          {currentUser.role === item.role ? "当前角色" : "切换"}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                通知设置
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(notifications).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">
                      {key === "assignments"
                        ? "作业通知"
                        : key === "grades"
                          ? "成绩通知"
                          : key === "reminders"
                            ? "学习提醒"
                            : "班级动态"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {key === "assignments"
                        ? "新作业发布时通知"
                        : key === "grades"
                          ? "批改完成时通知"
                          : key === "reminders"
                            ? "学习计划提醒"
                            : "班级公告和活动"}
                    </p>
                  </div>
                  <Switch
                    checked={value}
                    onCheckedChange={(checked) => setNotifications((prev) => ({ ...prev, [key]: checked }))}
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="w-5 h-5" />
                界面设置
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>主题模式</Label>
                <Select defaultValue="system">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">浅色模式</SelectItem>
                    <SelectItem value="dark">深色模式</SelectItem>
                    <SelectItem value="system">跟随系统</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>语言设置</Label>
                <Select defaultValue="zh-CN">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="zh-CN">简体中文</SelectItem>
                    <SelectItem value="en-US">English</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="w-5 h-5" />
                数据管理
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">导出学习数据</p>
                  <p className="text-sm text-muted-foreground">下载您的所有学习记录和数据</p>
                </div>
                <Button variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  导出
                </Button>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">清除缓存</p>
                  <p className="text-sm text-muted-foreground">清除本地缓存数据</p>
                </div>
                <Button variant="outline">清除</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                密码安全
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current-password">当前密码</Label>
                <div className="relative">
                  <Input id="current-password" type={showPassword ? "text" : "password"} />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-password">新密码</Label>
                <Input id="new-password" type="password" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm-password">确认新密码</Label>
                <Input id="confirm-password" type="password" />
              </div>
              <Button>更新密码</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>登录设备</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { device: "iPhone 15 Pro", location: "北京", time: "刚刚", current: true },
                  { device: "Chrome on Windows", location: "上海", time: "2小时前", current: false },
                  { device: "iPad Air", location: "广州", time: "1天前", current: false },
                ].map((session, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div>
                      <p className="font-medium">{session.device}</p>
                      <p className="text-sm text-muted-foreground">
                        {session.location} • {session.time}
                        {session.current && " • 当前设备"}
                      </p>
                    </div>
                    {!session.current && (
                      <Button variant="outline" size="sm">
                        注销
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
