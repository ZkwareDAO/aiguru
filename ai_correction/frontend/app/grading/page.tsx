'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  Download,
  Eye
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import { apiService } from '@/lib/api'

interface CorrectionResult {
  success: boolean
  result?: string
  error?: string
  correction_type?: string
  result_type?: string
  files_processed?: number
  strictness_level?: string
  language?: string
  auto_detected_type?: string
  message?: string
}

export default function GradingPage() {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [correctionResult, setCorrectionResult] = useState<CorrectionResult | null>(null)

  // 表单状态
  const [files, setFiles] = useState<FileList | null>(null)
  const [correctionType, setCorrectionType] = useState('auto')
  const [strictnessLevel, setStrictnessLevel] = useState('中等')
  const [language, setLanguage] = useState('zh')
  const [customScheme, setCustomScheme] = useState('')
  
  // 文件预览状态
  const [filePreviewContents, setFilePreviewContents] = useState<{[key: string]: string}>({})
  const [previewError, setPreviewError] = useState('')

  // 检查认证状态
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('auth_token')
      const username = localStorage.getItem('username')
      
      if (token && username) {
        // 确保API服务有token
        apiService.setToken(token)
        
        try {
          // 尝试解析JWT token
          const parts = token.split('.')
          if (parts.length === 3) {
            // 添加padding如果需要
            let payload = parts[1]
            while (payload.length % 4) {
              payload += '='
            }
            
            const decoded = JSON.parse(atob(payload))
            const exp = decoded.exp * 1000
            const now = Date.now()
            
            if (exp > now) {
              setIsAuthenticated(true)
              return
            } else {
              // Token过期
              localStorage.removeItem('auth_token')
              localStorage.removeItem('username')
              apiService.logout()
            }
          } else {
            // 不是标准JWT格式，但如果有username就认为已认证
            setIsAuthenticated(true)
            return
          }
        } catch (error) {
          console.log('Token解析失败，但检查是否有用户名:', error)
          // JWT解析失败，但如果有username就认为已认证
          if (username) {
            setIsAuthenticated(true)
            return
          }
          localStorage.removeItem('auth_token')
          localStorage.removeItem('username')
          apiService.logout()
        }
      }
      
      setIsAuthenticated(false)
    }

    checkAuth()
  }, [])

  // 文件预览处理
  const handleFilePreview = async (files: FileList | null) => {
    if (!files || files.length === 0) {
      setFilePreviewContents({})
      setPreviewError('')
      return
    }

    const previews: {[key: string]: string} = {}
    setPreviewError('')

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const fileKey = `${file.name}_${file.size}_${file.lastModified}`

      try {
        if (file.type.startsWith('text/') || file.name.endsWith('.txt') || file.name.endsWith('.md')) {
          // 文本文件预览
          const text = await file.text()
          previews[fileKey] = text.substring(0, 2000) + (text.length > 2000 ? '\n\n... (文件内容较长，仅显示前2000字符)' : '')
        } else if (file.type.startsWith('image/')) {
          // 图片文件预览
          const imageUrl = URL.createObjectURL(file)
          previews[fileKey] = `[图片文件: ${file.name}]`
        } else if (file.type === 'application/pdf') {
          // PDF文件预览
          previews[fileKey] = `[PDF文件: ${file.name}]\n文件大小: ${(file.size / 1024 / 1024).toFixed(2)} MB\n\n注意：PDF内容将在批改时自动提取和分析。`
        } else {
          // 其他文件类型
          previews[fileKey] = `[${file.type || '未知类型'}文件: ${file.name}]\n文件大小: ${(file.size / 1024 / 1024).toFixed(2)} MB\n\n此文件类型的内容将在批改时自动处理。`
        }
      } catch (error) {
        console.error(`预览文件 ${file.name} 失败:`, error)
        previews[fileKey] = `[预览失败: ${file.name}]\n错误: 无法读取文件内容`
      }
    }

    setFilePreviewContents(previews)
  }

  // 文件验证
  const validateFiles = (files: FileList | null) => {
    if (!files || files.length === 0) {
      throw new Error('请选择至少一个文件')
    }

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      
      // 检查文件大小 (5MB)
      if (file.size > 5 * 1024 * 1024) {
        throw new Error(`文件 "${file.name}" 超过5MB大小限制`)
      }

      // 检查文件类型
      const allowedTypes = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
        'application/pdf',
        'text/plain', 'text/markdown',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ]
      
      const allowedExtensions = ['.txt', '.md', '.doc', '.docx', '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
      const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
      
      if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
        throw new Error(`文件 "${file.name}" 格式不支持。支持的格式：图片(JPG,PNG,GIF等)、PDF、文本文件(TXT,DOC等)`)
      }
    }
  }

  // 处理文件上传和批改
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!isAuthenticated) {
      setError('请先登录账户')
      return
    }

    setIsLoading(true)
    setError('')
    setSuccess('')
    setCorrectionResult(null)
    setUploadProgress(0)

    try {
      // 验证文件
      validateFiles(files)

      setUploadProgress(30)

      // 将FileList转换为File数组
      const fileArray = files ? Array.from(files) : []
      
      // 使用API服务发送请求
      const result = await apiService.enhancedCorrection(
        null, // questionFiles
        fileArray, // studentAnswerFiles
        null, // markingSchemeFiles
        strictnessLevel,
        language,
        correctionType,
        true // generateSummary
      )

      setUploadProgress(100)

      if (result.success && result.data) {
        setCorrectionResult({
          success: true,
          result: result.data.result,
          correction_type: correctionType,
          files_processed: result.data.processing_info?.files_processed || fileArray.length,
          strictness_level: strictnessLevel,
          language: language
        })
        
        setSuccess(`批改完成！处理了 ${result.data.processing_info?.files_processed || fileArray.length} 个文件`)
        
        // 清空表单
        setFiles(null)
        setCustomScheme('')
        setFilePreviewContents({})
        
        // 重置文件输入
        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
        if (fileInput) fileInput.value = ''
        
      } else {
        throw new Error(result.error || '批改失败，请重试')
      }

    } catch (error: any) {
      console.error('批改错误:', error)
      
      if (error.message?.includes('401') || error.message?.includes('认证')) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('username')
        apiService.logout()
        setIsAuthenticated(false)
        setError('认证已过期，请重新登录')
      } else {
        setError(error.message || '批改失败，请重试')
      }
    } finally {
      setIsLoading(false)
      setUploadProgress(0)
    }
  }

  // 重新登录
  const handleReLogin = () => {
    localStorage.removeItem('auth_token')
    router.push('/auth')
  }

  // 如果未认证，显示登录提示
  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="max-w-lg mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-500" />
              需要登录
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-gray-600">请先登录账户才能使用AI批改功能</p>
            <Button onClick={handleReLogin} className="w-full">
              前往登录
              </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI智能批改系统</h1>
          <p className="text-gray-600">基于calling_api.py核心功能的专业批改平台</p>
      </div>

        {/* 错误提示 */}
        {error && (
          <Alert className="mb-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        )}

        {/* 成功提示 */}
        {success && (
          <Alert className="mb-6 border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">{success}</AlertDescription>
          </Alert>
        )}

        {/* 上传进度 */}
        {uploadProgress > 0 && (
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-4 w-4 animate-spin" />
                <div className="flex-1">
                  <div className="flex justify-between text-sm mb-1">
                    <span>处理进度</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} className="h-2" />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 左侧：上传表单 */}
          <Card>
            <CardHeader>
              <CardTitle>文件上传与批改设置</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* 文件上传 */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    选择文件 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    type="file"
                    multiple
                    accept="image/*,.pdf,.txt,.doc,.docx,.md"
                    onChange={(e) => {
                      setFiles(e.target.files)
                      handleFilePreview(e.target.files)
                    }}
                    className="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                  <p className="text-xs text-gray-500">
                    支持：图片、PDF、文本文件 | 最大5MB/文件 | 可选择多个文件
                  </p>
                </div>

                {/* 文件预览区域 */}
                {files && files.length > 0 && (
                  <div className="space-y-3">
                    <Label className="flex items-center gap-2">
                      <Eye className="h-4 w-4" />
                      文件预览 ({files.length} 个文件)
                    </Label>
                    <div className="border rounded-lg p-4 bg-gray-50 max-h-80 overflow-y-auto">
                      {Array.from(files).map((file, index) => {
                        const fileKey = `${file.name}_${file.size}_${file.lastModified}`
                        const previewContent = filePreviewContents[fileKey]
                        
                        return (
                          <div key={fileKey} className="mb-4 last:mb-0">
                            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-200">
                              <FileText className="h-4 w-4 text-blue-600" />
                              <span className="font-medium text-sm text-gray-700">
                                {file.name}
                              </span>
                              <span className="text-xs text-gray-500">
                                ({(file.size / 1024).toFixed(1)} KB)
                              </span>
                            </div>
                            
                            {file.type.startsWith('image/') ? (
                              <div className="space-y-2">
                                <img 
                                  src={URL.createObjectURL(file)} 
                                  alt={file.name}
                                  className="max-w-full max-h-48 object-contain rounded border"
                                  onLoad={(e) => {
                                    // 释放对象URL以节省内存
                                    setTimeout(() => {
                                      URL.revokeObjectURL((e.target as HTMLImageElement).src)
                                    }, 1000)
                                  }}
                                />
                                <p className="text-xs text-gray-600">
                                  图片将被AI分析其中的文字和内容进行批改
                                </p>
                              </div>
                            ) : (
                              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono bg-white p-3 rounded border">
                                {previewContent || '正在加载预览...'}
                              </pre>
                            )}
                          </div>
                        )
                      })}
                    </div>
                    
                    {previewError && (
                      <p className="text-xs text-red-600 flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        {previewError}
                      </p>
                    )}
                  </div>
                )}

                {/* 批改类型 */}
                <div className="space-y-2">
                  <Label>批改类型</Label>
                  <Select value={correctionType} onValueChange={setCorrectionType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">自动批改（推荐）</SelectItem>
                      <SelectItem value="generate_scheme">仅生成评分标准</SelectItem>
                      <SelectItem value="with_scheme">使用自定义评分标准</SelectItem>
                      <SelectItem value="single_group">单题批改</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* 自定义评分标准 */}
                {correctionType === 'with_scheme' && (
                <div className="space-y-2">
                    <Label>自定义评分标准</Label>
                    <Textarea
                      value={customScheme}
                      onChange={(e) => setCustomScheme(e.target.value)}
                      placeholder="请输入详细的评分标准..."
                      rows={4}
                      className="resize-none"
            />
          </div>
                )}

                {/* 批改参数 */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>严格程度</Label>
                    <Select value={strictnessLevel} onValueChange={setStrictnessLevel}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="宽松">宽松</SelectItem>
                        <SelectItem value="中等">中等</SelectItem>
                        <SelectItem value="严格">严格</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>输出语言</Label>
                    <Select value={language} onValueChange={setLanguage}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="zh">中文</SelectItem>
                        <SelectItem value="en">English</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
            </div>

            <Button
              type="submit"
                  disabled={isLoading || !files} 
                  className="w-full"
            >
                  {isLoading ? (
                <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      正在处理...
                </>
              ) : (
                <>
                      <Upload className="mr-2 h-4 w-4" />
                      开始批改
                </>
              )}
            </Button>
        </form>
            </CardContent>
          </Card>

          {/* 右侧：批改结果 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                批改结果
              </CardTitle>
            </CardHeader>
            <CardContent>
              {correctionResult ? (
                <div className="space-y-4">
                  {/* 结果信息 */}
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium">批改类型：</span>
                        <span className="text-gray-600">{correctionResult.result_type || correctionResult.correction_type}</span>
                      </div>
                      <div>
                        <span className="font-medium">处理文件：</span>
                        <span className="text-gray-600">{correctionResult.files_processed} 个</span>
                      </div>
                      <div>
                        <span className="font-medium">严格程度：</span>
                        <span className="text-gray-600">{correctionResult.strictness_level}</span>
                      </div>
                      <div>
                        <span className="font-medium">输出语言：</span>
                        <span className="text-gray-600">{correctionResult.language === 'zh' ? '中文' : 'English'}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* 批改内容 */}
                  <div className="border rounded-lg p-4 bg-white max-h-96 overflow-y-auto">
                    {correctionResult.result ? (
                      <div className="space-y-2">
                        <div className="text-sm text-gray-500 mb-2">批改结果：</div>
                        <div className="prose prose-sm max-w-none">
                          <pre className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800 font-normal">
                            {correctionResult.result}
                          </pre>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>批改结果为空，请检查上传的文件内容</p>
                      </div>
                    )}
                  </div>
                  
                  {/* 操作按钮 */}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      className="flex items-center gap-2"
                      onClick={() => {
                        // 跳转到最新的批改详情页面（第1题，因为记录是按时间倒序排列的）
                        router.push('/detail/1')
                      }}
                    >
                      <Eye className="h-4 w-4" />
                      查看详情对照
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(correctionResult.result || '')
                        setSuccess('结果已复制到剪贴板')
                        setTimeout(() => setSuccess(''), 2000)
                      }}
                    >
                      复制结果
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push('/results')}
                    >
                      <Download className="h-4 w-4 mr-1" />
                      查看历史
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>上传文件并开始批改后，结果将显示在这里</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 功能说明 */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>功能说明</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
              <div className="bg-blue-50 p-3 rounded-lg">
                <h4 className="font-medium text-blue-800 mb-2">自动批改</h4>
                <p className="text-blue-600">自动生成评分标准并进行批改，适合大多数场景</p>
              </div>
              <div className="bg-green-50 p-3 rounded-lg">
                <h4 className="font-medium text-green-800 mb-2">生成评分标准</h4>
                <p className="text-green-600">仅根据题目生成详细的评分标准，不进行批改</p>
              </div>
              <div className="bg-purple-50 p-3 rounded-lg">
                <h4 className="font-medium text-purple-800 mb-2">自定义标准</h4>
                <p className="text-purple-600">使用您提供的评分标准进行精确批改</p>
              </div>
              <div className="bg-orange-50 p-3 rounded-lg">
                <h4 className="font-medium text-orange-800 mb-2">单题批改</h4>
                <p className="text-orange-600">专门针对单道题目进行详细分析和批改</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
