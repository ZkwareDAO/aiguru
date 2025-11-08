"use client"

import type React from "react"

import { useState, useRef, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { Upload, Camera, FileText, Clipboard, X, CheckCircle, Loader2, ImageIcon, File } from "lucide-react"
import { cn } from "@/lib/utils"

interface UploadedFile {
  id: string
  name: string
  type: string
  size: number
  preview?: string
}

export function UploadInterface() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [textContent, setTextContent] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = Array.from(e.dataTransfer.files)
    handleFiles(files)
  }, [])

  const handleFiles = (files: File[]) => {
    files.forEach((file) => {
      const fileId = Math.random().toString(36).substr(2, 9)
      const newFile: UploadedFile = {
        id: fileId,
        name: file.name,
        type: file.type,
        size: file.size,
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
  }

  const removeFile = (fileId: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId))
  }

  const simulateUpload = async () => {
    setIsUploading(true)
    setUploadProgress(0)

    // Simulate upload progress
    for (let i = 0; i <= 100; i += 10) {
      setUploadProgress(i)
      await new Promise((resolve) => setTimeout(resolve, 200))
    }

    setIsUploading(false)
    // Here you would typically navigate to the grading results
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  return (
    <div className="space-y-6">
      {/* Upload Methods */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Camera Upload */}
        <Card className="hover:shadow-lg transition-all duration-300 hover:scale-105 cursor-pointer group">
          <CardContent className="p-6 text-center space-y-4" onClick={() => cameraInputRef.current?.click()}>
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mx-auto group-hover:bg-primary group-hover:text-primary-foreground transition-colors animate-float">
              <Camera className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-semibold">拍照上传</h3>
              <p className="text-sm text-muted-foreground">快速拍摄作业照片</p>
            </div>
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(Array.from(e.target.files))}
            />
          </CardContent>
        </Card>

        {/* File Upload */}
        <Card className="hover:shadow-lg transition-all duration-300 hover:scale-105 cursor-pointer group">
          <CardContent className="p-6 text-center space-y-4" onClick={() => fileInputRef.current?.click()}>
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mx-auto group-hover:bg-primary group-hover:text-primary-foreground transition-colors animate-float">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-semibold">文件上传</h3>
              <p className="text-sm text-muted-foreground">支持PDF、Word、图片等</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf,.doc,.docx,.txt"
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(Array.from(e.target.files))}
            />
          </CardContent>
        </Card>

        {/* Text Input */}
        <Card className="hover:shadow-lg transition-all duration-300 hover:scale-105">
          <CardContent className="p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mx-auto animate-float">
              <Clipboard className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold">文本输入</h3>
              <p className="text-sm text-muted-foreground">直接输入或粘贴内容</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Drag and Drop Area */}
      <Card
        className={cn(
          "border-2 border-dashed transition-all duration-300",
          dragActive ? "border-primary bg-primary/5 scale-105" : "border-muted-foreground/25",
          "hover:border-primary hover:bg-primary/5",
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <CardContent className="p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto animate-pulse-glow">
            <Upload className="w-8 h-8 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold">拖拽文件到此处</h3>
            <p className="text-muted-foreground">或点击上方按钮选择文件</p>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Badge variant="secondary">JPG</Badge>
            <Badge variant="secondary">PNG</Badge>
            <Badge variant="secondary">PDF</Badge>
            <Badge variant="secondary">DOC</Badge>
            <Badge variant="secondary">TXT</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Text Input Area */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clipboard className="w-5 h-5" />
            文本输入
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="在此输入或粘贴作业内容..."
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            className="min-h-32 resize-none"
          />
        </CardContent>
      </Card>

      {/* Uploaded Files */}
      {uploadedFiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              已上传文件 ({uploadedFiles.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {uploadedFiles.map((file) => (
                <div key={file.id} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
                  <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    {file.preview ? (
                      <img
                        src={file.preview || "/placeholder.svg"}
                        alt={file.name}
                        className="w-full h-full object-cover rounded-lg"
                      />
                    ) : file.type.startsWith("image/") ? (
                      <ImageIcon className="w-5 h-5 text-primary" />
                    ) : (
                      <File className="w-5 h-5 text-primary" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{file.name}</p>
                    <p className="text-sm text-muted-foreground">{formatFileSize(file.size)}</p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => removeFile(file.id)} className="flex-shrink-0">
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span className="font-medium">AI正在分析您的作业...</span>
              </div>
              <Progress value={uploadProgress} className="w-full" />
              <p className="text-sm text-muted-foreground text-center">
                {uploadProgress < 30 && "正在上传文件..."}
                {uploadProgress >= 30 && uploadProgress < 60 && "AI正在识别内容..."}
                {uploadProgress >= 60 && uploadProgress < 90 && "智能批改中..."}
                {uploadProgress >= 90 && "生成批改报告..."}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Submit Button */}
      <div className="flex justify-center">
        <Button
          size="lg"
          className="px-8 py-3 text-lg animate-pulse-glow"
          disabled={(uploadedFiles.length === 0 && !textContent.trim()) || isUploading}
          onClick={simulateUpload}
        >
          {isUploading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              AI批改中...
            </>
          ) : (
            <>
              <CheckCircle className="w-5 h-5 mr-2" />
              开始AI批改
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
