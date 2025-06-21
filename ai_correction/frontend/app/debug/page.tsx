'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function DebugPage() {
  const [testData, setTestData] = useState<any>(null)
  const [error, setError] = useState('')

  // 测试数据处理函数
  const testFileExtension = () => {
    const getFileExtension = (filename: string) => {
      if (!filename || typeof filename !== 'string') return ''
      return filename.split('.').pop()?.toLowerCase() || ''
    }

    const testCases = [
      'test.jpg',
      'document.pdf',
      '',
      null,
      undefined,
      123,
      'file.with.multiple.dots.png'
    ]

    const results = testCases.map(testCase => ({
      input: testCase,
      output: getFileExtension(testCase as any),
      type: typeof testCase
    }))

    setTestData(results)
  }

  // 测试文件处理
  const testFileHandling = () => {
    const mockFiles = {
      'file1': { filename: 'test.jpg', saved_path: '/path/to/file1' },
      'file2': { filename: 'document.pdf', saved_path: '/path/to/file2' },
      'file3': null,
      'file4': undefined,
      'file5': { saved_path: '/path/to/file5' }, // 缺少filename
      'file6': 'invalid_data'
    }

    const processedFiles = Object.entries(mockFiles).map(([key, fileInfo]) => {
      const safeFileInfo = typeof fileInfo === 'object' && fileInfo !== null 
        ? fileInfo 
        : { filename: key, saved_path: '' }
      
      const filename = (safeFileInfo as any)?.filename || key || '未知文件'
      
      return {
        key,
        originalData: fileInfo,
        processedData: safeFileInfo,
        finalFilename: filename
      }
    })

    setTestData(processedFiles)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">调试页面 - 历史记录错误修复测试</h1>
        
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>测试控制</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <Button onClick={testFileExtension}>
                  测试文件扩展名处理
                </Button>
                <Button onClick={testFileHandling}>
                  测试文件数据处理
                </Button>
                <Button onClick={() => setTestData(null)}>
                  清除结果
                </Button>
              </div>
            </CardContent>
          </Card>

          {error && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <p className="text-red-800">错误: {error}</p>
              </CardContent>
            </Card>
          )}

          {testData && (
            <Card>
              <CardHeader>
                <CardTitle>测试结果</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-gray-100 p-4 rounded-lg overflow-auto text-sm">
                  {JSON.stringify(testData, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>快速链接</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex gap-4">
                <Button variant="outline" onClick={() => window.open('/results', '_blank')}>
                  打开历史记录页面
                </Button>
                <Button variant="outline" onClick={() => window.open('/grading', '_blank')}>
                  打开批改页面
                </Button>
                <Button variant="outline" onClick={() => window.open('/', '_blank')}>
                  打开首页
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
} 