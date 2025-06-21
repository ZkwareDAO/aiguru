"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AlertCircle, CheckCircle, Loader2, User, Lock, Mail } from 'lucide-react'
import { apiService } from '@/lib/api'

export default function AuthPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // 登录表单状态
  const [loginData, setLoginData] = useState({
    username: '',
    password: ''
  })

  // 注册表单状态
  const [registerData, setRegisterData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  })

  // 处理登录
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    setSuccess('')

    try {
      // 先检查后端连接
      const healthCheck = await apiService.healthCheck()
      if (!healthCheck.success) {
        throw new Error('无法连接到服务器，请确保后端服务正在运行')
      }

      const result = await apiService.login(loginData)
      
      if (result.success) {
        setSuccess('登录成功！正在跳转...')
        
        // 跳转到批改页面
        setTimeout(() => {
          router.push('/grading')
        }, 1000)
      } else {
        throw new Error(result.error || '登录失败')
      }

    } catch (error: any) {
      console.error('登录错误:', error)
      setError(error.message || '登录失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  // 处理注册
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    setSuccess('')

    try {
      // 验证密码确认
      if (registerData.password !== registerData.confirmPassword) {
        throw new Error('两次输入的密码不一致')
      }

      if (registerData.password.length < 6) {
        throw new Error('密码长度至少6位')
      }

      // 先检查后端连接
      const healthCheck = await apiService.healthCheck()
      if (!healthCheck.success) {
        throw new Error('无法连接到服务器，请确保后端服务正在运行')
      }

      const result = await apiService.register({
        username: registerData.username,
        email: registerData.email,
        password: registerData.password,
        confirm_password: registerData.confirmPassword
      })

      if (result.success) {
        setSuccess('注册成功！请切换到登录标签页登录')
        
        // 清空注册表单
        setRegisterData({
          username: '',
          email: '',
          password: '',
          confirmPassword: ''
        })
      } else {
        throw new Error(result.error || '注册失败')
      }

    } catch (error: any) {
      console.error('注册错误:', error)
      setError(error.message || '注册失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  // 快速登录测试账户
  const handleQuickLogin = async () => {
    setLoginData({
      username: 'testuser',
      password: '123456'
    })
    
    setIsLoading(true)
    setError('')
    setSuccess('')

    try {
      // 先检查后端连接
      const healthCheck = await apiService.healthCheck()
      if (!healthCheck.success) {
        throw new Error('无法连接到服务器，请确保后端服务正在运行')
      }

      const result = await apiService.login({
        username: 'testuser',
        password: '123456'
      })

      if (result.success) {
        setSuccess('登录成功！正在跳转...')
        
        // 跳转到批改页面
        setTimeout(() => {
          router.push('/grading')
        }, 1000)
      } else {
        throw new Error(result.error || '快速登录失败')
      }

    } catch (error: any) {
      console.error('快速登录错误:', error)
      setError(error.message || '快速登录失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI智能批改系统</h1>
          <p className="text-gray-600">登录或注册账户开始使用</p>
        </div>

        {/* 错误提示 */}
        {error && (
          <Alert className="border-red-200 bg-red-50">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        )}

        {/* 成功提示 */}
        {success && (
          <Alert className="border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">{success}</AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle>账户认证</CardTitle>
            <CardDescription>登录或注册账户以使用AI批改功能</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login">登录</TabsTrigger>
                <TabsTrigger value="register">注册</TabsTrigger>
              </TabsList>

              {/* 登录标签页 */}
              <TabsContent value="login" className="space-y-4">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-username">用户名</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        id="login-username"
                        type="text"
                        placeholder="请输入用户名"
                        value={loginData.username}
                        onChange={(e) => setLoginData({...loginData, username: e.target.value})}
                        className="pl-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="login-password">密码</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        id="login-password"
                        type="password"
                        placeholder="请输入密码"
                        value={loginData.password}
                        onChange={(e) => setLoginData({...loginData, password: e.target.value})}
                        className="pl-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <Button 
                    type="submit" 
                    disabled={isLoading} 
                    className="w-full bg-blue-600 hover:bg-blue-700 focus:ring-2 focus:ring-blue-500"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        登录中...
                      </>
                    ) : (
                      '登录'
                    )}
                  </Button>
                </form>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-gray-300" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-gray-50 px-2 text-gray-500">或</span>
                  </div>
                </div>

                <Button 
                  onClick={handleQuickLogin}
                  disabled={isLoading}
                  variant="outline"
                  className="w-full border-blue-300 text-blue-600 hover:bg-blue-50 focus:ring-2 focus:ring-blue-500"
                >
                  使用测试账户快速登录
                </Button>
              </TabsContent>

              {/* 注册标签页 */}
              <TabsContent value="register" className="space-y-4">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="register-username">用户名</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        id="register-username"
                        type="text"
                        placeholder="请输入用户名"
                        value={registerData.username}
                        onChange={(e) => setRegisterData({...registerData, username: e.target.value})}
                        className="pl-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-email">邮箱</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        id="register-email"
                        type="email"
                        placeholder="请输入邮箱地址"
                        value={registerData.email}
                        onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                        className="pl-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-password">密码</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        id="register-password"
                        type="password"
                        placeholder="请输入密码（至少6位）"
                        value={registerData.password}
                        onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                        className="pl-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="register-confirm-password">确认密码</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        id="register-confirm-password"
                        type="password"
                        placeholder="请再次输入密码"
                        value={registerData.confirmPassword}
                        onChange={(e) => setRegisterData({...registerData, confirmPassword: e.target.value})}
                        className="pl-10 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                      />
                    </div>
                  </div>

                  <Button 
                    type="submit" 
                    disabled={isLoading} 
                    className="w-full bg-blue-600 hover:bg-blue-700 focus:ring-2 focus:ring-blue-500"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        注册中...
                      </>
                    ) : (
                      '注册'
                    )}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <div className="text-center text-sm text-gray-500 space-y-1">
          <p className="font-medium">测试账户信息：</p>
          <div className="bg-gray-100 rounded-md p-3 space-y-1">
                            <p className="font-mono">用户名: testuser | 密码: 123456</p>
            <p className="font-mono">用户名: test_user_2 | 密码: password2</p>
          </div>
        </div>
      </div>
    </div>
  )
} 