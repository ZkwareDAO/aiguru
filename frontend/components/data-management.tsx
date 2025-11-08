"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Switch } from "@/components/ui/switch"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Upload,
  Download,
  FileSpreadsheet,
  BarChart3,
  Filter,
  RefreshCw,
  Eye,
  Share2,
  Plus,
  Trash2,
  Edit,
} from "lucide-react"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts"

interface DataImportExportProps {
  userRole: "student" | "teacher" | "parent"
}

interface ChartConfig {
  id: string
  name: string
  type: "line" | "bar" | "area" | "pie" | "radar" | "scatter"
  dataSource: string
  xAxis?: string
  yAxis?: string
  filters: Record<string, any>
  dateRange: { start: string; end: string }
  isPublic: boolean
  createdAt: string
}

export function DataManagement({ userRole }: DataImportExportProps) {
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [showExportDialog, setShowExportDialog] = useState(false)
  const [showChartDialog, setShowChartDialog] = useState(false)
  const [selectedChart, setSelectedChart] = useState<ChartConfig | null>(null)
  const [importProgress, setImportProgress] = useState(0)
  const [exportProgress, setExportProgress] = useState(0)

  // Mock data for charts
  const mockStudentData = [
    { name: "张小明", math: 92, english: 88, physics: 93, total: 273 },
    { name: "李小红", math: 85, english: 92, physics: 87, total: 264 },
    { name: "王小华", math: 82, english: 87, physics: 86, total: 255 },
    { name: "刘小强", math: 78, english: 85, physics: 83, total: 246 },
    { name: "陈小美", math: 75, english: 82, physics: 80, total: 237 },
  ]

  const mockTimeSeriesData = [
    { date: "2024-01", average: 75, submissions: 120 },
    { date: "2024-02", average: 78, submissions: 135 },
    { date: "2024-03", average: 82, submissions: 142 },
    { date: "2024-04", average: 85, submissions: 158 },
    { date: "2024-05", average: 88, submissions: 165 },
  ]

  const mockSubjectDistribution = [
    { name: "数学", value: 35, color: "#22c55e" },
    { name: "英语", value: 25, color: "#3b82f6" },
    { name: "物理", value: 20, color: "#f59e0b" },
    { name: "化学", value: 15, color: "#ef4444" },
    { name: "生物", value: 5, color: "#8b5cf6" },
  ]

  const mockCustomCharts: ChartConfig[] = [
    {
      id: "chart-1",
      name: "班级成绩趋势分析",
      type: "line",
      dataSource: "student_scores",
      xAxis: "date",
      yAxis: "average_score",
      filters: { subject: "all", class: "高三1班" },
      dateRange: { start: "2024-01-01", end: "2024-05-31" },
      isPublic: true,
      createdAt: "2024-01-15",
    },
    {
      id: "chart-2",
      name: "学科分布统计",
      type: "pie",
      dataSource: "assignment_data",
      filters: { grade: "高三" },
      dateRange: { start: "2024-01-01", end: "2024-05-31" },
      isPublic: false,
      createdAt: "2024-02-10",
    },
    {
      id: "chart-3",
      name: "学生能力雷达图",
      type: "radar",
      dataSource: "knowledge_points",
      filters: { student_id: "all" },
      dateRange: { start: "2024-01-01", end: "2024-05-31" },
      isPublic: true,
      createdAt: "2024-03-05",
    },
  ]

  const handleImport = async (file: File) => {
    setImportProgress(0)
    // Simulate import progress
    const interval = setInterval(() => {
      setImportProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + 10
      })
    }, 200)
  }

  const handleExport = async (format: string, dataType: string) => {
    setExportProgress(0)
    // Simulate export progress
    const interval = setInterval(() => {
      setExportProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + 15
      })
    }, 300)
  }

  const renderChart = (config: ChartConfig) => {
    switch (config.type) {
      case "line":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={mockTimeSeriesData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="average" stroke="#22c55e" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )
      case "bar":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={mockStudentData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="total" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        )
      case "pie":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <RechartsPieChart>
              <Tooltip />
              <RechartsPieChart data={mockSubjectDistribution}>
                {mockSubjectDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </RechartsPieChart>
            </RechartsPieChart>
          </ResponsiveContainer>
        )
      case "radar":
        return (
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={mockStudentData.slice(0, 1)}>
              <PolarGrid />
              <PolarAngleAxis dataKey="name" />
              <PolarRadiusAxis />
              <Radar name="成绩" dataKey="math" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        )
      default:
        return <div className="h-64 flex items-center justify-center text-muted-foreground">暂不支持此图表类型</div>
    }
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">数据管理</h2>
          <p className="text-muted-foreground">导入导出数据，创建自定义图表分析</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Upload className="w-4 h-4 mr-2" />
                导入数据
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>导入数据</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>数据类型</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择数据类型" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="students">学生信息</SelectItem>
                        <SelectItem value="scores">成绩数据</SelectItem>
                        <SelectItem value="assignments">作业数据</SelectItem>
                        <SelectItem value="classes">班级信息</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>文件格式</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择格式" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="csv">CSV</SelectItem>
                        <SelectItem value="xlsx">Excel</SelectItem>
                        <SelectItem value="json">JSON</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>上传文件</Label>
                  <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center">
                    <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground mb-2">点击或拖拽文件到此处</p>
                    <p className="text-xs text-muted-foreground">支持 CSV, Excel, JSON 格式，最大 10MB</p>
                    <input type="file" className="hidden" accept=".csv,.xlsx,.json" />
                  </div>
                </div>

                {importProgress > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>导入进度</span>
                      <span>{importProgress}%</span>
                    </div>
                    <Progress value={importProgress} />
                  </div>
                )}

                <div className="flex items-center space-x-2">
                  <Switch id="validate-data" />
                  <Label htmlFor="validate-data">导入前验证数据格式</Label>
                </div>

                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowImportDialog(false)}>
                    取消
                  </Button>
                  <Button onClick={() => handleImport(new File([], "test.csv"))}>开始导入</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={showExportDialog} onOpenChange={setShowExportDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-2" />
                导出数据
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>导出数据</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>导出内容</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择导出内容" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部数据</SelectItem>
                        <SelectItem value="students">学生信息</SelectItem>
                        <SelectItem value="scores">成绩数据</SelectItem>
                        <SelectItem value="assignments">作业数据</SelectItem>
                        <SelectItem value="analytics">分析报告</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>导出格式</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择格式" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="csv">CSV</SelectItem>
                        <SelectItem value="xlsx">Excel</SelectItem>
                        <SelectItem value="pdf">PDF报告</SelectItem>
                        <SelectItem value="json">JSON</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>时间范围</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input type="date" placeholder="开始日期" />
                    <Input type="date" placeholder="结束日期" />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>筛选条件</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择班级" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部班级</SelectItem>
                        <SelectItem value="class1">高三(1)班</SelectItem>
                        <SelectItem value="class2">高三(2)班</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择科目" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部科目</SelectItem>
                        <SelectItem value="math">数学</SelectItem>
                        <SelectItem value="english">英语</SelectItem>
                        <SelectItem value="physics">物理</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {exportProgress > 0 && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>导出进度</span>
                      <span>{exportProgress}%</span>
                    </div>
                    <Progress value={exportProgress} />
                  </div>
                )}

                <div className="flex items-center space-x-2">
                  <Switch id="include-charts" />
                  <Label htmlFor="include-charts">包含图表和分析</Label>
                </div>

                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowExportDialog(false)}>
                    取消
                  </Button>
                  <Button onClick={() => handleExport("xlsx", "all")}>开始导出</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={showChartDialog} onOpenChange={setShowChartDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                创建图表
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>创建自定义图表</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>图表名称</Label>
                    <Input placeholder="输入图表名称" />
                  </div>
                  <div className="space-y-2">
                    <Label>图表类型</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择图表类型" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="line">折线图</SelectItem>
                        <SelectItem value="bar">柱状图</SelectItem>
                        <SelectItem value="area">面积图</SelectItem>
                        <SelectItem value="pie">饼图</SelectItem>
                        <SelectItem value="radar">雷达图</SelectItem>
                        <SelectItem value="scatter">散点图</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>数据源</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择数据源" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="student_scores">学生成绩</SelectItem>
                        <SelectItem value="assignment_data">作业数据</SelectItem>
                        <SelectItem value="class_performance">班级表现</SelectItem>
                        <SelectItem value="knowledge_points">知识点掌握</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>时间范围</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择时间范围" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="week">最近一周</SelectItem>
                        <SelectItem value="month">最近一月</SelectItem>
                        <SelectItem value="semester">本学期</SelectItem>
                        <SelectItem value="year">本学年</SelectItem>
                        <SelectItem value="custom">自定义</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>X轴字段</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择X轴字段" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="date">日期</SelectItem>
                        <SelectItem value="student">学生</SelectItem>
                        <SelectItem value="subject">科目</SelectItem>
                        <SelectItem value="class">班级</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Y轴字段</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择Y轴字段" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="score">分数</SelectItem>
                        <SelectItem value="average">平均分</SelectItem>
                        <SelectItem value="count">数量</SelectItem>
                        <SelectItem value="percentage">百分比</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>筛选条件</Label>
                  <div className="grid grid-cols-3 gap-2">
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="班级" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部班级</SelectItem>
                        <SelectItem value="class1">高三(1)班</SelectItem>
                        <SelectItem value="class2">高三(2)班</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="科目" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部科目</SelectItem>
                        <SelectItem value="math">数学</SelectItem>
                        <SelectItem value="english">英语</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="成绩范围" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部</SelectItem>
                        <SelectItem value="excellent">优秀(90+)</SelectItem>
                        <SelectItem value="good">良好(80-89)</SelectItem>
                        <SelectItem value="average">一般(60-79)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>图表预览</Label>
                  <Card>
                    <CardContent className="p-4">
                      <div className="h-64 flex items-center justify-center border-2 border-dashed border-muted-foreground/25 rounded">
                        <div className="text-center">
                          <BarChart3 className="w-12 h-12 mx-auto mb-2 text-muted-foreground" />
                          <p className="text-sm text-muted-foreground">图表预览将在这里显示</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch id="public-chart" />
                  <Label htmlFor="public-chart">设为公开图表</Label>
                </div>

                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowChartDialog(false)}>
                    取消
                  </Button>
                  <Button variant="outline">预览图表</Button>
                  <Button>创建图表</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <FileSpreadsheet className="w-6 h-6 mx-auto mb-2 text-blue-500" />
            <p className="text-2xl font-bold">1,234</p>
            <p className="text-xs text-muted-foreground">数据记录</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <BarChart3 className="w-6 h-6 mx-auto mb-2 text-green-500" />
            <p className="text-2xl font-bold">{mockCustomCharts.length}</p>
            <p className="text-xs text-muted-foreground">自定义图表</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Upload className="w-6 h-6 mx-auto mb-2 text-purple-500" />
            <p className="text-2xl font-bold">15</p>
            <p className="text-xs text-muted-foreground">本月导入</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Download className="w-6 h-6 mx-auto mb-2 text-orange-500" />
            <p className="text-2xl font-bold">8</p>
            <p className="text-xs text-muted-foreground">本月导出</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="charts" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="charts">自定义图表</TabsTrigger>
          <TabsTrigger value="templates">图表模板</TabsTrigger>
          <TabsTrigger value="history">操作历史</TabsTrigger>
        </TabsList>

        <TabsContent value="charts" className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder="搜索图表..." className="pl-10 w-64" />
              </div>
              <Select>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="line">折线图</SelectItem>
                  <SelectItem value="bar">柱状图</SelectItem>
                  <SelectItem value="pie">饼图</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-1" />
              刷新数据
            </Button>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {mockCustomCharts.map((chart) => (
              <Card key={chart.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="text-lg">{chart.name}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant={chart.isPublic ? "default" : "secondary"} className="text-xs">
                        {chart.isPublic ? "公开" : "私有"}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {chart.type === "line"
                          ? "折线图"
                          : chart.type === "bar"
                            ? "柱状图"
                            : chart.type === "pie"
                              ? "饼图"
                              : "雷达图"}
                      </Badge>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="mb-4">{renderChart(chart)}</div>
                  <div className="flex items-center justify-between text-sm text-muted-foreground mb-3">
                    <span>创建时间: {chart.createdAt}</span>
                    <span>数据源: {chart.dataSource}</span>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="flex-1 bg-transparent">
                      <Eye className="w-4 h-4 mr-1" />
                      查看
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1 bg-transparent">
                      <Edit className="w-4 h-4 mr-1" />
                      编辑
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1 bg-transparent">
                      <Share2 className="w-4 h-4 mr-1" />
                      分享
                    </Button>
                    <Button variant="outline" size="sm">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="templates" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                name: "班级成绩对比",
                description: "对比不同班级的平均成绩",
                type: "bar",
                preview: "预览柱状图",
              },
              {
                name: "学生进步趋势",
                description: "展示学生成绩变化趋势",
                type: "line",
                preview: "预览折线图",
              },
              {
                name: "科目分布分析",
                description: "分析各科目作业分布情况",
                type: "pie",
                preview: "预览饼图",
              },
              {
                name: "知识点掌握雷达",
                description: "多维度展示知识点掌握情况",
                type: "radar",
                preview: "预览雷达图",
              },
              {
                name: "成绩分布散点",
                description: "分析成绩与时间的关系",
                type: "scatter",
                preview: "预览散点图",
              },
              {
                name: "学习时长统计",
                description: "统计学生学习时长分布",
                type: "area",
                preview: "预览面积图",
              },
            ].map((template, index) => (
              <Card key={index} className="hover:shadow-md transition-shadow cursor-pointer">
                <CardContent className="p-6">
                  <div className="text-center mb-4">
                    <div className="w-16 h-16 bg-primary/10 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <BarChart3 className="w-8 h-8 text-primary" />
                    </div>
                    <h3 className="font-semibold mb-2">{template.name}</h3>
                    <p className="text-sm text-muted-foreground mb-3">{template.description}</p>
                    <Badge variant="outline" className="text-xs">
                      {template.type === "bar"
                        ? "柱状图"
                        : template.type === "line"
                          ? "折线图"
                          : template.type === "pie"
                            ? "饼图"
                            : template.type === "radar"
                              ? "雷达图"
                              : template.type === "scatter"
                                ? "散点图"
                                : "面积图"}
                    </Badge>
                  </div>
                  <Button className="w-full" size="sm">
                    使用模板
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>操作历史</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-3">
                  {[
                    {
                      action: "导入数据",
                      details: "导入学生成绩数据 (150条记录)",
                      time: "2024-01-20 14:30",
                      status: "成功",
                      type: "import",
                    },
                    {
                      action: "创建图表",
                      details: "创建班级成绩趋势分析图表",
                      time: "2024-01-20 10:15",
                      status: "成功",
                      type: "chart",
                    },
                    {
                      action: "导出报告",
                      details: "导出月度分析报告 (PDF格式)",
                      time: "2024-01-19 16:45",
                      status: "成功",
                      type: "export",
                    },
                    {
                      action: "导入数据",
                      details: "导入作业数据 (失败：格式错误)",
                      time: "2024-01-19 09:20",
                      status: "失败",
                      type: "import",
                    },
                    {
                      action: "分享图表",
                      details: "分享学科分布统计图表给家长",
                      time: "2024-01-18 15:30",
                      status: "成功",
                      type: "share",
                    },
                  ].map((item, index) => (
                    <div key={index} className="flex items-center gap-3 p-3 border border-border rounded-lg">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          item.type === "import"
                            ? "bg-blue-100 text-blue-600"
                            : item.type === "export"
                              ? "bg-green-100 text-green-600"
                              : item.type === "chart"
                                ? "bg-purple-100 text-purple-600"
                                : "bg-orange-100 text-orange-600"
                        }`}
                      >
                        {item.type === "import" ? (
                          <Upload className="w-4 h-4" />
                        ) : item.type === "export" ? (
                          <Download className="w-4 h-4" />
                        ) : item.type === "chart" ? (
                          <BarChart3 className="w-4 h-4" />
                        ) : (
                          <Share2 className="w-4 h-4" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium text-sm">{item.action}</p>
                          <Badge variant={item.status === "成功" ? "default" : "destructive"} className="text-xs">
                            {item.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{item.details}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">{item.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
