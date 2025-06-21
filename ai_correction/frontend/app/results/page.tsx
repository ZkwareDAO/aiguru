'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  FileText, 
  Clock, 
  Eye, 
  ArrowLeft,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

interface CorrectionRecord {
  timestamp: string
  content: string
  files: any
  settings: any
}

export default function ResultsPage() {
  const router = useRouter()
  const [records, setRecords] = useState<CorrectionRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // 检查认证状态
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

  // 格式化时间
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN')
  }

  // 获取文件数量
  const getFileCount = (files: any) => {
    if (!files || typeof files !== 'object') return 0
    try {
      return Object.keys(files).length
    } catch (error) {
      return 0
    }
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

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto">
        {/* 页面标题 */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push('/')}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回首页
            </Button>
            <h1 className="text-3xl font-bold text-gray-900">批改记录</h1>
          </div>
          <p className="text-gray-600">查看您的所有批改记录，点击题号查看详细结果</p>
        </div>

        {/* 错误提示 */}
        {error && (
          <Alert className="mb-6 border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        )}

        {/* 加载状态 */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-flex items-center gap-2 text-gray-600">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              加载中...
            </div>
          </div>
        ) : records.length === 0 ? (
          // 空状态
          <Card>
            <CardContent className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">暂无批改记录</h3>
              <p className="text-gray-500 mb-6">您还没有进行过任何批改，开始您的第一次批改吧！</p>
              <Button onClick={() => router.push('/grading')}>
                开始批改
              </Button>
            </CardContent>
          </Card>
        ) : (
          // 题目列表
          <div className="space-y-4">
            {records.map((record, index) => {
              const questionNumber = records.length - index // 从最新到最旧，题号递减
              return (
                <Card key={index} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      {/* 左侧信息 */}
                      <div className="flex items-center gap-6">
                        {/* 题号 */}
                        <div className="flex-shrink-0">
                          <div className="w-16 h-16 bg-blue-500 text-white rounded-lg flex items-center justify-center font-bold text-xl">
                            #{questionNumber}
                          </div>
                        </div>
                        
                        {/* 详细信息 */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-4">
                            <h3 className="text-lg font-semibold text-gray-900">
                              第 {questionNumber} 题
                            </h3>
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                              {getCorrectionTypeText(record.settings)}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-6 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <Clock className="h-4 w-4" />
                              {formatTime(record.timestamp)}
                            </div>
                            <div className="flex items-center gap-1">
                              <FileText className="h-4 w-4" />
                              {getFileCount(record.files)} 个文件
                            </div>
                            <div className="flex items-center gap-1">
                              <CheckCircle className="h-4 w-4 text-green-500" />
                              批改完成
                            </div>
                          </div>
                          
                          {/* 设置信息 */}
                          {record.settings && (
                            <div className="flex items-center gap-4 text-xs text-gray-500">
                              <span>严格程度: {record.settings.strictness_level || '中等'}</span>
                              <span>语言: {record.settings.language === 'zh' ? '中文' : 'English'}</span>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* 右侧操作 */}
                      <div className="flex-shrink-0 flex gap-2">
                        <Link href={`/detail/${questionNumber}`}>
                          <Button className="flex items-center gap-2">
                            <Eye className="h-4 w-4" />
                            详情对照
                          </Button>
                        </Link>
                        <Link href={`/results/${questionNumber}`}>
                          <Button variant="outline" size="sm" className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            原始结果
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}

        {/* 底部操作 */}
        {records.length > 0 && (
          <div className="mt-8 flex justify-center gap-4">
            <Button
              variant="outline"
              onClick={() => router.push('/grading')}
            >
              新建批改
            </Button>
            <Button
              variant="outline"
              onClick={() => window.location.reload()}
            >
              刷新记录
            </Button>
          </div>
        )}
      </div>
    </div>
  )
} 