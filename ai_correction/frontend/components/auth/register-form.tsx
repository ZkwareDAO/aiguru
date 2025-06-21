"use client"

import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { AlertCircle, Loader2, UserPlus, Mail, Lock, User } from "lucide-react"
import apiService, { type RegisterRequest } from "@/lib/api"

interface RegisterFormProps {
  onSuccess?: () => void;
  onToggleForm?: () => void;
}

export function RegisterForm({ onSuccess, onToggleForm }: RegisterFormProps) {
  const [formData, setFormData] = useState<RegisterRequest>({
    username: '',
    password: '',
    confirm_password: '',
    email: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    // 前端验证
    if (formData.password !== formData.confirm_password) {
      setError('密码确认不匹配')
      setLoading(false)
      return
    }

    if (formData.password.length < 6) {
      setError('密码长度至少6位')
      setLoading(false)
      return
    }

    try {
      const result = await apiService.register(formData)
      
      if (result.success) {
        setSuccess(true)
        setTimeout(() => {
          if (onSuccess) {
            onSuccess()
          } else if (onToggleForm) {
            onToggleForm()
          }
        }, 1500)
      } else {
        setError(result.error || '注册失败')
      }
    } catch (err) {
      setError('网络错误，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    if (error) setError(null)
  }

  if (success) {
    return (
      <Card className="w-full max-w-md bg-slate-800/70 border-slate-700/80 backdrop-blur-lg shadow-xl">
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <UserPlus className="w-16 h-16 text-green-400 mx-auto mb-4" />
            <h3 className="text-2xl font-semibold text-green-300 mb-2">注册成功！</h3>
            <p className="text-slate-300">您的账户已创建，正在跳转到登录页面...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md bg-slate-800/70 border-slate-700/80 backdrop-blur-lg shadow-xl">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl text-white flex items-center justify-center gap-2">
          <UserPlus className="w-6 h-6 text-cyan-400" />
          用户注册
        </CardTitle>
        <CardDescription className="text-slate-300">
          创建新账户以开始使用AI智能批改
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
                className="pl-10 bg-slate-700/50 border-slate-600 text-white placeholder-slate-400 focus:border-cyan-500"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-slate-200">邮箱（可选）</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="请输入邮箱地址"
                className="pl-10 bg-slate-700/50 border-slate-600 text-white placeholder-slate-400 focus:border-cyan-500"
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
                placeholder="请输入密码（至少6位）"
                className="pl-10 bg-slate-700/50 border-slate-600 text-white placeholder-slate-400 focus:border-cyan-500"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm_password" className="text-slate-200">确认密码</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                id="confirm_password"
                name="confirm_password"
                type="password"
                value={formData.confirm_password}
                onChange={handleInputChange}
                placeholder="请再次输入密码"
                className="pl-10 bg-slate-700/50 border-slate-600 text-white placeholder-slate-400 focus:border-cyan-500"
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
                注册中...
              </>
            ) : (
              '注册账户'
            )}
          </Button>

          {onToggleForm && (
            <Button
              type="button"
              variant="ghost"
              onClick={onToggleForm}
              className="w-full text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10"
            >
              已有账户？点击登录
            </Button>
          )}
        </form>
      </CardContent>
    </Card>
  )
} 