"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { BrainCircuit, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useRouter } from "next/navigation"
import { 
  GraduationCap, 
  History, 
  User, 
  LogOut,
  Menu,
  X
} from 'lucide-react'

export default function Header() {
  const router = useRouter()
  const pathname = usePathname()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState<string | null>(null)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('auth_token')
      const storedUsername = localStorage.getItem('username')
      
      if (token && storedUsername) {
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
              setUsername(decoded.sub || storedUsername)
              return
            } else {
              // Token过期
              localStorage.removeItem('auth_token')
              localStorage.removeItem('username')
            }
          } else {
            // 不是标准JWT格式，但如果有username就认为已认证
            setIsAuthenticated(true)
            setUsername(storedUsername)
            return
          }
        } catch (error) {
          console.log('Token解析失败，但检查是否有用户名:', error)
          // JWT解析失败，但如果有username就认为已认证
          if (storedUsername) {
            setIsAuthenticated(true)
            setUsername(storedUsername)
            return
          }
          localStorage.removeItem('auth_token')
          localStorage.removeItem('username')
        }
      }
      
      setIsAuthenticated(false)
      setUsername('')
    }

    checkAuth()
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('username')
    setIsAuthenticated(false)
    setUsername(null)
    router.push('/auth')
  }

  const navItems = [
    {
      href: '/grading',
      label: '智能批改',
      icon: GraduationCap,
      requireAuth: true
    },
    {
      href: '/history',
      label: '历史记录',
      icon: History,
      requireAuth: true
    },
    {
      href: '/account',
      label: '账户管理',
      icon: User,
      requireAuth: true
    }
  ]

  const filteredNavItems = navItems.filter(item => !item.requireAuth || isAuthenticated)

  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <GraduationCap className="h-8 w-8 text-blue-600" />
              <span className="font-bold text-xl text-gray-900">AI智能批改</span>
        </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            {filteredNavItems.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              
              return (
          <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
          >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
          </Link>
              )
            })}
          </nav>
          
          {/* User Menu */}
          <div className="hidden md:flex items-center space-x-4">
          {isAuthenticated ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-700">
                  欢迎，{username}
              </span>
              <Button
                onClick={handleLogout}
                variant="outline"
                size="sm"
                  className="flex items-center space-x-1"
              >
                  <LogOut className="h-4 w-4" />
                  <span>退出</span>
              </Button>
            </div>
          ) : (
              <Link href="/auth">
                <Button className="flex items-center space-x-1">
                  <User className="h-4 w-4" />
                  <span>登录</span>
                </Button>
              </Link>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 border-t">
              {filteredNavItems.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-md text-base font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
              
              {/* Mobile user menu */}
              <div className="border-t pt-3 mt-3">
                {isAuthenticated ? (
                  <div className="space-y-2">
                    <div className="px-3 py-2 text-sm text-gray-700">
                      欢迎，{username}
                    </div>
              <Button
                      onClick={() => {
                        handleLogout()
                        setIsMobileMenuOpen(false)
                      }}
                variant="outline"
                size="sm"
                      className="w-full flex items-center justify-center space-x-1"
              >
                      <LogOut className="h-4 w-4" />
                      <span>退出</span>
                    </Button>
                  </div>
                ) : (
                  <Link href="/auth" onClick={() => setIsMobileMenuOpen(false)}>
                    <Button className="w-full flex items-center justify-center space-x-1">
                      <User className="h-4 w-4" />
                      <span>登录</span>
              </Button>
                </Link>
                )}
              </div>
            </div>
            </div>
          )}
      </div>
    </header>
  )
}
