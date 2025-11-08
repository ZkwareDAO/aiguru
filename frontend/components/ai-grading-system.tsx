"use client"

import { useState, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Upload, Camera, FileText, X, CheckCircle, File, Brain, Send } from "lucide-react"
import { cn } from "@/lib/utils"
import { CompletionAnimation, useCompletionAnimation } from "./completion-animations"

interface UploadedFile {
  id: string
  name: string
  type: "question" | "answer" | "standard"
  file: File
  preview?: string
}

interface GradingTask {
  id: string
  status: "pending" | "processing" | "completed" | "error"
  progress: number
  result?: any
  createdAt: Date
}

export function AIGradingSystem() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [gradingTasks, setGradingTasks] = useState<GradingTask[]>([])
  const [selectedClass, setSelectedClass] = useState("")
  const [selectedStudents, setSelectedStudents] = useState<string[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [currentStep, setCurrentStep] = useState<"upload" | "grading" | "results">("upload")

  const { animation, showAnimation, hideAnimation } = useCompletionAnimation()

  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = (files: File[], type: "question" | "answer" | "standard") => {
    files.forEach((file) => {
      const fileId = Math.random().toString(36).substr(2, 9)
      const newFile: UploadedFile = {
        id: fileId,
        name: file.name,
        type,
        file,
      }

      // Create preview for images
      if (file.type.startsWith("image/")) {
        const reader = new FileReader()
        reader.onload = (e) => {
          setUploadedFiles((prev) =>
            prev.map((f) => (f.id === fileId ? { ...f, preview: e.target?.result as string } : f)),
          )
        }
        reader.readAsDataURL(file)
      }

      setUploadedFiles((prev) => [...prev, newFile])
    })

    showAnimation("success", `${getFileTypeLabel(type)}上传成功！`)
  }

  const removeFile = (fileId: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId))
  }

  const startGrading = async () => {
    const questionFiles = uploadedFiles.filter((f) => f.type === "question")
    const answerFiles = uploadedFiles.filter((f) => f.type === "answer")
    const standardFiles = uploadedFiles.filter((f) => f.type === "standard")

    if (questionFiles.length === 0 || answerFiles.length === 0 || standardFiles.length === 0) {
      alert("请上传题目、学生作答和批改标准文件")
      return
    }

    const taskId = Math.random().toString(36).substr(2, 9)
    const newTask: GradingTask = {
      id: taskId,
      status: "processing",
      progress: 0,
      createdAt: new Date(),
    }

    setGradingTasks((prev) => [...prev, newTask])
    setCurrentStep("grading")

    showAnimation("progress", "AI智能批改已启动！")

    // Simulate AI grading process
    for (let i = 0; i <= 100; i += 5) {
      await new Promise((resolve) => setTimeout(resolve, 200))
      setGradingTasks((prev) => prev.map((task) => (task.id === taskId ? { ...task, progress: i } : task)))
    }

    // Complete grading
    setGradingTasks((prev) =>
      prev.map((task) =>
        task.id === taskId
          ? {
              ...task,
              status: "completed",
              result: {
                score: 85,
                feedback: "整体答题思路清晰，但在第3题的计算过程中存在小错误...",
                suggestions: ["加强计算准确性", "注意单位换算", "完善解题步骤"],
              },
            }
          : task,
      ),
    )
    setCurrentStep("results")

    showAnimation("achievement", "AI批改完成！得分85分")
  }

  const sendResults = () => {
    if (!selectedClass || selectedStudents.length === 0) {
      alert("请选择班级和学生")
      return
    }

    showAnimation("celebration", `批改结果已成功发送给${selectedStudents.length}名学生！`)
  }

  const getFileTypeLabel = (type: string) => {
    switch (type) {
      case "question":
        return "题目文件"
      case "answer":
        return "学生作答"
      case "standard":
        return "批改标准"
      default:
        return "未知类型"
    }
  }

  const getFileTypeColor = (type: string) => {
    switch (type) {
      case "question":
        return "bg-blue-100 text-blue-800"
      case "answer":
        return "bg-green-100 text-green-800"
      case "standard":
        return "bg-purple-100 text-purple-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 p-4 sm:p-6">
      {animation && (
        <CompletionAnimation type={animation.type} message={animation.message} onComplete={hideAnimation} />
      )}

      {/* Progress Steps */}
      <div className="flex items-center justify-center space-x-4 mb-8">
        {[
          { step: "upload", label: "文件上传", icon: Upload },
          { step: "grading", label: "AI批改", icon: Brain },
          { step: "results", label: "结果分发", icon: Send },
        ].map(({ step, label, icon: Icon }, index) => (
          <div key={step} className="flex items-center">
            <div
              className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium",
                currentStep === step
                  ? "bg-primary text-primary-foreground animate-pulse-glow"
                  : index < ["upload", "grading", "results"].indexOf(currentStep)
                    ? "bg-green-500 text-white"
                    : "bg-muted text-muted-foreground",
              )}
            >
              <Icon className="w-5 h-5" />
            </div>
            <span className="ml-2 text-sm font-medium hidden sm:block">{label}</span>
            {index < 2 && <div className="w-8 h-0.5 bg-muted mx-2 hidden sm:block" />}
          </div>
        ))}
      </div>

      {currentStep === "upload" && (
        <>
          {/* File Upload Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {[
              {
                type: "question",
                title: "题目文件",
                description: "上传考试题目或作业题目",
                color: "border-blue-200 bg-blue-50",
              },
              {
                type: "answer",
                title: "学生作答",
                description: "上传学生的答题文件",
                color: "border-green-200 bg-green-50",
              },
              {
                type: "standard",
                title: "批改标准",
                description: "上传评分标准或参考答案",
                color: "border-purple-200 bg-purple-50",
              },
            ].map(({ type, title, description, color }) => (
              <Card
                key={type}
                className={cn("cursor-pointer hover:shadow-lg transition-all duration-300 hover:scale-105", color)}
              >
                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-lg">{title}</CardTitle>
                  <p className="text-sm text-muted-foreground">{description}</p>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const input = document.createElement("input")
                        input.type = "file"
                        input.multiple = true
                        input.accept = "image/*,.pdf,.doc,.docx,.txt"
                        input.onchange = (e) => {
                          const files = Array.from((e.target as HTMLInputElement).files || [])
                          handleFileUpload(files, type as any)
                        }
                        input.click()
                      }}
                    >
                      <FileText className="w-4 h-4 mr-2" />
                      选择文件
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const input = document.createElement("input")
                        input.type = "file"
                        input.accept = "image/*"
                        input.capture = "environment"
                        input.onchange = (e) => {
                          const files = Array.from((e.target as HTMLInputElement).files || [])
                          handleFileUpload(files, type as any)
                        }
                        input.click()
                      }}
                    >
                      <Camera className="w-4 h-4 mr-2" />
                      拍照
                    </Button>
                  </div>

                  {/* Show uploaded files for this type */}
                  <div className="space-y-2">
                    {uploadedFiles
                      .filter((f) => f.type === type)
                      .map((file) => (
                        <div
                          key={file.id}
                          className="flex items-center gap-2 p-2 bg-white rounded-lg border animate-fade-in-up"
                        >
                          <div className="w-8 h-8 bg-primary/10 rounded flex items-center justify-center flex-shrink-0">
                            {file.preview ? (
                              <img
                                src={file.preview || "/placeholder.svg"}
                                alt={file.name}
                                className="w-full h-full object-cover rounded"
                              />
                            ) : (
                              <File className="w-4 h-4 text-primary" />
                            )}
                          </div>
                          <span className="text-sm truncate flex-1">{file.name}</span>
                          <Button variant="ghost" size="sm" onClick={() => removeFile(file.id)}>
                            <X className="w-3 h-3" />
                          </Button>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Start Grading Button */}
          <div className="flex justify-center pt-6">
            <Button
              size="lg"
              className="px-8 py-3 text-lg animate-pulse-glow"
              disabled={
                uploadedFiles.filter((f) => f.type === "question").length === 0 ||
                uploadedFiles.filter((f) => f.type === "answer").length === 0 ||
                uploadedFiles.filter((f) => f.type === "standard").length === 0
              }
              onClick={startGrading}
            >
              <Brain className="w-5 h-5 mr-2" />
              开始AI智能批改
            </Button>
          </div>
        </>
      )}

      {currentStep === "grading" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-6 h-6 text-primary animate-pulse" />
              AI正在智能批改中...
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {gradingTasks.map((task) => (
              <div key={task.id} className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">批改任务 #{task.id.slice(-6)}</span>
                  <Badge variant={task.status === "completed" ? "default" : "secondary"}>
                    {task.status === "processing" ? "处理中" : task.status === "completed" ? "已完成" : "等待中"}
                  </Badge>
                </div>
                <Progress value={task.progress} className="w-full" />
                <div className="text-sm text-muted-foreground">
                  {task.progress < 20 && "正在分析题目结构..."}
                  {task.progress >= 20 && task.progress < 40 && "正在识别学生答案..."}
                  {task.progress >= 40 && task.progress < 60 && "正在对比标准答案..."}
                  {task.progress >= 60 && task.progress < 80 && "正在生成评分和反馈..."}
                  {task.progress >= 80 && task.progress < 100 && "正在完善批改报告..."}
                  {task.progress === 100 && "批改完成！"}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {currentStep === "results" && (
        <div className="space-y-6">
          {/* Grading Results */}
          <Card className="animate-fade-in-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="w-6 h-6 text-green-500 animate-bounce" />
                批改结果
              </CardTitle>
            </CardHeader>
            <CardContent>
              {gradingTasks
                .filter((t) => t.status === "completed")
                .map((task) => (
                  <div key={task.id} className="space-y-4 p-4 bg-muted/50 rounded-lg animate-fade-in-up">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">任务 #{task.id.slice(-6)}</span>
                      <div className="text-2xl font-bold text-green-600 animate-pulse-scale">
                        {task.result?.score}分
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium mb-2">批改反馈：</h4>
                      <p className="text-sm text-muted-foreground">{task.result?.feedback}</p>
                    </div>
                    <div>
                      <h4 className="font-medium mb-2">改进建议：</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {task.result?.suggestions?.map((suggestion: string, index: number) => (
                          <li key={index}>• {suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
            </CardContent>
          </Card>

          {/* Result Distribution */}
          <Card className="animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Send className="w-6 h-6 text-primary" />
                结果分发
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="class-select">选择班级</Label>
                  <Select value={selectedClass} onValueChange={setSelectedClass}>
                    <SelectTrigger>
                      <SelectValue placeholder="请选择班级" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="class-1">高三(1)班</SelectItem>
                      <SelectItem value="class-2">高三(2)班</SelectItem>
                      <SelectItem value="class-3">高三(3)班</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="students-select">选择学生</Label>
                  <Select
                    value={selectedStudents.join(",")}
                    onValueChange={(value) => setSelectedStudents(value.split(","))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="请选择学生" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全班学生</SelectItem>
                      <SelectItem value="student-1">张三</SelectItem>
                      <SelectItem value="student-2">李四</SelectItem>
                      <SelectItem value="student-3">王五</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                onClick={sendResults}
                className="w-full hover:scale-105 transition-transform duration-200"
                disabled={!selectedClass || selectedStudents.length === 0}
              >
                <Send className="w-4 h-4 mr-2" />
                发送批改结果
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
