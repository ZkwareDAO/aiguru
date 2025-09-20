"use client"

import { useState, useEffect } from "react"
import { CheckCircle, Star, Trophy, Target, Sparkles, Heart, ThumbsUp } from "lucide-react"
import { cn } from "@/lib/utils"

interface CompletionAnimationProps {
  type: "success" | "achievement" | "progress" | "celebration"
  message: string
  onComplete?: () => void
  duration?: number
}

export function CompletionAnimation({ type, message, onComplete, duration = 3000 }: CompletionAnimationProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [animationPhase, setAnimationPhase] = useState<"enter" | "display" | "exit">("enter")

  useEffect(() => {
    const timer1 = setTimeout(() => setAnimationPhase("display"), 300)
    const timer2 = setTimeout(() => setAnimationPhase("exit"), duration - 500)
    const timer3 = setTimeout(() => {
      setIsVisible(false)
      onComplete?.()
    }, duration)

    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
      clearTimeout(timer3)
    }
  }, [duration, onComplete])

  if (!isVisible) return null

  const getAnimationConfig = () => {
    switch (type) {
      case "success":
        return {
          icon: CheckCircle,
          color: "text-green-500",
          bgColor: "bg-green-50",
          borderColor: "border-green-200",
          particles: "bg-green-400",
        }
      case "achievement":
        return {
          icon: Trophy,
          color: "text-yellow-500",
          bgColor: "bg-yellow-50",
          borderColor: "border-yellow-200",
          particles: "bg-yellow-400",
        }
      case "progress":
        return {
          icon: Target,
          color: "text-blue-500",
          bgColor: "bg-blue-50",
          borderColor: "border-blue-200",
          particles: "bg-blue-400",
        }
      case "celebration":
        return {
          icon: Sparkles,
          color: "text-purple-500",
          bgColor: "bg-purple-50",
          borderColor: "border-purple-200",
          particles: "bg-purple-400",
        }
    }
  }

  const config = getAnimationConfig()
  const Icon = config.icon

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
      {/* Backdrop */}
      <div
        className={cn(
          "absolute inset-0 bg-black/20 transition-opacity duration-300",
          animationPhase === "enter" ? "opacity-0" : animationPhase === "display" ? "opacity-100" : "opacity-0",
        )}
      />

      {/* Main Animation Container */}
      <div
        className={cn(
          "relative transform transition-all duration-500 ease-out",
          animationPhase === "enter"
            ? "scale-0 rotate-180"
            : animationPhase === "display"
              ? "scale-100 rotate-0"
              : "scale-110 opacity-0",
        )}
      >
        {/* Floating Particles */}
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className={cn("absolute w-2 h-2 rounded-full animate-float-particle", config.particles)}
            style={{
              left: `${Math.cos((i * Math.PI * 2) / 8) * 80 + 50}%`,
              top: `${Math.sin((i * Math.PI * 2) / 8) * 80 + 50}%`,
              animationDelay: `${i * 0.1}s`,
              animationDuration: "2s",
            }}
          />
        ))}

        {/* Main Card */}
        <div
          className={cn(
            "relative bg-white rounded-2xl shadow-2xl border-2 p-8 min-w-[300px] text-center",
            config.bgColor,
            config.borderColor,
            "animate-bounce-gentle",
          )}
        >
          {/* Glow Effect */}
          <div className={cn("absolute inset-0 rounded-2xl blur-xl opacity-30 animate-pulse-glow", config.bgColor)} />

          {/* Icon with Pulse */}
          <div className="relative mb-4">
            <div
              className={cn(
                "w-16 h-16 mx-auto rounded-full flex items-center justify-center animate-pulse-scale",
                config.bgColor,
              )}
            >
              <Icon className={cn("w-8 h-8", config.color)} />
            </div>

            {/* Ripple Effect */}
            <div className={cn("absolute inset-0 w-16 h-16 mx-auto rounded-full animate-ripple", config.borderColor)} />
          </div>

          {/* Message */}
          <p className="text-lg font-semibold text-gray-800 mb-2 animate-fade-in-up">{message}</p>

          {/* Success Indicators */}
          <div className="flex justify-center gap-2 animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
            {[Star, Heart, ThumbsUp].map((IconComp, i) => (
              <IconComp
                key={i}
                className={cn("w-4 h-4 animate-bounce", config.color)}
                style={{ animationDelay: `${i * 0.1}s` }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Hook for triggering completion animations
export function useCompletionAnimation() {
  const [animation, setAnimation] = useState<{
    type: "success" | "achievement" | "progress" | "celebration"
    message: string
  } | null>(null)

  const showAnimation = (type: "success" | "achievement" | "progress" | "celebration", message: string) => {
    setAnimation({ type, message })
  }

  const hideAnimation = () => {
    setAnimation(null)
  }

  return {
    animation,
    showAnimation,
    hideAnimation,
  }
}
