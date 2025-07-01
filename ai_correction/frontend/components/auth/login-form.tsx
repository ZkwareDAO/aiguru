"use client"

import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { AlertCircle, Loader2, Lock, User } from "lucide-react"
import { apiService, type LoginRequest } from "@/lib/api"
import { useRouter } from 'next/navigation'

interface LoginFormProps {
  onSuccess?: () => void;
  onToggleForm?: () => void;
}

export function LoginForm({ onSuccess, onToggleForm }: LoginFormProps) {
  const [formData, setFormData] = useState<LoginRequest>({
    username: '',
    password: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const result = await apiService.login(formData)
      
      if (result.access_token) {
        if (onSuccess) {
          onSuccess()
        } else {
          router.push('/grading')
        }
      } else {
        setError('登录失败')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '网络错误，请重试'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev: LoginRequest) => ({
      ...prev,
      [name]: value
    }))
    if (error) setError(null)
  }

  // 填充测试账户
  const fillTestAccount = () => {
    setFormData({
      username: 'test_user_1',
      password: 'password1'
    })
    setError(null)
  }

  return (
    <Card className="w-full max-w-md bg-slate-800/70 border-slate-700/80 backdrop-blur-lg shadow-xl">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl text-white flex items-center justify-center gap-2">
          <Lock className="w-6 h-6 text-cyan-400" />
          用户登录
        </CardTitle>
        <CardDescription className="text-slate-300">
          登录您的账户以开始使用AI智能批改
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username" className="text-slate-200">用户名</Label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                id="username"
                name="username"
                type="text"
                value={formData.username}
                onChange={handleInputChange}
                placeholder="请输入用户名"
                className="pl-10 bg-slate-700/50 border-2 border-slate-600 text-white placeholder-slate-400 focus:border-cyan-500 focus:ring-cyan-500/20 transition-colors"
                required
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="password" className="text-slate-200">密码</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleInputChange}
                placeholder="请输入密码"
                className="pl-10 bg-slate-700/50 border-2 border-slate-600 text-white placeholder-slate-400 focus:border-cyan-500 focus:ring-cyan-500/20 transition-colors"
                required
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-900/40 border border-red-700/60 text-red-200 rounded-lg flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <Button
            type="submit"
            className="w-full bg-gradient-to-r from-cyan-500 to-sky-600 hover:from-cyan-600 hover:to-sky-700 text-white font-semibold py-2.5 transition-all duration-300 disabled:opacity-60"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                登录中...
              </>
            ) : (
              '登录'
            )}
          </Button>

          <div className="flex flex-col space-y-2">
            <Button
              type="button"
              variant="outline"
              onClick={fillTestAccount}
              className="w-full border-slate-600 text-slate-300 hover:bg-slate-700/50 hover:text-white"
            >
              使用测试账户
            </Button>
            
            {onToggleForm && (
              <Button
                type="button"
                variant="ghost"
                onClick={onToggleForm}
                className="w-full text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10"
              >
                没有账户？点击注册
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  )
} 