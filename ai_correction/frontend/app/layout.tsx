import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { cn } from "@/lib/utils"
import Header from "@/components/header" // Import Header
import { MathSymbolBackground } from "@/components/math-symbol-background" // Import MathSymbolBackground

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })

export const metadata: Metadata = {
  title: {
    default: "AI 智能批改平台 X",
    template: "%s | AI 智能批改平台 X",
  },
  description: "体验未来化的智能评分与作业分析，由尖端 AI 强力驱动。动态、精准、高效。",
    generator: 'v0.dev'
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" className="dark">
      <body
        className={cn(
          "min-h-screen bg-black font-sans antialiased selection:bg-cyan-500 selection:text-white",
          inter.variable,
        )}
      >
        <MathSymbolBackground /> {/* Global dynamic background */}
        <Header /> {/* Global header */}
        <main className="relative z-10 pt-20">
          {/* Add padding for fixed header, ensure content is above background */}
          {children}
        </main>
      </body>
    </html>
  )
}
