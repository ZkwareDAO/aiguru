"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ArrowRight, BookOpenCheck, Cpu, Zap, Lightbulb } from "lucide-react"

// ... (rest of the HomePage component remains the same as previous version)
// Make sure the main content container inside HomePage does NOT have its own pt-16/pt-20 if layout's main already has it.
// The existing structure for HomePage:
// <div className="relative isolate overflow-hidden pt-16 sm:pt-20">
// This pt-16/pt-20 should be REMOVED because layout.tsx's <main> now handles global padding.

const features = [
  {
    icon: <Zap className="h-10 w-10 text-purple-400" />,
    title: "闪电般快速反馈",
    description: "提交即刻获得AI分析结果，无需漫长等待，教学效率指数级提升。",
    glowColor: "purple",
  },
  {
    icon: <BookOpenCheck className="h-10 w-10 text-sky-400" />,
    title: "多维度精准评估",
    description: "超越简单对错判断，深入剖析知识点掌握、逻辑思维、创新表达。",
    glowColor: "sky",
  },
  {
    icon: <Lightbulb className="h-10 w-10 text-yellow-400" />,
    title: "个性化学习建议",
    description: "基于学生作答特点，AI生成针对性提升建议，助力因材施教。",
    glowColor: "yellow",
  },
]

const coreExperiences = [
  {
    title: "数学难题迎刃而解",
    description: "上传复杂数学题照片，AI不仅给出答案，更能分析解题步骤，指出常见错误。",
    image: "/placeholder.svg?width=400&height=300",
    tags: ["数学", "步骤分析", "AI辅导"],
  },
  {
    title: "作文批改细致入微",
    description: "AI对学生作文进行多维度评价：从立意、结构到语言表达，提供详尽修改意见。",
    image: "/placeholder.svg?width=400&height=300",
    tags: ["语文", "写作提升", "智能润色"],
  },
  {
    title: "编程作业智能Debug",
    description: "提交代码，AI辅助查找逻辑错误、语法问题，并提供优化方案，加速编程学习。",
    image: "/placeholder.svg?width=400&height=300",
    tags: ["编程", "代码审查", "错误定位"],
  },
]

