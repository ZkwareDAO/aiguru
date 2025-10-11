"use client"

import { useState } from "react"
import { Menu, X, Home, BookOpen, Users, BarChart3, Settings, Brain } from "lucide-react"
import { Button } from "@/components/ui/button"

interface HiddenNavigationProps {
  currentPage: string
  onPageChange: (page: string) => void
  userRole: "student" | "teacher" | "parent"
}

export function HiddenNavigation({ currentPage, onPageChange, userRole }: HiddenNavigationProps) {
  const [isOpen, setIsOpen] = useState(false)

  const navigationItems = [
    { id: "home", icon: Home, label: "首页", color: "text-sky-600" },
    { id: "assignments", icon: BookOpen, label: "作业系统", color: "text-blue-600" },
    { id: "classes", icon: Users, label: "班级管理", color: "text-cyan-600" },
    { id: "grading", icon: Brain, label: "智能批改", color: "text-indigo-600" },
    { id: "analytics", icon: BarChart3, label: "数据分析", color: "text-purple-600" },
    { id: "settings", icon: Settings, label: "系统设置", color: "text-slate-600" },
  ]

  return (
    <>
      <div className="nav-trigger" onClick={() => setIsOpen(!isOpen)}>
        {isOpen ? <X className="w-6 h-6 text-white" /> : <Menu className="w-6 h-6 text-white" />}
      </div>

      <div
        className={`fixed inset-0 z-50 transition-all duration-300 ${
          isOpen ? "opacity-100 visible" : "opacity-0 invisible"
        }`}
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setIsOpen(false)} />

        {/* Navigation panel */}
        <div
          className={`absolute top-0 right-0 h-full w-80 bg-white/95 backdrop-blur-xl border-l border-sky-200 shadow-2xl transform transition-transform duration-300 ${
            isOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-sky-400 to-cyan-500 rounded-xl flex items-center justify-center">
                  <Brain className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="font-bold text-slate-800">AI智能批改</h2>
                  <p className="text-sm text-slate-500">
                    {userRole === "teacher" ? "教师" : userRole === "student" ? "学生" : "家长"}模式
                  </p>
                </div>
              </div>
            </div>

            {/* Navigation items */}
            <nav className="space-y-2">
              {navigationItems.map((item) => (
                <Button
                  key={item.id}
                  variant={currentPage === item.id ? "default" : "ghost"}
                  className={`w-full justify-start gap-3 h-12 ${
                    currentPage === item.id
                      ? "bg-gradient-to-r from-sky-500 to-cyan-500 text-white shadow-lg"
                      : "hover:bg-sky-50 text-slate-700"
                  }`}
                  onClick={() => {
                    onPageChange(item.id)
                    setIsOpen(false)
                  }}
                >
                  <item.icon className={`w-5 h-5 ${currentPage === item.id ? "text-white" : item.color}`} />
                  {item.label}
                </Button>
              ))}
            </nav>

            {/* Footer */}
            <div className="absolute bottom-6 left-6 right-6">
              <div className="p-4 bg-gradient-to-r from-sky-50 to-cyan-50 rounded-xl border border-sky-200">
                <p className="text-sm text-slate-600 text-center">AI助手随时为您服务</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
