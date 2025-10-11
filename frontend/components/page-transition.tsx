"use client"

import type { ReactNode } from "react"

interface PageTransitionProps {
  children: ReactNode
  direction?: "left" | "right" | "up"
}

export function PageTransition({ children, direction = "up" }: PageTransitionProps) {
  const getAnimationClass = () => {
    switch (direction) {
      case "left":
        return "animate-slide-in-left"
      case "right":
        return "animate-slide-in-right"
      case "up":
        return "animate-fade-in-up"
      default:
        return "animate-fade-in-up"
    }
  }

  return <div className={`${getAnimationClass()}`}>{children}</div>
}
