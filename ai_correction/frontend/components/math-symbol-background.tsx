"use client"

import { useRef, useEffect, useCallback } from "react"

export function MathSymbolBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouse = useRef({ x: -1000, y: -1000, radius: 110 }) // Slightly increased radius for larger symbols
  const particles = useRef<Particle[]>([])

  const symbols = [
    "Σ",
    "π",
    "∫",
    "√",
    "∞",
    "∂",
    "∇",
    "≈",
    "≠",
    "≤",
    "≥",
    "α",
    "β",
    "γ",
    "δ",
    "ε",
    "ζ",
    "η",
    "θ",
    "ι",
    "κ",
    "λ",
    "μ",
    "ν",
    "ξ",
    "ο",
    "ρ",
    "σ",
    "τ",
    "υ",
    "φ",
    "χ",
    "ψ",
    "ω",
    "∀",
    "∃",
    "∴",
    "∵",
    "∈",
    "∉",
    "⊂",
    "⊃",
    "∪",
    "∩",
    "∅",
    "∧",
    "∨",
    "¬",
    "⇒",
    "⇔",
    "ℏ",
    "ℵ",
    "ℶ",
    "ℷ",
    "ℸ",
    "∑",
    "∏",
    "∐",
    "∯",
    "∮",
    "∰",
    "∱",
    "⨋",
    "⨌",
    "⨍",
    "⨎",
    "⨏",
    "⨐",
    "⨑",
    "⨒",
    "⨓",
    "⨔",
    "⨕",
    "⨖",
    "⨗",
    "⨘",
    "⨙",
    "⨚",
    "⨛",
    "⨜",
  ] // Added more symbols for variety

  class Particle {
    x: number
    y: number
    baseX: number
    baseY: number
    density: number
    symbol: string
    size: number
    baseSize: number // Store base size
    targetSize: number // Target size on hover
    baseColor: string
    color: string
    opacity: number
    baseOpacity: number
    vx: number // velocity x
    vy: number // velocity y

    constructor(x: number, y: number, symbol: string) {
      this.x = x + (Math.random() - 0.5) * 15
      this.y = y + (Math.random() - 0.5) * 15
      this.baseX = x
      this.baseY = y
      this.density = Math.random() * 45 + 15
      this.symbol = symbol
      this.baseSize = Math.random() * 8 + 16 // Increased base size: 16px to 24px
      this.size = this.baseSize
      this.targetSize = 28 // Increased target hover size: 28px
      this.baseOpacity = 0.12 + Math.random() * 0.18 // Slightly increased base opacity
      this.opacity = this.baseOpacity
      this.baseColor = `45, 212, 191` // Teal-400 RGB (cyan-ish)
      this.color = `rgba(${this.baseColor}, ${this.opacity})`
      this.vx = 0
      this.vy = 0
    }

    draw(ctx: CanvasRenderingContext2D) {
      ctx.fillStyle = this.color
      ctx.font = `bold ${this.size}px 'Roboto Mono', monospace`
      ctx.fillText(this.symbol, this.x, this.y)
    }

    update() {
      const dxMouse = mouse.current.x - this.x
      const dyMouse = mouse.current.y - this.y
      const distanceMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse)

      const forceFactor = 0.045
      const repulsionFactor = 0.9

      if (distanceMouse < mouse.current.radius) {
        const angle = Math.atan2(dyMouse, dxMouse)
        const force = (mouse.current.radius - distanceMouse) / mouse.current.radius
        this.vx -= Math.cos(angle) * force * repulsionFactor * (this.density / 20)
        this.vy -= Math.sin(angle) * force * repulsionFactor * (this.density / 20)

        const targetOpacity = 0.6 + (1 - distanceMouse / mouse.current.radius) * 0.4
        this.opacity += (targetOpacity - this.opacity) * 0.25
        this.size += (this.targetSize - this.size) * 0.15 // Grow towards targetSize
      } else {
        this.opacity += (this.baseOpacity - this.opacity) * 0.06
        this.size += (this.baseSize - this.size) * 0.08 // Return to baseSize
      }

      this.vx += (this.baseX - this.x) * forceFactor * (this.density / 100)
      this.vy += (this.baseY - this.y) * forceFactor * (this.density / 100)

      this.vx *= 0.82 // Slightly less damping for more "floaty" return
      this.vy *= 0.82

      this.x += this.vx
      this.y += this.vy

      this.color = `rgba(${this.baseColor}, ${Math.max(0, Math.min(1, this.opacity))})`
    }
  }

  const init = useCallback(
    (canvas: HTMLCanvasElement) => {
      canvas.width = window.innerWidth * window.devicePixelRatio
      canvas.height = window.innerHeight * window.devicePixelRatio
      canvas.style.width = `${window.innerWidth}px`
      canvas.style.height = `${window.innerHeight}px`

      const ctx = canvas.getContext("2d")
      if (!ctx) return
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

      particles.current = []
      const gap = 40 // Adjusted gap for larger symbols
      const symbolCount = symbols.length
      for (let y = 0; y < window.innerHeight + gap; y += gap) {
        for (let x = 0; x < window.innerWidth + gap; x += gap) {
          const randomSymbol = symbols[Math.floor(Math.random() * symbolCount)]
          particles.current.push(new Particle(x, y, randomSymbol))
        }
      }
    },
    [symbols], // symbols array is stable, but good practice
  )

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    init(canvas)
    let animationFrameId: number

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height) // Clear with transparency
      particles.current.forEach((p) => {
        p.update()
        p.draw(ctx)
      })
      animationFrameId = requestAnimationFrame(animate)
    }
    animate()

    const handleMouseMove = (event: MouseEvent) => {
      mouse.current.x = event.clientX
      mouse.current.y = event.clientY
    }

    const handleResize = () => {
      cancelAnimationFrame(animationFrameId)
      init(canvas) // Re-initialize particles on resize
      animate()
    }

    window.addEventListener("mousemove", handleMouseMove)
    window.addEventListener("resize", handleResize)

    return () => {
      window.removeEventListener("mousemove", handleMouseMove)
      window.removeEventListener("resize", handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [init])

  return <canvas ref={canvasRef} className="fixed top-0 left-0 -z-10" />
}
