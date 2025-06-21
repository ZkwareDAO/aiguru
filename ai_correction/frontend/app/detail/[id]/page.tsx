'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
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
  Eye,
  Maximize2,
  Minimize2,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Monitor,
  FileImage,
  FileCode,
  File,
  ChevronLeft,
  ChevronRight
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
  filename?: string
  saved_path?: string
  original_name?: string
  size?: number
}

export default function DetailPage() {
  const router = useRouter()
  const params = useParams()
  const questionId = params.id as string
  
  const [records, setRecords] = useState<CorrectionRecord[]>([])
  const [currentRecord, setCurrentRecord] = useState<CorrectionRecord | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [filePreviewData, setFilePreviewData] = useState<{[key: string]: string}>({})

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
      const recordIndex = records.length - 1 - questionIndex
      if (recordIndex >= 0 && recordIndex < records.length) {
        setCurrentRecord(records[recordIndex])
        // 自动选择第一个文件
        const files = records[recordIndex].files
        if (files && typeof files === 'object') {
          const fileKeys = Object.keys(files)
          if (fileKeys.length > 0) {
            setSelectedFile(fileKeys[0])
          }
        } else if (Array.isArray(files) && files.length > 0) {
          setSelectedFile('0')
        }
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

  // 获取文件预览数据
  const loadFilePreview = async (filePath: string) => {
    if (filePreviewData[filePath]) return filePreviewData[filePath]
    
    console.log('加载文件预览:', filePath) // 调试信息
    
    try {
      const token = localStorage.getItem('auth_token')
      const url = `http://localhost:8000/api/file/preview?path=${encodeURIComponent(filePath)}`
      console.log('请求URL:', url) // 调试信息
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('API响应数据:', data) // 调试信息
        let content = ''
        
        if (data.type === 'text') {
          content = data.content
        } else if (data.type === 'image') {
          content = data.base64
        } else if (data.type === 'pdf') {
          content = data.message || `PDF文件 (${(data.size / 1024).toFixed(1)} KB) - 点击下载查看`
        } else if (data.type === 'binary') {
          content = data.message || `文件 (${(data.size / 1024).toFixed(1)} KB)`
        } else if (data.type === 'error') {
          content = data.message || '文件处理出错'
        }
        
        console.log('处理后的内容:', content) // 调试信息
        
        setFilePreviewData(prev => ({
          ...prev,
          [filePath]: content
        }))
        return content
      } else {
        console.error('文件预览请求失败:', response.status, response.statusText)
        const errorContent = `文件预览失败 (${response.status}): ${response.statusText}`
        setFilePreviewData(prev => ({
          ...prev,
          [filePath]: errorContent
        }))
        return errorContent
      }
    } catch (error) {
      console.error('加载文件预览失败:', error)
      const errorContent = `文件预览加载失败: ${error instanceof Error ? error.message : '未知错误'}`
      setFilePreviewData(prev => ({
        ...prev,
        [filePath]: errorContent
      }))
      return errorContent
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
      router.push(`/detail/${newId}`)
    }
  }

  // 获取文件类型图标
  const getFileIcon = (filename: string) => {
    if (!filename) return File
    const ext = filename.split('.').pop()?.toLowerCase()
    
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext || '')) {
      return FileImage
    }
    if (['txt', 'md', 'doc', 'docx'].includes(ext || '')) {
      return FileText
    }
    if (['pdf'].includes(ext || '')) {
      return FileCode
    }
    return File
  }

  // 判断是否为图片文件
  const isImageFile = (filename: string) => {
    if (!filename) return false
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
    return imageExtensions.includes(filename.split('.').pop()?.toLowerCase() || '')
  }

  // 判断是否为PDF文件
  const isPdfFile = (filename: string) => {
    if (!filename) return false
    return filename.split('.').pop()?.toLowerCase() === 'pdf'
  }

  // 获取文件信息
  const getFileInfo = (fileKey: string): FileInfo => {
    if (!currentRecord?.files) return {}
    
    const files = currentRecord.files
    if (Array.isArray(files)) {
      const index = parseInt(fileKey)
      return files[index] || {}
    } else if (typeof files === 'object') {
      return files[fileKey] || {}
    }
    return {}
  }

  // 渲染文件预览
  const renderFilePreview = (fileKey: string, fileInfo: FileInfo) => {
    const filename = fileInfo?.filename || fileInfo?.original_name || '未知文件'
    const isImage = isImageFile(filename)
    const isPdf = isPdfFile(filename)
    const FileIcon = getFileIcon(filename)
    
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b bg-slate-50/50">
          <div className="flex items-center gap-2">
            <FileIcon className="h-4 w-4 text-blue-600" />
            <span className="font-medium text-sm">{filename}</span>
          </div>
          <div className="flex items-center gap-2">
            {fileInfo?.size && (
              <Badge variant="secondary" className="text-xs">
                {(fileInfo.size / 1024).toFixed(1)} KB
              </Badge>
            )}
            <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
              <Maximize2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
        
                 <div className="flex-1 p-4 overflow-auto">
           {isImage || isPdf ? (
             <div className="flex items-center justify-center h-full min-h-[400px] bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg border-2 border-dashed border-slate-200">
               {filePreviewData[fileInfo?.saved_path || ''] && (filePreviewData[fileInfo?.saved_path || ''].startsWith('data:image') || filePreviewData[fileInfo?.saved_path || ''].startsWith('data:application/pdf')) ? (
                 isPdf ? (
                   <embed
                     src={filePreviewData[fileInfo?.saved_path || '']}
                     type="application/pdf"
                     className="w-full h-full min-h-[400px] rounded-lg shadow-lg"
                   />
                 ) : (
                   <img
                     src={filePreviewData[fileInfo?.saved_path || '']}
                     alt={filename}
                     className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                   />
                 )
               ) : (
                 <div className="text-center">
                   {isPdf ? (
                     <FileCode className="h-16 w-16 mx-auto mb-4 text-slate-400" />
                   ) : (
                     <ImageIcon className="h-16 w-16 mx-auto mb-4 text-slate-400" />
                   )}
                   <p className="text-slate-600 font-medium">{isPdf ? 'PDF预览' : '图片预览'}</p>
                   <p className="text-sm text-slate-500 mt-1">{filename}</p>
                   <Button 
                     variant="outline" 
                     size="sm" 
                     className="mt-3"
                     onClick={() => loadFilePreview(fileInfo?.saved_path || '')}
                   >
                     <Eye className="h-4 w-4 mr-2" />
                     加载预览
                   </Button>
                 </div>
               )}
             </div>
           ) : (
            <div className="h-full min-h-[400px] bg-slate-900 rounded-lg p-4 font-mono text-sm text-green-400 overflow-auto">
              <div className="flex items-center gap-2 mb-4 text-slate-400">
                <div className="flex gap-1">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                </div>
                <span className="text-xs">{filename}</span>
              </div>
              <div className="whitespace-pre-wrap">
                {filePreviewData[fileInfo?.saved_path || ''] || '点击加载文件内容...'}
              </div>
              {!filePreviewData[fileInfo?.saved_path || ''] && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="mt-4 text-green-400 hover:text-green-300"
                  onClick={() => loadFilePreview(fileInfo?.saved_path || '')}
                >
                  <Eye className="h-4 w-4 mr-2" />
                  加载内容
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  // 解析批改结果为结构化数据
  const parseCorrectionResult = (content: string) => {
    const sections = content.split(/(?=##?\s)/g).filter(section => section.trim())
    const steps: any[] = []
    let summary = ''
    let totalScore = ''
    
    sections.forEach(section => {
      if (section.includes('步骤') || (section.includes('第') && section.includes('分析'))) {
        const stepMatch = section.match(/第?(\d+)步?[：:](.+?)(?=\n|$)/)
        if (stepMatch) {
          const scoreMatch = section.match(/(\d+)\/(\d+)\s*分/)
          steps.push({
            step: stepMatch[1],
            title: stepMatch[2]?.trim(),
            content: section,
            score: scoreMatch ? `${scoreMatch[1]}/${scoreMatch[2]}` : null
          })
        }
      } else if (section.includes('总分') || section.includes('总结')) {
        const scoreMatch = section.match(/总分[：:]?\s*(\d+\/\d+)/)
        if (scoreMatch) {
          totalScore = scoreMatch[1]
        }
        summary = section
      }
    })
    
    return { steps, summary, totalScore }
  }

  // 渲染批改结果
  const renderCorrectionResult = () => {
    if (!currentRecord?.content) return null
    
    const { steps, summary, totalScore } = parseCorrectionResult(currentRecord.content)
    
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-blue-600" />
            <span className="font-medium text-sm">批改结果</span>
          </div>
          <div className="flex items-center gap-2">
            {totalScore && (
              <Badge variant="default" className="bg-blue-600">
                总分: {totalScore}
              </Badge>
            )}
            {copySuccess && (
              <Badge variant="outline" className="text-green-600 border-green-600">
                已复制
              </Badge>
            )}
            <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={handleCopyResult}>
              <Copy className="h-3 w-3" />
            </Button>
            <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={handleDownloadResult}>
              <Download className="h-3 w-3" />
            </Button>
          </div>
        </div>
        
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {steps.map((step, index) => (
              <Card key={index} className="border-l-4 border-l-blue-500">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">
                        {step.step}
                      </div>
                      步骤 {step.step}
                    </CardTitle>
                    {step.score && (
                      <Badge variant="outline" className="text-xs">
                        {step.score} 分
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-0 bg-slate-50/50">
                  <div className="text-sm text-slate-800 whitespace-pre-wrap">
                    {step.content.replace(/^##?\s*第?\d+步?[：:].+?\n/, '')}
                  </div>
                </CardContent>
              </Card>
            ))}
            
            {summary && (
              <Card className="border-l-4 border-l-green-500">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    总结
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 bg-slate-50/50">
                  <div className="text-sm text-slate-800 whitespace-pre-wrap">
                    {summary}
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* 如果没有结构化步骤，显示原始内容 */}
            {steps.length === 0 && (
              <Card>
                <CardContent className="p-4 bg-slate-50/50">
                  <div className="text-sm text-slate-800 whitespace-pre-wrap">
                    {currentRecord.content}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </ScrollArea>
      </div>
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
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-lg mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-500" />
              需要登录
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-gray-600">请先登录账户才能查看批改详情</p>
            <div className="flex gap-2">
              <Button onClick={() => router.push('/auth')} className="flex-1">
                前往登录
              </Button>
              <Button variant="outline" onClick={() => router.push('/')} className="flex-1">
                返回首页
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // 加载状态
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 text-gray-600">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="text-lg">加载中...</span>
          </div>
        </div>
      </div>
    )
  }

  // 错误状态
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-lg mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-5 w-5" />
              加载失败
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="border-red-200 bg-red-50">
              <AlertDescription className="text-red-800">{error}</AlertDescription>
            </Alert>
            <div className="flex gap-2">
              <Button onClick={fetchRecords} className="flex-1">
                重试
              </Button>
              <Button variant="outline" onClick={() => router.push('/')} className="flex-1">
                返回首页
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // 没有记录
  if (!currentRecord) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-lg mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-gray-500" />
              未找到记录
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-gray-600">第 {questionId} 题的批改记录不存在</p>
            <div className="flex gap-2">
              <Button onClick={() => router.push('/results')} className="flex-1">
                查看所有记录
              </Button>
              <Button variant="outline" onClick={() => router.push('/')} className="flex-1">
                返回首页
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const files = currentRecord.files
  const fileKeys = files ? (Array.isArray(files) ? files.map((_, i) => i.toString()) : Object.keys(files)) : []

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* 顶部导航栏 */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-slate-200 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/results')}
                className="flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                返回列表
              </Button>
              <Separator orientation="vertical" className="h-6" />
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-500 text-white flex items-center justify-center font-bold text-sm">
                  #{questionId}
                </div>
                <div>
                  <h1 className="font-semibold text-lg">第 {questionId} 题详情</h1>
                  <p className="text-sm text-slate-500">
                    {formatTime(currentRecord.timestamp)} · {getCorrectionTypeText(currentRecord.settings)}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigateToQuestion('prev')}
                disabled={parseInt(questionId) <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
                上一题
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigateToQuestion('next')}
                disabled={parseInt(questionId) >= records.length}
              >
                下一题
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-200px)]">
          {/* 左侧：文件预览 */}
          <Card className="flex flex-col overflow-hidden shadow-lg border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader className="pb-0">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Monitor className="h-5 w-5 text-blue-600" />
                  文件预览
                </CardTitle>
                {fileKeys.length > 1 && (
                  <Badge variant="secondary">
                    {fileKeys.length} 个文件
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
              {fileKeys.length > 0 ? (
                <div className="h-full flex flex-col">
                  {/* 文件选择标签 */}
                  {fileKeys.length > 1 && (
                    <Tabs value={selectedFile || fileKeys[0]} onValueChange={setSelectedFile} className="flex-shrink-0">
                      <TabsList className="w-full justify-start p-1 bg-slate-100/50">
                        {fileKeys.map((fileKey) => {
                          const fileInfo = getFileInfo(fileKey)
                          const filename = fileInfo?.filename || fileInfo?.original_name || `文件 ${parseInt(fileKey) + 1}`
                          return (
                            <TabsTrigger key={fileKey} value={fileKey} className="text-xs">
                              {filename.length > 15 ? filename.substring(0, 15) + '...' : filename}
                            </TabsTrigger>
                          )
                        })}
                      </TabsList>
                    </Tabs>
                  )}
                  
                  {/* 文件内容 */}
                  <div className="flex-1 overflow-hidden">
                    {selectedFile ? renderFilePreview(selectedFile, getFileInfo(selectedFile)) : (
                      <div className="h-full flex items-center justify-center text-slate-500">
                        <div className="text-center">
                          <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                          <p>请选择要预览的文件</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500">
                  <div className="text-center">
                    <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>暂无文件可预览</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 右侧：批改结果 */}
          <Card className="flex flex-col overflow-hidden shadow-lg border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader className="pb-0">
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                批改结果
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
              {renderCorrectionResult()}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}