"use client"

import { useEffect, useState, useRef } from "react"

interface BrandLaunchAnimationProps {
  onComplete: () => void
}

interface TetrisBlock {
  id: number
  x: number
  y: number
  shape: number[][]
  color: string
  rotation: number
  falling: boolean
}

const TETRIS_SHAPES = [
  // I-piece
  [[1, 1, 1, 1]],
  // O-piece
  [
    [1, 1],
    [1, 1],
  ],
  // T-piece
  [
    [0, 1, 0],
    [1, 1, 1],
  ],
  // S-piece
  [
    [0, 1, 1],
    [1, 1, 0],
  ],
  // Z-piece
  [
    [1, 1, 0],
    [0, 1, 1],
  ],
  // J-piece
  [
    [1, 0, 0],
    [1, 1, 1],
  ],
  // L-piece
  [
    [0, 0, 1],
    [1, 1, 1],
  ],
]

const TETRIS_COLORS = [
  "#00f5ff", // cyan
  "#ffff00", // yellow
  "#a020f0", // purple
  "#00ff00", // green
  "#ff0000", // red
  "#0000ff", // blue
  "#ffa500", // orange
]

export function BrandLaunchAnimation({ onComplete }: BrandLaunchAnimationProps) {
  const [stage, setStage] = useState(0)
  const [blocks, setBlocks] = useState<TetrisBlock[]>([])
  const [gridBlocks, setGridBlocks] = useState<boolean[][]>([])
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()

  // Initialize grid
  useEffect(() => {
    const grid = Array(20)
      .fill(null)
      .map(() => Array(10).fill(false))
    setGridBlocks(grid)
  }, [])

  useEffect(() => {
    const timer1 = setTimeout(() => setStage(1), 500)
    const timer2 = setTimeout(() => setStage(2), 2000)
    const timer3 = setTimeout(() => setStage(3), 4000)
    const timer4 = setTimeout(() => setStage(4), 5500)
    const timer5 = setTimeout(() => onComplete(), 7000)

    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
      clearTimeout(timer3)
      clearTimeout(timer4)
      clearTimeout(timer5)
    }
  }, [onComplete])

  // Generate falling blocks
  useEffect(() => {
    if (stage < 1 || stage > 3) return

    const interval = setInterval(() => {
      const newBlock: TetrisBlock = {
        id: Date.now() + Math.random(),
        x: Math.floor(Math.random() * 8),
        y: -2,
        shape: TETRIS_SHAPES[Math.floor(Math.random() * TETRIS_SHAPES.length)],
        color: TETRIS_COLORS[Math.floor(Math.random() * TETRIS_COLORS.length)],
        rotation: 0,
        falling: true,
      }

      setBlocks((prev) => [...prev, newBlock])
    }, 800)

    return () => clearInterval(interval)
  }, [stage])

  // Animate falling blocks
  useEffect(() => {
    if (stage < 1) return

    const animate = () => {
      setBlocks((prev) =>
        prev
          .map((block) => {
            if (!block.falling) return block

            const newY = block.y + 0.1
            if (newY > 18) {
              return { ...block, falling: false, y: 18 }
            }
            return { ...block, y: newY }
          })
          .filter((block) => block.y < 20),
      )

      animationRef.current = requestAnimationFrame(animate)
    }

    animationRef.current = requestAnimationFrame(animate)
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [stage])

  // Fill and clear animation
  useEffect(() => {
    if (stage !== 4) return

    const fillGrid = () => {
      const newGrid = Array(20)
        .fill(null)
        .map(() => Array(10).fill(true))
      setGridBlocks(newGrid)

      // Clear from top to bottom
      setTimeout(() => {
        let row = 0
        const clearRowInterval = setInterval(() => {
          setGridBlocks((prev) => {
            const newGrid = [...prev]
            newGrid[row] = Array(10).fill(false)
            return newGrid
          })

          row++
          if (row >= 20) {
            clearInterval(clearRowInterval)
          }
        }, 50)
      }, 300)
    }

    fillGrid()
  }, [stage])

  return (
    <div className="fixed inset-0 z-50 bg-gray-900 flex items-center justify-center overflow-hidden">
      {/* Tetris Grid Background */}
      <div className="absolute inset-0 opacity-20">
        <div className="grid grid-cols-10 gap-px h-full w-full max-w-md mx-auto">
          {gridBlocks.flat().map((filled, index) => (
            <div
              key={index}
              className={`border border-cyan-500/30 transition-all duration-100 ${
                filled ? "bg-cyan-400" : "bg-transparent"
              }`}
            />
          ))}
        </div>
      </div>

      {/* Falling Tetris Blocks */}
      <div className="absolute inset-0 max-w-md mx-auto">
        {blocks.map((block) => (
          <div
            key={block.id}
            className="absolute transition-all duration-100"
            style={{
              left: `${block.x * 10}%`,
              top: `${block.y * 5}%`,
              transform: `rotate(${block.rotation}deg)`,
            }}
          >
            {block.shape.map((row, rowIndex) => (
              <div key={rowIndex} className="flex">
                {row.map((cell, cellIndex) => (
                  <div
                    key={cellIndex}
                    className={`w-6 h-6 ${cell ? "opacity-80" : "opacity-0"}`}
                    style={{
                      backgroundColor: cell ? block.color : "transparent",
                      boxShadow: cell ? `0 0 10px ${block.color}` : "none",
                    }}
                  />
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Brand Content */}
      <div className="relative z-10 text-center">
        {/* Logo */}
        <div
          className={`mb-8 transition-all duration-1000 ${stage >= 1 ? "opacity-100 scale-100" : "opacity-0 scale-50"}`}
        >
          <div className="relative">
            <div className="w-40 h-40 mx-auto bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-3xl flex items-center justify-center shadow-2xl animate-pulse">
              <div className="text-6xl font-bold text-white">AI</div>
            </div>
            <div className="absolute -top-4 -right-4 w-8 h-8 bg-yellow-400 rounded-full animate-bounce"></div>
          </div>
        </div>

        {/* Brand Name */}
        <div
          className={`mb-6 transition-all duration-1000 delay-500 ${stage >= 2 ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}
        >
          <h1
            className="text-8xl font-bold text-cyan-100 animate-pulse"
            style={{
              textShadow:
                "0 0 30px rgba(34, 211, 238, 1), 0 0 60px rgba(59, 130, 246, 0.8), 0 0 90px rgba(147, 51, 234, 0.6)",
              filter: "drop-shadow(0 0 20px rgba(34, 211, 238, 0.8))",
            }}
          >
            aiguru
          </h1>
          <div className="flex justify-center mt-4">
            {["智", "能", "批", "改", "专", "家"].map((char, index) => (
              <span
                key={index}
                className={`text-2xl text-cyan-100 mx-1 transition-all duration-300 font-semibold`}
                style={{
                  animationDelay: `${index * 100}ms`,
                  animation: stage >= 2 ? "fadeInUp 0.6s ease-out forwards" : "none",
                  textShadow: "0 0 15px rgba(34, 211, 238, 0.8), 0 0 30px rgba(59, 130, 246, 0.6)",
                }}
              >
                {char}
              </span>
            ))}
          </div>
        </div>

        {/* Features */}
        <div
          className={`flex justify-center gap-8 transition-all duration-1000 delay-1000 ${stage >= 3 ? "opacity-100 scale-100" : "opacity-0 scale-50"}`}
        >
          {[
            { text: "AI批改", color: "from-cyan-400 to-blue-500" },
            { text: "智能分析", color: "from-blue-500 to-purple-500" },
            { text: "高效管理", color: "from-purple-500 to-pink-500" },
          ].map((feature, index) => (
            <div
              key={index}
              className={`px-6 py-3 rounded-full bg-gradient-to-r ${feature.color} text-white font-semibold shadow-lg animate-bounce`}
              style={{ animationDelay: `${index * 200}ms` }}
            >
              {feature.text}
            </div>
          ))}
        </div>

        {/* Loading Progress */}
        <div className={`mt-12 transition-all duration-1000 ${stage >= 1 ? "opacity-100" : "opacity-0"}`}>
          <div className="w-80 h-3 bg-gray-700 rounded-full mx-auto overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 to-purple-500 rounded-full transition-all duration-2000 ease-out shadow-lg"
              style={{
                width: `${Math.min((stage / 4) * 100, 100)}%`,
                boxShadow: "0 0 20px rgba(34, 211, 238, 0.5)",
              }}
            />
          </div>
          <p className="text-cyan-300 mt-4 text-lg font-medium">
            {stage === 1 && "初始化AI引擎..."}
            {stage === 2 && "加载智能模块..."}
            {stage === 3 && "准备批改系统..."}
            {stage >= 4 && "启动完成!"}
          </p>
        </div>
      </div>

      {/* Exit Animation Overlay */}
      <div
        className={`absolute inset-0 bg-gray-900 transition-all duration-1000 ${
          stage >= 4 ? "opacity-100" : "opacity-0"
        }`}
        style={{
          clipPath: stage >= 4 ? "inset(0 0 0 0)" : "inset(100% 0 0 0)",
          transition: "clip-path 1.5s ease-in-out",
        }}
      />

      <style jsx>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  )
}
