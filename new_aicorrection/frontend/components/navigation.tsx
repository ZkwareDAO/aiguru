"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { BookOpen, Upload, Users, BarChart3, Bot, Bell, User, Menu, X, Brain, Sparkles } from "lucide-react"

interface NavigationProps {
  userRole: "student" | "teacher" | "parent"
  activeTab: string
  onTabChange: (tab: string) => void
}

export function Navigation({ userRole, activeTab, onTabChange }: NavigationProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const navItems = [
    { id: "home", label: "批改入口", icon: Upload },
    { id: "errors", label: "错题本", icon: BookOpen },
    { id: "class", label: "班级系统", icon: Users },
    { id: "reports", label: "学习报告", icon: BarChart3 },
    { id: "assistant", label: "AI助手", icon: Bot },
  ]

  const getRoleTheme = () => {
    switch (userRole) {
      case "student":
        return "student-theme"
      case "teacher":
        return "teacher-theme"
      case "parent":
        return "parent-theme"
      default:
        return "student-theme"
    }
  }

  return (
    <div className={`${getRoleTheme()}`}>
      {/* Mobile Header */}
      <div className="lg:hidden bg-card border-b border-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center animate-pulse-glow">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-lg">AI智能批改</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="w-5 h-5" />
              <Badge className="absolute -top-1 -right-1 w-2 h-2 p-0 bg-destructive" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="lg:hidden bg-card border-b border-border animate-slide-in-right">
          <div className="p-4 space-y-2">
            {navItems.map((item) => (
              <Button
                key={item.id}
                variant={activeTab === item.id ? "default" : "ghost"}
                className="w-full justify-start gap-3"
                onClick={() => {
                  onTabChange(item.id)
                  setIsMobileMenuOpen(false)
                }}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Desktop Header */}
      <div className="hidden lg:flex bg-card border-b border-border p-4">
        <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center animate-pulse-glow">
              <Brain className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="font-bold text-xl">AI智能批改</h1>
              <p className="text-sm text-muted-foreground">让学习更高效</p>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => (
              <Button
                key={item.id}
                variant={activeTab === item.id ? "default" : "ghost"}
                className="gap-2"
                onClick={() => onTabChange(item.id)}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Button>
            ))}
          </div>

          {/* User Actions */}
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="w-5 h-5" />
              <Badge className="absolute -top-1 -right-1 w-2 h-2 p-0 bg-destructive" />
            </Button>
            <Button variant="ghost" size="sm">
              <User className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Role Badge */}
      <div className="bg-muted/50 px-4 py-2 border-b border-border">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent animate-float" />
            <span className="text-sm font-medium">
              {userRole === "student" && "学生模式"}
              {userRole === "teacher" && "教师模式"}
              {userRole === "parent" && "家长模式"}
            </span>
          </div>
          <Badge variant="secondary" className="text-xs">
            {userRole === "student" && "活力学习"}
            {userRole === "teacher" && "专业教学"}
            {userRole === "parent" && "关爱陪伴"}
          </Badge>
        </div>
      </div>
    </div>
  )
}
