"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Bot, X } from "lucide-react"
import { AIAssistant } from "./ai-assistant"

export function FloatingAIButton() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Floating Button */}
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          size="lg"
          className="w-14 h-14 rounded-full shadow-lg animate-pulse-glow"
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? <X className="w-6 h-6" /> : <Bot className="w-6 h-6" />}
        </Button>
      </div>

      {/* AI Assistant Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-40 flex items-end justify-end p-6">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/20" onClick={() => setIsOpen(false)} />

          {/* Assistant Panel */}
          <Card className="relative w-full max-w-md h-[600px] animate-slide-in-right">
            <CardContent className="p-0 h-full">
              <AIAssistant />
            </CardContent>
          </Card>
        </div>
      )}
    </>
  )
}
