'use client';

import { useState, useEffect } from 'react';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '@/components/ui/dialog';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  Download, 
  Eye, 
  Trash2, 
  Search, 
  Filter, 
  FileText, 
  Calendar,
  BarChart3,
  TrendingUp,
  Archive,
  MoreVertical,
  RefreshCw
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { 
  apiService, 
  UserRecord, 
  UserStatistics, 
  downloadFile, 
  formatTimestamp, 
  getFileTypeIcon 
} from '@/lib/api';

interface PaginationInfo {
  records: UserRecord[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export default function HistoryPage() {
  const [records, setRecords] = useState<UserRecord[]>([]);
  const [statistics, setStatistics] = useState<UserStatistics | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<UserRecord | null>(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [filterLanguage, setFilterLanguage] = useState<string>('all');
  const [filterStrictness, setFilterStrictness] = useState<string>('all');
  const { toast } = useToast();

  // 加载历史记录
  const loadRecords = async (page: number = 0) => {
    try {
      setLoading(true);
      const response = await apiService.getUserRecords(page, 9);
      
      if (response.success && response.data) {
        setRecords(response.data.records);
        setCurrentPage(response.data.page);
        setTotalPages(response.data.total_pages);
      } else {
        toast({
          title: "加载失败",
          description: response.error || "无法加载历史记录",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "加载错误",
        description: "网络连接失败",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // 加载统计信息
  const loadStatistics = async () => {
    try {
      const response = await apiService.getUserStatistics();
      
      if (response.success && response.data) {
        setStatistics(response.data);
      }
    } catch (error) {
      console.error('Failed to load statistics:', error);
    }
  };

  useEffect(() => {
    loadRecords();
    loadStatistics();
  }, []);

  // 过滤记录
  const filteredRecords = records.filter(record => {
    const matchesSearch = record.content?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         record.timestamp?.includes(searchTerm);
    const matchesLanguage = filterLanguage === 'all' || record.settings?.language === filterLanguage;
    const matchesStrictness = filterStrictness === 'all' || record.settings?.strictness_level === filterStrictness;
    
    return matchesSearch && matchesLanguage && matchesStrictness;
  });

  // 导出记录
  const handleExport = async (recordIndex: number, format: string) => {
    try {
      const blob = await apiService.exportRecord(recordIndex, format);
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
      const filename = `correction_result_${timestamp}.${format}`;
      downloadFile(blob, filename);
      
      toast({
        title: "导出成功",
        description: `已导出为 ${format.toUpperCase()} 格式`,
      });
    } catch (error) {
      toast({
        title: "导出失败",
        description: error instanceof Error ? error.message : "导出过程中发生错误",
        variant: "destructive",
      });
    }
  };

  // 删除记录
  const handleDelete = async (recordIndex: number) => {
    try {
      const response = await apiService.deleteRecord(recordIndex);
      
      if (response.success) {
        toast({
          title: "删除成功",
          description: "记录已删除",
        });
        loadRecords(currentPage);
        loadStatistics();
      } else {
        toast({
          title: "删除失败",
          description: response.error || "删除过程中发生错误",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "删除错误",
        description: "网络连接失败",
        variant: "destructive",
      });
    }
  };

  // 清空所有记录
  const handleClearAll = async () => {
    try {
      const response = await apiService.clearAllRecords();
      
      if (response.success) {
        toast({
          title: "清空成功",
          description: "所有记录已清空",
        });
        loadRecords(0);
        loadStatistics();
      } else {
        toast({
          title: "清空失败",
          description: response.error || "清空过程中发生错误",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "清空错误",
        description: "网络连接失败",
        variant: "destructive",
      });
    }
  };

  // 查看详情
  const handleViewDetail = async (recordIndex: number) => {
    try {
      const response = await apiService.getRecordDetail(recordIndex);
      
      if (response.success && response.data) {
        setSelectedRecord(response.data);
        setShowDetailDialog(true);
      } else {
        toast({
          title: "加载失败",
          description: "无法加载记录详情",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "加载错误",
        description: "网络连接失败",
        variant: "destructive",
      });
    }
  };

  // 获取语言显示名称
  const getLanguageName = (lang: string) => {
    return lang === 'zh' ? '中文' : '英文';
  };

  // 获取严格程度颜色
  const getStrictnessColor = (level: string) => {
    switch (level) {
      case '宽松': return 'bg-green-100 text-green-800';
      case '中等': return 'bg-yellow-100 text-yellow-800';
      case '严格': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">批改历史</h1>
        <p className="text-gray-600 mt-2">查看和管理您的所有批改记录</p>
      </div>

      <Tabs defaultValue="records" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="records" className="flex items-center gap-2">
            <Archive className="w-4 h-4" />
            历史记录
          </TabsTrigger>
          <TabsTrigger value="statistics" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            统计分析
          </TabsTrigger>
        </TabsList>

        <TabsContent value="records" className="space-y-6">
          {/* 搜索和过滤器 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-5 h-5" />
                搜索和过滤
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="search">搜索内容</Label>
                  <Input
                    id="search"
                    type="text"
                    placeholder="搜索批改内容或日期..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="language">语言</Label>
                  <select
                    id="language"
                    className="w-full p-2 border rounded-md"
                    value={filterLanguage}
                    onChange={(e) => setFilterLanguage(e.target.value)}
                  >
                    <option value="all">所有语言</option>
                    <option value="zh">中文</option>
                    <option value="en">英文</option>
                  </select>
                </div>
                <div>
                  <Label htmlFor="strictness">严格程度</Label>
                  <select
                    id="strictness"
                    className="w-full p-2 border rounded-md"
                    value={filterStrictness}
                    onChange={(e) => setFilterStrictness(e.target.value)}
                  >
                    <option value="all">所有程度</option>
                    <option value="宽松">宽松</option>
                    <option value="中等">中等</option>
                    <option value="严格">严格</option>
                  </select>
                </div>
              </div>
              
              <div className="flex justify-between items-center">
                <Button
                  variant="outline"
                  onClick={() => loadRecords(currentPage)}
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  刷新
                </Button>
                
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive" className="flex items-center gap-2">
                      <Trash2 className="w-4 h-4" />
                      清空所有记录
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>确认清空所有记录？</AlertDialogTitle>
                      <AlertDialogDescription>
                        此操作将永久删除所有批改记录，无法恢复。请确认您要继续。
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>取消</AlertDialogCancel>
                      <AlertDialogAction onClick={handleClearAll}>
                        确认清空
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </CardContent>
          </Card>

          {/* 记录列表 */}
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">加载中...</p>
            </div>
          ) : filteredRecords.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <Archive className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">暂无记录</h3>
                <p className="text-gray-600">还没有任何批改记录，开始您的第一次批改吧！</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
              {filteredRecords.map((record, index) => (
                <Card key={index} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          {formatTimestamp(record.timestamp)}
                        </CardTitle>
                        <CardDescription className="mt-2 flex flex-wrap gap-1">
                          <Badge variant="outline">
                            {getLanguageName(record.settings.language)}
                          </Badge>
                          <Badge className={getStrictnessColor(record.settings.strictness_level)}>
                            {record.settings.strictness_level}
                          </Badge>
                          {record.settings.groups_processed && (
                            <Badge variant="secondary">
                              {record.settings.groups_processed}组
                            </Badge>
                          )}
                        </CardDescription>
                      </div>
                      
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleViewDetail(index)}>
                            <Eye className="w-4 h-4 mr-2" />
                            查看详情
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleExport(index, 'pdf')}>
                            <Download className="w-4 h-4 mr-2" />
                            导出PDF
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleExport(index, 'docx')}>
                            <Download className="w-4 h-4 mr-2" />
                            导出Word
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleExport(index, 'txt')}>
                            <Download className="w-4 h-4 mr-2" />
                            导出文本
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDelete(index)}
                            className="text-red-600"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            删除
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardHeader>
                  
                  <CardContent>
                    <div className="space-y-3">
                      {/* 文件信息 */}
                      <div>
                        <h4 className="font-medium text-sm mb-2">上传文件:</h4>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(record.files).map(([key, file]: [string, any]) => (
                            <span key={key} className="text-xs bg-gray-100 px-2 py-1 rounded">
                              {getFileTypeIcon(file.original_name || '')} {file.original_name}
                            </span>
                          ))}
                        </div>
                      </div>
                      
                      {/* 内容预览 */}
                      <div>
                        <h4 className="font-medium text-sm mb-2">批改预览:</h4>
                        <p className="text-sm text-gray-600 line-clamp-3">
                          {record.content.substring(0, 150)}...
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-6">
              <Button
                variant="outline"
                disabled={currentPage === 0}
                onClick={() => loadRecords(currentPage - 1)}
              >
                上一页
              </Button>
              
              {Array.from({ length: totalPages }, (_, i) => (
                <Button
                  key={i}
                  variant={i === currentPage ? "default" : "outline"}
                  onClick={() => loadRecords(i)}
                >
                  {i + 1}
                </Button>
              ))}
              
              <Button
                variant="outline"
                disabled={currentPage === totalPages - 1}
                onClick={() => loadRecords(currentPage + 1)}
              >
                下一页
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="statistics" className="space-y-6">
          {statistics && (
            <>
              {/* 总体统计 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">总批改次数</CardTitle>
                    <FileText className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{statistics.total_corrections}</div>
                    <p className="text-xs text-muted-foreground">
                      累计批改记录
                    </p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">最近7天</CardTitle>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {statistics.recent_activity.reduce((sum, day) => sum + day.count, 0)}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      近期活动次数
                    </p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">常用语言</CardTitle>
                    <BarChart3 className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {statistics.language_stats.zh > statistics.language_stats.en ? '中文' : '英文'}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      使用最多的语言
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* 详细统计 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>语言使用统计</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span>中文</span>
                        <span>{statistics.language_stats.zh}次</span>
                      </div>
                      <Progress 
                        value={(statistics.language_stats.zh / statistics.total_corrections) * 100} 
                        className="w-full"
                      />
                    </div>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span>英文</span>
                        <span>{statistics.language_stats.en}次</span>
                      </div>
                      <Progress 
                        value={(statistics.language_stats.en / statistics.total_corrections) * 100} 
                        className="w-full"
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>严格程度统计</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {Object.entries(statistics.strictness_stats).map(([level, count]) => (
                      <div key={level} className="space-y-3">
                        <div className="flex justify-between">
                          <span>{level}</span>
                          <span>{count}次</span>
                        </div>
                        <Progress 
                          value={(count / statistics.total_corrections) * 100} 
                          className="w-full"
                        />
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>

              {/* 最近活动 */}
              <Card>
                <CardHeader>
                  <CardTitle>最近7天活动</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-7 gap-2">
                    {statistics.recent_activity.map((day) => (
                      <div key={day.date} className="text-center">
                        <div className="text-xs text-gray-500 mb-1">
                          {new Date(day.date).getDate()}
                        </div>
                        <div className="bg-blue-100 rounded p-2 text-sm font-medium">
                          {day.count}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>

      {/* 详情对话框 */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>批改详情</DialogTitle>
            <DialogDescription>
              {selectedRecord && formatTimestamp(selectedRecord.timestamp)}
            </DialogDescription>
          </DialogHeader>
          
          {selectedRecord && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">批改设置</h4>
                  <div className="space-y-1 text-sm">
                    <p>语言: {getLanguageName(selectedRecord.settings?.language || 'zh')}</p>
                    <p>严格程度: {selectedRecord.settings?.strictness_level || '中等'}</p>
                    {selectedRecord.settings?.groups_processed && (
                      <p>处理组数: {selectedRecord.settings.groups_processed}</p>
                    )}
                  </div>
                </div>
                
                <div>
                  <h4 className="font-medium mb-2">上传文件</h4>
                  <div className="space-y-1 text-sm">
                    {(() => {
                      if (!selectedRecord.files) {
                        return <p className="text-gray-500">无文件信息</p>;
                      }
                      
                      if (Array.isArray(selectedRecord.files)) {
                        return selectedRecord.files.map((file: any, index: number) => (
                          <p key={index}>
                            {getFileTypeIcon(file?.original_name || file?.filename || '')} {file?.original_name || file?.filename || '未知文件'}
                          </p>
                        ));
                      }
                      
                      if (typeof selectedRecord.files === 'object') {
                        return Object.entries(selectedRecord.files).map(([key, file]: [string, any]) => (
                          <p key={key}>
                            {getFileTypeIcon(file?.original_name || file?.filename || '')} {file?.original_name || file?.filename || '未知文件'}
                          </p>
                        ));
                      }
                      
                      return <p className="text-gray-500">无文件信息</p>;
                    })()}
                  </div>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium mb-2">批改内容</h4>
                <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm">
                    {selectedRecord.content}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
} 