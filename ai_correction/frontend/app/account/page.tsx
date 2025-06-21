'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { User, Mail, Lock, Settings, Activity, Download, Trash2 } from 'lucide-react'
import { apiService } from '@/lib/api'
import { useRouter } from 'next/navigation'

interface UserProfile {
  username: string
  email: string
  created_at: string
}

interface UserStatistics {
  total_corrections: number
  monthly_stats: Record<string, number>
  language_stats: Record<string, number>
  strictness_stats: Record<string, number>
  recent_activity: Array<{
    date: string
    count: number
  }>
}

export default function AccountPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [statistics, setStatistics] = useState<UserStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  // 密码修改相关状态
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordLoading, setPasswordLoading] = useState(false)
  
  // 邮箱修改相关状态
  const [newEmail, setNewEmail] = useState('')
  const [emailLoading, setEmailLoading] = useState(false)
  
  const router = useRouter()

  useEffect(() => {
    if (!apiService.isAuthenticated()) {
      router.push('/auth')
      return
    }
    
    loadUserData()
  }, [])

  const loadUserData = async () => {
    try {
      setLoading(true)
      
             // 并行加载用户资料和统计信息
       const [profileResponse, statsResponse] = await Promise.all([
         apiService.getUserProfile(),
         apiService.getUserStatistics()
       ])
      
      if (profileResponse.success && profileResponse.data) {
        setProfile(profileResponse.data)
        setNewEmail(profileResponse.data.email || '')
      } else {
        setError(profileResponse.error || '加载用户资料失败')
      }
      
      if (statsResponse.success && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
      
    } catch (err) {
      setError('加载用户数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (newPassword !== confirmPassword) {
      setError('新密码确认不匹配')
      return
    }
    
    if (newPassword.length < 6) {
      setError('新密码长度至少6位')
      return
    }
    
    try {
      setPasswordLoading(true)
      setError('')
      
             const response = await apiService.changePassword(currentPassword, newPassword)
      
      if (response.success) {
        setSuccess('密码修改成功')
        setCurrentPassword('')
        setNewPassword('')
        setConfirmPassword('')
      } else {
        setError(response.error || '密码修改失败')
      }
    } catch (err) {
      setError('密码修改失败')
    } finally {
      setPasswordLoading(false)
    }
  }

  const handleEmailUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!newEmail || !newEmail.includes('@')) {
      setError('请输入有效的邮箱地址')
      return
    }
    
    try {
      setEmailLoading(true)
      setError('')
      
             const response = await apiService.updateEmail(newEmail)
      
       if (response.success) {
         setSuccess('邮箱更新成功')
         if (profile) {
           setProfile({ ...profile, email: newEmail })
         }
       } else {
         setError(response.error || '邮箱更新失败')
       }
     } catch (err) {
       setError('邮箱更新失败')
     } finally {
       setEmailLoading(false)
     }
   }
 
   const handleClearAllRecords = async () => {
     if (!confirm('确定要清空所有批改记录吗？此操作不可恢复！')) {
       return
     }
     
     try {
       const response = await apiService.clearAllRecords()
       if (response.success) {
         setSuccess('所有记录已清空')
         // 重新加载统计信息
         loadUserData()
       } else {
         setError(response.error || '清空记录失败')
       }
     } catch (err) {
       setError('清空记录失败')
     }
   }
 
   const handleLogout = () => {
     apiService.logout()
     router.push('/auth')
   }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-white text-xl">加载中...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 py-8">
      <div className="container mx-auto px-4 max-w-4xl">
        {/* 页面标题 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">账户管理</h1>
          <p className="text-slate-300">管理您的个人信息和系统设置</p>
        </div>

        {/* 消息提示 */}
        {error && (
          <Alert className="mb-6 border-red-500 bg-red-500/10">
            <AlertDescription className="text-red-400">{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert className="mb-6 border-green-500 bg-green-500/10">
            <AlertDescription className="text-green-400">{success}</AlertDescription>
          </Alert>
        )}

        {/* 主要内容区域 */}
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-slate-800/50">
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              个人资料
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Lock className="w-4 h-4" />
              安全设置
            </TabsTrigger>
            <TabsTrigger value="statistics" className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              使用统计
            </TabsTrigger>
            <TabsTrigger value="data" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              数据管理
            </TabsTrigger>
          </TabsList>

          {/* 个人资料 */}
          <TabsContent value="profile">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
                  <User className="w-6 h-6 text-cyan-400" />
                  个人资料
                </h2>
              </CardHeader>
              <CardContent className="space-y-6">
                {profile && (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <Label className="text-slate-300">用户名</Label>
                        <Input
                          value={profile.username}
                          disabled
                          className="mt-2 bg-slate-700/50 border-slate-600 text-white"
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">注册时间</Label>
                        <Input
                          value={new Date(profile.created_at).toLocaleString('zh-CN')}
                          disabled
                          className="mt-2 bg-slate-700/50 border-slate-600 text-white"
                        />
                      </div>
                    </div>
                    
                    <form onSubmit={handleEmailUpdate} className="space-y-4">
                      <div>
                        <Label className="text-slate-300">邮箱地址</Label>
                        <div className="flex gap-4 mt-2">
                          <Input
                            type="email"
                            value={newEmail}
                            onChange={(e) => setNewEmail(e.target.value)}
                            className="bg-slate-700/50 border-slate-600 text-white flex-1"
                            placeholder="请输入邮箱地址"
                          />
                          <Button
                            type="submit"
                            disabled={emailLoading || newEmail === profile.email}
                            className="bg-cyan-600 hover:bg-cyan-700"
                          >
                            {emailLoading ? '更新中...' : '更新邮箱'}
                          </Button>
                        </div>
                      </div>
                    </form>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 安全设置 */}
          <TabsContent value="security">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
                  <Lock className="w-6 h-6 text-cyan-400" />
                  安全设置
                </h2>
              </CardHeader>
              <CardContent>
                <form onSubmit={handlePasswordChange} className="space-y-6">
                  <div>
                    <Label className="text-slate-300">当前密码</Label>
                    <Input
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="mt-2 bg-slate-700/50 border-slate-600 text-white"
                      placeholder="请输入当前密码"
                      required
                    />
                  </div>
                  
                  <div>
                    <Label className="text-slate-300">新密码</Label>
                    <Input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="mt-2 bg-slate-700/50 border-slate-600 text-white"
                      placeholder="请输入新密码（至少6位）"
                      minLength={6}
                      required
                    />
                  </div>
                  
                  <div>
                    <Label className="text-slate-300">确认新密码</Label>
                    <Input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="mt-2 bg-slate-700/50 border-slate-600 text-white"
                      placeholder="请再次输入新密码"
                      required
                    />
                  </div>
                  
                  <Button
                    type="submit"
                    disabled={passwordLoading || !currentPassword || !newPassword || !confirmPassword}
                    className="w-full bg-cyan-600 hover:bg-cyan-700"
                  >
                    {passwordLoading ? '修改中...' : '修改密码'}
                  </Button>
                </form>
                
                <div className="mt-8 pt-6 border-t border-slate-700">
                  <Button
                    onClick={handleLogout}
                    variant="outline"
                    className="w-full border-red-500 text-red-400 hover:bg-red-500/10"
                  >
                    退出登录
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 使用统计 */}
          <TabsContent value="statistics">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
                  <Activity className="w-6 h-6 text-cyan-400" />
                  使用统计
                </h2>
              </CardHeader>
              <CardContent>
                {statistics ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="text-center p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-3xl font-bold text-cyan-400">{statistics.total_corrections}</div>
                        <div className="text-slate-300">总批改次数</div>
                      </div>
                      <div className="text-center p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-3xl font-bold text-green-400">
                          {Object.keys(statistics.monthly_stats).length}
                        </div>
                        <div className="text-slate-300">活跃月数</div>
                      </div>
                      <div className="text-center p-4 bg-slate-700/30 rounded-lg">
                        <div className="text-3xl font-bold text-purple-400">
                          {statistics.recent_activity.length}
                        </div>
                        <div className="text-slate-300">近期活动天数</div>
                      </div>
                    </div>
                    
                    {/* 语言偏好统计 */}
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-3">语言偏好</h3>
                      <div className="space-y-2">
                        {Object.entries(statistics.language_stats).map(([lang, count]) => (
                          <div key={lang} className="flex justify-between items-center p-2 bg-slate-700/30 rounded">
                            <span className="text-slate-300">{lang === 'zh' ? '中文' : '英文'}</span>
                            <span className="text-cyan-400 font-semibold">{count} 次</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    {/* 严格程度统计 */}
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-3">批改严格程度偏好</h3>
                      <div className="space-y-2">
                        {Object.entries(statistics.strictness_stats).map(([level, count]) => (
                          <div key={level} className="flex justify-between items-center p-2 bg-slate-700/30 rounded">
                            <span className="text-slate-300">{level}</span>
                            <span className="text-cyan-400 font-semibold">{count} 次</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-slate-300">
                    <Activity className="w-16 h-16 mx-auto mb-4 text-slate-500" />
                    <p>暂无统计数据</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 数据管理 */}
          <TabsContent value="data">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <h2 className="text-2xl font-semibold text-white flex items-center gap-2">
                  <Settings className="w-6 h-6 text-cyan-400" />
                  数据管理
                </h2>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-slate-700/30 rounded-lg">
                    <div>
                      <h3 className="text-white font-semibold">批改历史记录</h3>
                      <p className="text-slate-300 text-sm">查看和管理您的所有批改记录</p>
                    </div>
                    <Button
                      onClick={() => router.push('/history')}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      查看记录
                    </Button>
                  </div>
                  
                  <div className="flex items-center justify-between p-4 bg-red-900/20 border border-red-700/50 rounded-lg">
                    <div>
                      <h3 className="text-white font-semibold">清空所有数据</h3>
                      <p className="text-slate-300 text-sm">永久删除您的所有批改记录，此操作不可恢复</p>
                    </div>
                    <Button
                      onClick={handleClearAllRecords}
                      variant="destructive"
                      className="bg-red-600 hover:bg-red-700"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      清空数据
                    </Button>
                  </div>
                </div>
                
                <div className="bg-slate-700/30 p-4 rounded-lg">
                  <h3 className="text-white font-semibold mb-2">数据保护说明</h3>
                  <ul className="text-slate-300 text-sm space-y-1">
                    <li>• 您的数据仅保存在本地服务器上</li>
                    <li>• 批改记录会自动清理超过7天的旧数据</li>
                    <li>• 您可以随时导出或删除自己的数据</li>
                    <li>• 我们不会与第三方分享您的个人信息</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
} 