export default function HomePage() {
  return (
    <>
      {/* MathSymbolBackground and Header are now in layout.tsx */}
      {/* The main div for HomePage content. The pt-20 is handled by layout's <main> tag. */}
      <div className="relative isolate overflow-hidden">
        {/* Hero Section */}
        <section className="relative flex h-[calc(100vh-5rem)] min-h-[650px] flex-col items-center justify-center text-center px-4 md:px-6">
          {/* Ensure this section doesn't have conflicting full-page opaque background if symbols are to show */}
          <div className="absolute inset-0 -z-20 bg-black/75"></div>{" "}
          {/* Slightly darker overlay for better text contrast over symbols */}
          {/* Pulsating Blobs */}
          <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-cyan-500/20 rounded-full filter blur-3xl opacity-50 animate-blob"></div>
          <div className="absolute top-1/3 right-1/4 w-72 h-72 bg-purple-500/20 rounded-full filter blur-3xl opacity-50 animate-blob animation-delay-2000"></div>
          <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-sky-500/20 rounded-full filter blur-3xl opacity-50 animate-blob animation-delay-4000"></div>
          <div className="animate-hero-content-appear space-y-8 max-w-3xl">
            <h1 className="text-5xl font-extrabold tracking-tight text-white sm:text-6xl md:text-7xl lg:text-8xl leading-tight">
              <span className="block animated-text-bg clip-text bg-gradient-to-r from-cyan-400 via-sky-400 to-purple-500">
                AI赋能教育
              </span>
              <span className="block text-slate-200 mt-2 sm:mt-4">智能批改新纪元</span>
            </h1>
            <p className="mx-auto text-lg text-slate-300 md:text-xl max-w-2xl">
              释放教师生产力，激发学生潜能。体验前所未有的作业与试卷智能分析、即时反馈和深度洞察。
            </p>
            <div className="flex flex-col gap-4 sm:flex-row justify-center items-center">
              <Button
                asChild
                size="xl"
                className="group bg-gradient-to-r from-cyan-500 via-sky-500 to-purple-600 text-white font-bold text-xl px-10 py-7 rounded-xl shadow-2xl shadow-cyan-500/40 hover:shadow-purple-500/60 transition-all duration-300 transform hover:scale-110 hover:rotate-[-2deg] focus:outline-none focus:ring-4 focus:ring-purple-400 focus:ring-offset-2 focus:ring-offset-black"
              >
                <Link href="/grading">
                  <Cpu className="mr-3 h-7 w-7 transition-transform duration-500 group-hover:animate-pulse-fast" />
                  立即开始批改
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                size="xl"
                className="group text-slate-200 border-slate-600 hover:bg-slate-800/50 hover:text-white hover:border-cyan-500 font-semibold text-lg px-8 py-7 rounded-xl transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-black"
              >
                <Link href="/test">
                  系统测试
                <ArrowRight className="ml-2 h-5 w-5 transition-transform duration-300 group-hover:translate-x-1.5" />
                </Link>
              </Button>
            </div>
            
            {/* 快速访问功能 */}
            <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-white hover:bg-slate-800/50 transition-all duration-200"
              >
                <Link href="/auth">🔐 登录</Link>
              </Button>
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-white hover:bg-slate-800/50 transition-all duration-200"
              >
                <Link href="/results">📚 批改记录</Link>
              </Button>
              <Button
                asChild
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-white hover:bg-slate-800/50 transition-all duration-200"
              >
                <Link href="/test">🔧 系统测试</Link>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-slate-300 hover:text-white hover:bg-slate-800/50 transition-all duration-200"
                onClick={() => window.open('http://localhost:8000/docs', '_blank')}
              >
                📖 API文档
              </Button>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-24 sm:py-32 bg-black/85 backdrop-blur-sm">
          {" "}
          {/* Slightly more opaque for readability over symbols */}
          <div className="container mx-auto px-4 md:px-6">
            <div className="mx-auto max-w-3xl text-center mb-16">
              <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl md:text-6xl animated-text-bg clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-orange-400">
                核心优势
              </h2>
              <p className="mt-6 text-lg text-slate-300">我们不仅仅是批改，更是智能化的教育革新伙伴。</p>
            </div>
            <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
              {features.map((feature, index) => (
                <div
                  key={feature.title}
                  className={`feature-card-enhanced group rounded-2xl border border-slate-700/80 bg-slate-900/70 p-8 transition-all duration-300 hover:border-${feature.glowColor}-500/70 hover:shadow-${feature.glowColor}-500/30 hover:shadow-2xl hover:-translate-y-3 relative overflow-hidden backdrop-blur-xs`} // Added backdrop-blur-xs
                  style={{ animationDelay: `${index * 200}ms` }}
                >
                  <div
                    className={`absolute -top-1/3 -right-1/4 w-1/2 h-1/2 bg-${feature.glowColor}-500/10 rounded-full filter blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500`}
                  ></div>
                  <div
                    className={`mb-6 flex h-16 w-16 items-center justify-center rounded-xl bg-gradient-to-br from-${feature.glowColor}-500/20 to-slate-800 border border-${feature.glowColor}-500/30 shadow-lg`}
                  >
                    {feature.icon}
                  </div>
                  <h3 className="text-2xl font-semibold text-white mb-3">{feature.title}</h3>
                  <p className="text-slate-400 leading-relaxed">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Core Experience / Examples Section */}
        <section id="core-experience" className="py-24 sm:py-32 bg-black/90 backdrop-blur-sm">
          {" "}
          {/* Slightly more opaque for readability */}
          <div className="container mx-auto px-4 md:px-6">
            <div className="mx-auto max-w-3xl text-center mb-16">
              <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl md:text-6xl animated-text-bg clip-text bg-gradient-to-r from-green-400 via-teal-400 to-cyan-400">
                核心体验实例
              </h2>
              <p className="mt-6 text-lg text-slate-300">直观感受 AI 如何革新不同学科的作业批改与辅导。</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
              {coreExperiences.map((exp, index) => (
                <div
                  key={exp.title}
                  className="example-card group rounded-2xl border border-slate-800 bg-slate-900/80 overflow-hidden transition-all duration-300 hover:shadow-2xl hover:shadow-cyan-500/20 hover:border-cyan-600/50 transform hover:-translate-y-2 backdrop-blur-xs" // Added backdrop-blur-xs
                  style={{ animationDelay: `${index * 200 + 600}ms` }}
                >
                  <div className="relative h-56 overflow-hidden">
                    <img
                      src={exp.image || "/placeholder.svg"}
                      alt={exp.title}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent"></div>
                  </div>
                  <div className="p-6">
                    <h3 className="text-xl font-semibold text-white mb-2">{exp.title}</h3>
                    <p className="text-slate-400 text-sm mb-4 h-20 overflow-hidden">{exp.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {exp.tags.map((tag) => (
                        <span key={tag} className="text-xs bg-slate-700/50 text-cyan-300 px-2.5 py-1 rounded-full">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
      <footer className="bg-black border-t border-slate-800/50 py-10">
        <div className="container mx-auto px-4 md:px-6 text-center text-slate-500">
          <p>&copy; {new Date().getFullYear()} AI 智能批改平台 X. 未来教育，即刻触达。</p>
        </div>
      </footer>
      {/* Global styles from previous version remain the same */}
      <style jsx global>{`
        .clip-text {
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          text-fill-color: transparent;
        }
        .animated-text-bg {
          background-size: 200% auto;
          animation: text-flow-animation 5s linear infinite;
        }
        @keyframes text-flow-animation {
          to {
            background-position: 200% center;
          }
        }
        
        @keyframes hero-content-appear {
          from { opacity: 0; transform: translateY(40px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .animate-hero-content-appear {
          animation: hero-content-appear 1s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
        }

        .feature-card-enhanced, .example-card {
          opacity: 0;
          transform: translateY(30px);
          animation: card-appear 0.8s ease-out forwards;
        }
        @keyframes card-appear {
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes pulse-fast {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.15); }
        }
        .animate-pulse-fast { animation: pulse-fast 1s infinite; }

        @keyframes sway {
          0%, 100% { transform: rotate(-3deg); }
          50% { transform: rotate(3deg); }
        }
        .animate-sway { animation: sway 1.5s ease-in-out infinite; }

        @keyframes blob {
          0% { transform: scale(1) translate(0px, 0px); opacity: 0.5; }
          33% { transform: scale(1.1) translate(30px, -40px); opacity: 0.6; }
          66% { transform: scale(0.9) translate(-20px, 20px); opacity: 0.4; }
          100% { transform: scale(1) translate(0px, 0px); opacity: 0.5; }
        }
        .animate-blob { animation: blob 15s infinite cubic-bezier(0.455, 0.03, 0.515, 0.955); }
        .animation-delay-2000 { animation-delay: -5s; }
        .animation-delay-4000 { animation-delay: -10s; }
      `}</style>
    </>
  )
}
