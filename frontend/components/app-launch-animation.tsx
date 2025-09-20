"use client"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Brain, Zap, BookOpen, Users, Target, Award, CheckCircle, Sparkles } from "lucide-react"

interface AppLaunchAnimationProps {
  onComplete: () => void
}

export function AppLaunchAnimation({ onComplete }: AppLaunchAnimationProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [showContent, setShowContent] = useState(false)

  const steps = [
    {
      icon: Brain,
      title: "初始化AI引擎",
      description: "正在启动智能批改系统...",
      color: "text-blue-500",
      bgColor: "bg-blue-100",
      duration: 1000,
    },
    {
      icon: BookOpen,
      title: "加载知识库",
      description: "正在同步最新教学资源...",
      color: "text-green-500",
      bgColor: "bg-green-100",
      duration: 800,
    },
    {
      icon: Users,
      title: "连接班级数据",
      description: "正在获取学生信息...",
      color: "text-purple-500",
      bgColor: "bg-purple-100",
      duration: 600,
    },
    {
      icon: Target,
      title: "优化算法模型",
      description: "正在个性化学习方案...",
      color: "text-orange-500",
      bgColor: "bg-orange-100",
      duration: 700,
    },
    {
      icon: Award,
      title: "系统就绪",
      description: "AI智能批改系统已准备完毕",
      color: "text-yellow-500",
      bgColor: "bg-yellow-100",
      duration: 500,
    },
  ]

  useEffect(() => {
    // Show content after initial delay
    const showTimer = setTimeout(() => {
      setShowContent(true)
    }, 300)

    return () => clearTimeout(showTimer)
  }, [])

  const currentStepData = steps[currentStep]

  useEffect(() => {
    if (!showContent) return

    const stepTimer = setTimeout(() => {
      if (currentStep < steps.length - 1) {
        setCurrentStep(currentStep + 1)
        setProgress(((currentStep + 1) / steps.length) * 100)
      } else {
        // Complete animation
        setTimeout(() => {
          onComplete()
        }, 1000)
      }
    }, currentStepData?.duration || 1000)

    return () => clearTimeout(stepTimer)
  }, [currentStep, showContent, onComplete])

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-primary/5 via-background to-accent/5 flex items-center justify-center z-50">
      {/* Background Animation */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/10 rounded-full animate-pulse" />
        <div className="absolute top-3/4 right-1/4 w-48 h-48 bg-accent/10 rounded-full animate-pulse delay-1000" />
        <div className="absolute bottom-1/4 left-1/3 w-32 h-32 bg-secondary/10 rounded-full animate-pulse delay-500" />
      </div>

      {/* Main Content */}
      <div
        className={`relative z-10 transition-all duration-1000 ${showContent ? "opacity-100 scale-100" : "opacity-0 scale-95"}`}
      >
        <Card className="w-96 bg-background/80 backdrop-blur-sm border-primary/20 shadow-2xl">
          <CardContent className="p-8 text-center">
            {/* Logo Area */}
            <div className="mb-8">
              <div className="w-20 h-20 bg-gradient-to-br from-primary to-accent rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse-glow">
                <Brain className="w-10 h-10 text-primary-foreground" />
              </div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                AI智能批改系统
              </h1>
              <p className="text-sm text-muted-foreground mt-2">让教育更智能，让学习更高效</p>
            </div>

            {/* Current Step */}
            <div className="mb-6">
              <div
                className={`w-16 h-16 ${currentStepData?.bgColor} rounded-full flex items-center justify-center mx-auto mb-4 transition-all duration-500 animate-bounce`}
              >
                {currentStepData && <currentStepData.icon className={`w-8 h-8 ${currentStepData.color}`} />}
              </div>
              <h3 className="text-lg font-semibold mb-2">{currentStepData?.title}</h3>
              <p className="text-sm text-muted-foreground">{currentStepData?.description}</p>
            </div>

            {/* Progress Bar */}
            <div className="mb-6">
              <Progress value={progress} className="h-2 mb-2" />
              <p className="text-xs text-muted-foreground">{Math.round(progress)}% 完成</p>
            </div>

            {/* Step Indicators */}
            <div className="flex justify-center gap-2">
              {steps.map((step, index) => (
                <div
                  key={index}
                  className={`w-2 h-2 rounded-full transition-all duration-300 ${
                    index <= currentStep ? "bg-primary" : "bg-muted"
                  }`}
                />
              ))}
            </div>

            {/* Features Preview */}
            <div className="mt-8 grid grid-cols-2 gap-3 text-xs">
              <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                <Zap className="w-3 h-3 text-yellow-500" />
                <span>智能批改</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                <Target className="w-3 h-3 text-blue-500" />
                <span>个性化分析</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                <Users className="w-3 h-3 text-green-500" />
                <span>班级管理</span>
              </div>
              <div className="flex items-center gap-2 p-2 bg-muted/50 rounded-lg">
                <Sparkles className="w-3 h-3 text-purple-500" />
                <span>数据洞察</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Floating Elements */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-20 left-20 animate-float">
          <CheckCircle className="w-6 h-6 text-green-500 opacity-60" />
        </div>
        <div className="absolute top-32 right-32 animate-float delay-1000">
          <BookOpen className="w-5 h-5 text-blue-500 opacity-60" />
        </div>
        <div className="absolute bottom-32 left-32 animate-float delay-500">
          <Award className="w-6 h-6 text-yellow-500 opacity-60" />
        </div>
        <div className="absolute bottom-20 right-20 animate-float delay-1500">
          <Target className="w-5 h-5 text-purple-500 opacity-60" />
        </div>
      </div>
    </div>
  )
}
