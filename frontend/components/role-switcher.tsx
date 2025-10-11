"use client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { User, Settings, LogOut, GraduationCap, UserCheck, Users, ChevronDown } from "lucide-react"

interface RoleSwitcherProps {
  currentRole: "student" | "teacher" | "parent"
  userName: string
  userAvatar?: string
  onRoleChange: (role: "student" | "teacher" | "parent") => void
  onSettingsClick: () => void
  onLogout: () => void
}

export function RoleSwitcher({
  currentRole,
  userName,
  userAvatar,
  onRoleChange,
  onSettingsClick,
  onLogout,
}: RoleSwitcherProps) {
  const getRoleIcon = (role: string) => {
    switch (role) {
      case "student":
        return <GraduationCap className="w-4 h-4" />
      case "teacher":
        return <UserCheck className="w-4 h-4" />
      case "parent":
        return <Users className="w-4 h-4" />
      default:
        return <User className="w-4 h-4" />
    }
  }

  const getRoleName = (role: string) => {
    switch (role) {
      case "student":
        return "学生"
      case "teacher":
        return "教师"
      case "parent":
        return "家长"
      default:
        return "用户"
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case "student":
        return "bg-chart-2/10 text-chart-2"
      case "teacher":
        return "bg-chart-1/10 text-chart-1"
      case "parent":
        return "bg-chart-4/10 text-chart-4"
      default:
        return "bg-muted text-muted-foreground"
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-auto p-2 justify-start gap-3">
          <Avatar className="w-8 h-8">
            <AvatarImage src={userAvatar || "/placeholder.svg"} />
            <AvatarFallback className="text-sm">
              {userName
                .split(" ")
                .map((n) => n[0])
                .join("")}
            </AvatarFallback>
          </Avatar>
          <div className="flex items-center gap-2 text-left">
            <div>
              <p className="text-sm font-medium leading-none">{userName}</p>
              <div className="flex items-center gap-1 mt-1">
                <Badge className={`text-xs ${getRoleColor(currentRole)}`}>
                  {getRoleIcon(currentRole)}
                  {getRoleName(currentRole)}
                </Badge>
              </div>
            </div>
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="start">
        <div className="px-2 py-1.5">
          <p className="text-sm font-medium">{userName}</p>
          <p className="text-xs text-muted-foreground">当前角色：{getRoleName(currentRole)}</p>
        </div>
        <DropdownMenuSeparator />

        {/* Role switching options */}
        {["student", "teacher", "parent"].map((role) => (
          <DropdownMenuItem
            key={role}
            onClick={() => onRoleChange(role as any)}
            className={currentRole === role ? "bg-muted" : ""}
          >
            <div className="flex items-center gap-2">
              {getRoleIcon(role)}
              <span>切换到{getRoleName(role)}模式</span>
              {currentRole === role && (
                <Badge variant="secondary" className="ml-auto text-xs">
                  当前
                </Badge>
              )}
            </div>
          </DropdownMenuItem>
        ))}

        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onSettingsClick}>
          <Settings className="w-4 h-4 mr-2" />
          账户设置
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onLogout} className="text-destructive">
          <LogOut className="w-4 h-4 mr-2" />
          退出登录
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
