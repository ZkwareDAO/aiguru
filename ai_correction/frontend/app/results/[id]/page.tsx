'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  ArrowLeft, 
  ArrowRight, 
  Home, 
  FileText, 
  Image as ImageIcon, 
  Download, 
  Copy,
  Clock,
  Settings,
  AlertCircle,
  CheckCircle,
  Eye
} from 'lucide-react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'

interface CorrectionRecord {
  timestamp: string
  content: string
  files: any
  settings: any
}

interface FileInfo {
  filename: string
  saved_path?: string
}

export default function ResultDetailPage() {
  const router = useRouter()
  const params = useParams()
  const questionId = params.id as string
  
  const [records, setRecords] = useState<CorrectionRecord[]>([])
  const [currentRecord, setCurrentRecord] = useState<CorrectionRecord | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)

  // 检查认证状态并获取记录
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setIsAuthenticated(false)
      setIsLoading(false)
      return
    }
    setIsAuthenticated(true)
    fetchRecords()
  }, [])

  // 当记录加载完成后，设置当前记录
  useEffect(() => {
    if (records.length > 0 && questionId) {
      const questionIndex = parseInt(questionId) - 1
      const recordIndex = records.length - 1 - questionIndex // 从最新到最旧的索引转换
      if (recordIndex >= 0 && recordIndex < records.length) {
        setCurrentRecord(records[recordIndex])
      }
    }
  }, [records, questionId])

  // 获取批改记录
  const fetchRecords = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch('http://localhost:8000/api/user/records', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('auth_token')
          setIsAuthenticated(false)
          throw new Error('认证已过期，请重新登录')
        }
        throw new Error('获取记录失败')
      }

      const data = await response.json()
      setRecords(data.records || [])
    } catch (error: any) {
      setError(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  // 复制批改结果
  const handleCopyResult = async () => {
    if (currentRecord?.content) {
      try {
        await navigator.clipboard.writeText(currentRecord.content)
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
      } catch (error) {
        console.error('复制失败:', error)
      }
    }
  }

  // 下载批改结果
  const handleDownloadResult = () => {
    if (currentRecord?.content) {
      const blob = new Blob([currentRecord.content], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `批改结果_第${questionId}题_${new Date().toLocaleDateString()}.txt`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  // 导航到其他题目
  const navigateToQuestion = (direction: 'prev' | 'next') => {
    const currentId = parseInt(questionId)
    const newId = direction === 'prev' ? currentId - 1 : currentId + 1
    const maxId = records.length
    
    if (newId >= 1 && newId <= maxId) {
      router.push(`/results/${newId}`)
    }
  }

  // 获取文件扩展名
  const getFileExtension = (filename: string) => {
    if (!filename || typeof filename !== 'string') return ''
    return filename.split('.').pop()?.toLowerCase() || ''
  }

  // 判断是否为图片文件
  const isImageFile = (filename: string) => {
    if (!filename || typeof filename !== 'string') return false
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    return imageExtensions.includes(getFileExtension(filename))
  }

  // 渲染文件预览
  const renderFilePreview = (fileKey: string, fileInfo: FileInfo) => {
    // 安全地获取文件名
    const filename = fileInfo?.filename || fileKey || '未知文件'
    const isImage = isImageFile(filename)
    
    return (
      <Card key={fileKey} className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            {isImage ? <ImageIcon className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
            {filename}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isImage ? (
            <div className="border rounded-lg overflow-hidden bg-gray-50">
              <img
                src={`data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==`}
                alt={filename}
                className="max-w-full h-auto max-h-96 object-contain mx-auto"
                onError={(e) => {
                  const target = e.target as HTMLImageElement
                  target.style.display = 'none'
                  const errorDiv = target.nextElementSibling as HTMLElement
                  if (errorDiv) errorDiv.classList.remove('hidden')
                }}
              />
              <div className="hidden p-8 text-center text-gray-500">
                <ImageIcon className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>图片预览暂不可用</p>
                <p className="text-sm">文件名: {filename}</p>
              </div>
            </div>
          ) : (
            <div className="border rounded-lg p-6 bg-gray-50 text-center">
              <FileText className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p className="font-medium text-gray-700">{filename}</p>
              <p className="text-sm text-gray-500">
                {getFileExtension(filename).toUpperCase()} 文件
              </p>
              <p className="text-xs text-gray-400 mt-2">
                暂不支持此文件类型的预览
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  // 格式化时间
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN')
  }

  // 获取批改类型显示文本
  const getCorrectionTypeText = (settings: any) => {
    if (!settings) return '未知类型'
    
    const typeMap: { [key: string]: string } = {
      'auto': '自动批改',
      'generate_scheme': '评分标准生成',
      'with_scheme': '自定义标准批改',
      'single_group': '单题批改',
      'enhanced_api': '增强批改',
      'intelligent_api': '智能批改'
    }
    
    return typeMap[settings.correction_type] || typeMap[settings.processing_method] || '自动批改'
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
            <p className="text-gray-600">请先登录账户才能查看批改记录</p>
            <Button onClick={() => router.push('/auth')} className="w-full">
              前往登录
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <div className="inline-flex items-center gap-2 text-gray-600">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            加载中...
          </div>
        </div>
      </div>
    )
  }

  if (error || !currentRecord) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert className="max-w-lg mx-auto border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            {error || '找不到指定的批改记录'}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const currentQuestionNumber = parseInt(questionId)
  const totalQuestions = records.length

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* 顶部导航 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/results')}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                返回列表
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/')}
              >
                <Home className="h-4 w-4 mr-2" />
                首页
              </Button>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigateToQuestion('prev')}
                disabled={currentQuestionNumber <= 1}
              >
                <ArrowLeft className="h-4 w-4" />
                上一题
              </Button>
              <span className="px-3 py-1 bg-gray-100 rounded text-sm font-medium">
                {currentQuestionNumber} / {totalQuestions}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigateToQuestion('next')}
                disabled={currentQuestionNumber >= totalQuestions}
              >
                下一题
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          {/* 题目标题 */}
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-500 text-white rounded-lg flex items-center justify-center font-bold text-lg">
              #{currentQuestionNumber}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">第 {currentQuestionNumber} 题批改结果</h1>
              <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {formatTime(currentRecord.timestamp)}
                </div>
                <div className="flex items-center gap-1">
                  <Settings className="h-4 w-4" />
                  {getCorrectionTypeText(currentRecord.settings)}
                </div>
                <div className="flex items-center gap-1">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  批改完成
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 主要内容 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左侧：文件预览 */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="h-5 w-5" />
                  上传文件预览
                </CardTitle>
              </CardHeader>
              <CardContent>
                {currentRecord.files && Object.keys(currentRecord.files).length > 0 ? (
                  <div className="space-y-4">
                    {Object.entries(currentRecord.files).map(([key, fileInfo]: [string, any]) => {
                      // 确保fileInfo是一个对象
                      const safeFileInfo = typeof fileInfo === 'object' && fileInfo !== null 
                        ? fileInfo 
                        : { filename: key, saved_path: '' }
                      return renderFilePreview(key, safeFileInfo)
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>没有找到上传的文件</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* 右侧：批改结果 */}
          <div>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    批改结果
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCopyResult}
                    >
                      <Copy className="h-4 w-4 mr-1" />
                      {copySuccess ? '已复制' : '复制'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownloadResult}
                    >
                      <Download className="h-4 w-4 mr-1" />
                      下载
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="result" className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="result">批改内容</TabsTrigger>
                    <TabsTrigger value="settings">批改设置</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="result" className="mt-4">
                    <div className="border rounded-lg p-4 bg-gray-50 max-h-96 overflow-y-auto">
                      <pre className="whitespace-pre-wrap text-sm font-mono text-gray-800">
                        {currentRecord.content || '暂无批改内容'}
                      </pre>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="settings" className="mt-4">
                    <div className="space-y-3">
                      {currentRecord.settings ? (
                        <>
                          <div className="flex justify-between py-2 border-b">
                            <span className="font-medium">批改类型:</span>
                            <span className="text-gray-600">{getCorrectionTypeText(currentRecord.settings)}</span>
                          </div>
                          <div className="flex justify-between py-2 border-b">
                            <span className="font-medium">严格程度:</span>
                            <span className="text-gray-600">{currentRecord.settings.strictness_level || '中等'}</span>
                          </div>
                          <div className="flex justify-between py-2 border-b">
                            <span className="font-medium">输出语言:</span>
                            <span className="text-gray-600">
                              {currentRecord.settings.language === 'zh' ? '中文' : 'English'}
                            </span>
                          </div>
                          <div className="flex justify-between py-2 border-b">
                            <span className="font-medium">处理方法:</span>
                            <span className="text-gray-600">{currentRecord.settings.processing_method || '标准处理'}</span>
                          </div>
                          {currentRecord.settings.custom_scheme && (
                            <div className="py-2">
                              <span className="font-medium block mb-2">自定义评分标准:</span>
                              <div className="bg-gray-100 p-3 rounded text-sm">
                                {currentRecord.settings.custom_scheme}
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        <p className="text-gray-500">暂无设置信息</p>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* 底部操作 */}
        <div className="mt-8 flex justify-center gap-4">
          <Button
            variant="outline"
            onClick={() => router.push('/grading')}
          >
            新建批改
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push('/results')}
          >
            查看所有记录
          </Button>
        </div>

        {/* 成功提示 */}
        {copySuccess && (
          <div className="fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg">
            结果已复制到剪贴板
          </div>
        )}
      </div>
    </div>
  )
} 