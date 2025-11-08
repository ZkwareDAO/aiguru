"use client"

import { useState, useEffect } from "react"
import { BrandLaunchAnimation } from "@/components/brand-launch-animation"
import { HiddenNavigation } from "@/components/hidden-navigation"
import { UserManagement } from "@/components/user-management"
import { ClassDashboard } from "@/components/class-dashboard"
import { AssignmentSystem } from "@/components/assignment-system"
import { DataManagement } from "@/components/data-management"
import { Card, CardContent } from "@/components/ui/card"
import { Brain, BookOpen, Users, BarChart3, Award, TrendingUp } from "lucide-react"
import { AIGradingSystem } from "@/components/ai-grading-system"

export default function Home() {
  const [showLaunchAnimation, setShowLaunchAnimation] = useState(true)
  const [currentPage, setCurrentPage] = useState("home")
  const [currentUser, setCurrentUser] = useState({
    id: "user-1",
    name: "张老师",
    email: "zhang.teacher@school.edu.cn",
    role: "teacher" as "student" | "teacher" | "parent",
    avatar: "/placeholder.svg?height=40&width=40",
    classes: ["高三(1)班", "高三(2)班"],
    school: "北京市第一中学",
    grade: "高三",
  })

  useEffect(() => {
    console.log("[v0] Setting launch animation to true")
    setShowLaunchAnimation(true)
  }, [])

  const handleAnimationComplete = () => {
    console.log("[v0] Animation completed, hiding launch screen")
    setShowLaunchAnimation(false)
  }

  const handleRoleChange = (role: "student" | "teacher" | "parent") => {
    setCurrentUser((prev) => ({ ...prev, role }))
  }

  const handleProfileUpdate = (profile: Partial<typeof currentUser>) => {
    setCurrentUser((prev) => ({ ...prev, ...profile }))
  }

  if (showLaunchAnimation) {
    console.log("[v0] Rendering brand launch animation")
    return <BrandLaunchAnimation onComplete={handleAnimationComplete} />
  }

  const renderPage = () => {
    switch (currentPage) {
      case "assignments":
        return (
          <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-50 p-6">
            <AssignmentSystem userRole={currentUser.role} currentUser={currentUser} />
          </div>
        )
      case "classes":
        return (
          <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-50 p-6">
            <ClassDashboard userRole={currentUser.role} />
          </div>
        )
      case "grading":
        return (
          <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-50 p-2 sm:p-6">
            <AIGradingSystem />
          </div>
        )
      case "analytics":
        return (
          <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-50 p-6">
            <DataManagement userRole={currentUser.role} />
          </div>
        )
      case "settings":
        return (
          <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-50 p-6">
            <div className="max-w-4xl mx-auto">
              <UserManagement
                currentUser={currentUser}
                onRoleChange={handleRoleChange}
                onProfileUpdate={handleProfileUpdate}
              />
            </div>
          </div>
        )
      default:
        return (
          <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-cyan-50">
            <div className="container mx-auto px-4 sm:px-6 py-4 sm:py-8">
              <div className="space-y-6 sm:space-y-8">
                {/* Welcome card */}
                <Card className="card-hover animate-scale-in bg-gradient-to-br from-sky-100/50 via-blue-100/50 to-cyan-100/50 border-sky-200 overflow-hidden relative">
                  <div className="absolute inset-0 animate-shimmer"></div>
                  <CardContent className="p-4 sm:p-8 relative z-10">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                      <div className="space-y-3 flex-1">
                        <h1 className="text-2xl sm:text-4xl font-bold gradient-text">欢迎回来，{currentUser.name}！</h1>
                        <p className="text-slate-600 text-sm sm:text-lg max-w-2xl">
                          {currentUser.role === "teacher"
                            ? "今天有新的作业需要批改，AI助手已为您准备就绪"
                            : currentUser.role === "student"
                              ? "继续您的学习之旅，查看最新的作业反馈"
                              : "查看孩子的最新学习进展和成绩分析"}
                        </p>
                      </div>
                      <div className="flex items-center gap-4 sm:gap-6 w-full sm:w-auto justify-around sm:justify-end">
                        <div className="text-center animate-bounce-subtle delay-200">
                          <div className="text-2xl sm:text-4xl font-bold gradient-text">15</div>
                          <p className="text-xs sm:text-sm text-slate-500">
                            {currentUser.role === "teacher" ? "待批改" : "新消息"}
                          </p>
                        </div>
                        <div className="text-center animate-bounce-subtle delay-400">
                          <div className="text-2xl sm:text-4xl font-bold text-emerald-600">92%</div>
                          <p className="text-xs sm:text-sm text-slate-500">
                            {currentUser.role === "teacher" ? "批改准确率" : "完成率"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Stats grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
                  {[
                    {
                      icon: BookOpen,
                      value: currentUser.role === "teacher" ? "156" : "12",
                      label: currentUser.role === "teacher" ? "本月批改" : "本周作业",
                      color: "text-sky-500",
                      delay: "delay-100",
                    },
                    {
                      icon: Users,
                      value: currentUser.role === "teacher" ? "45" : "45",
                      label: currentUser.role === "teacher" ? "班级学生" : "班级同学",
                      color: "text-blue-500",
                      delay: "delay-200",
                    },
                    {
                      icon: Award,
                      value: currentUser.role === "teacher" ? "4.8" : "85.6",
                      label: currentUser.role === "teacher" ? "教学评分" : "平均分",
                      color: "text-cyan-500",
                      delay: "delay-300",
                    },
                    {
                      icon: TrendingUp,
                      value: "+12%",
                      label: "本月提升",
                      color: "text-indigo-500",
                      delay: "delay-400",
                    },
                  ].map((stat, index) => (
                    <Card
                      key={index}
                      className={`card-hover animate-fade-in-up ${stat.delay} bg-white/70 backdrop-blur-sm border-sky-200`}
                    >
                      <CardContent className="p-3 sm:p-6 text-center">
                        <stat.icon
                          className={`w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-2 sm:mb-3 ${stat.color} animate-float`}
                        />
                        <p className="text-xl sm:text-3xl font-bold gradient-text mb-1">{stat.value}</p>
                        <p className="text-xs sm:text-sm text-slate-500">{stat.label}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Quick actions */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 animate-fade-in-up delay-500">
                  {[
                    {
                      title: "快速批改",
                      description: "上传作业，立即获得AI批改结果",
                      icon: Brain,
                      color: "from-sky-400 to-blue-500",
                      action: () => setCurrentPage("grading"),
                    },
                    {
                      title: "班级管理",
                      description: "查看班级动态，管理学生信息",
                      icon: Users,
                      color: "from-blue-400 to-cyan-500",
                      action: () => setCurrentPage("classes"),
                    },
                    {
                      title: "学习分析",
                      description: "深入了解学习数据和趋势",
                      icon: BarChart3,
                      color: "from-cyan-400 to-teal-500",
                      action: () => setCurrentPage("analytics"),
                    },
                  ].map((action, index) => (
                    <Card
                      key={index}
                      className="card-hover cursor-pointer bg-white/70 backdrop-blur-sm border-sky-200"
                      onClick={action.action}
                    >
                      <CardContent className="p-4 sm:p-6">
                        <div
                          className={`w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-r ${action.color} rounded-xl flex items-center justify-center mb-3 sm:mb-4`}
                        >
                          <action.icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                        </div>
                        <h3 className="text-lg sm:text-xl font-semibold text-slate-800 mb-2">{action.title}</h3>
                        <p className="text-sm sm:text-base text-slate-600">{action.description}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )
    }
  }

  return (
    <>
      <HiddenNavigation currentPage={currentPage} onPageChange={setCurrentPage} userRole={currentUser.role} />
      {renderPage()}
    </>
  )
}
