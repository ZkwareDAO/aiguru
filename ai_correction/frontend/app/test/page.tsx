'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

export default function TestPage() {
  const [testResults, setTestResults] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const runTests = async () => {
    setIsLoading(true)
    setTestResults([])
    
    const tests = [
      {
        name: '后端健康检查',
        test: async () => {
          const response = await fetch('http://localhost:8000/health')
          if (!response.ok) throw new Error(`HTTP ${response.status}`)
          return await response.json()
        }
      },
      {
        name: '批改服务健康检查',
        test: async () => {
          const response = await fetch('http://localhost:8000/api/correction/health')
          if (!response.ok) throw new Error(`HTTP ${response.status}`)
          return await response.json()
        }
      },
      {
        name: '系统状态检查',
        test: async () => {
          const response = await fetch('http://localhost:8000/api/system/status')
          if (!response.ok) throw new Error(`HTTP ${response.status}`)
          return await response.json()
        }
      }
    ]

    for (const test of tests) {
      try {
        const result = await test.test()
        setTestResults(prev => [...prev, {
          name: test.name,
          status: 'success',
          result: result,
          error: null
        }])
      } catch (error: any) {
        setTestResults(prev => [...prev, {
          name: test.name,
          status: 'error',
          result: null,
          error: error.message
        }])
      }
    }
    
    setIsLoading(false)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">系统测试页面</h1>
          <p className="text-gray-600">检查AI智能批改系统的各项功能是否正常</p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>系统状态检测</CardTitle>
          </CardHeader>
          <CardContent>
            <Button 
              onClick={runTests} 
              disabled={isLoading}
              className="mb-4"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  检测中...
                </>
              ) : (
                '开始检测'
              )}
            </Button>

            <div className="space-y-4">
              {testResults.map((result, index) => (
                <Alert 
                  key={index}
                  className={result.status === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}
                >
                  {result.status === 'success' ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-600" />
                  )}
                  <AlertDescription>
                    <div className="font-medium mb-2">
                      {result.name}: {result.status === 'success' ? '✅ 正常' : '❌ 异常'}
                    </div>
                    {result.status === 'success' && result.result && (
                      <div className="text-sm text-gray-600">
                        <pre className="whitespace-pre-wrap">
                          {JSON.stringify(result.result, null, 2)}
                        </pre>
                      </div>
                    )}
                    {result.status === 'error' && (
                      <div className="text-sm text-red-700">
                        错误: {result.error}
                      </div>
                    )}
                  </AlertDescription>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>快速访问</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Button 
                variant="outline" 
                onClick={() => window.open('http://localhost:8000/health', '_blank')}
              >
                后端健康检查
              </Button>
              <Button 
                variant="outline" 
                onClick={() => window.open('http://localhost:8000/docs', '_blank')}
              >
                API文档
              </Button>
              <Button 
                variant="outline" 
                onClick={() => window.open('/grading', '_self')}
              >
                批改页面
              </Button>
              <Button 
                variant="outline" 
                onClick={() => window.open('/auth', '_self')}
              >
                登录页面
              </Button>
              <Button 
                variant="outline" 
                onClick={() => window.open('/results', '_self')}
              >
                批改记录
              </Button>
              <Button 
                variant="outline" 
                onClick={() => window.open('/', '_self')}
              >
                首页
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-medium text-blue-800 mb-2">💡 使用提示</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• 如果所有检测都显示正常，系统已准备就绪</li>
            <li>• 如果有错误，请检查后端服务是否启动</li>
            <li>• 可以使用 start_unified.bat 启动完整系统</li>
            <li>• 测试账户: test_user_1 / password1</li>
          </ul>
        </div>
      </div>
    </div>
  )
} 