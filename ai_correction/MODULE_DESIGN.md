# 理科作业批改网站模块设计

## 模块划分

### 1. 核心模块
- `App`: 应用程序主模块，负责协调各个功能模块
- `FileUploader`: 文件上传处理模块
- `AIService`: AI批改服务模块（模拟）
- `ResultViewer`: 结果展示模块
- `ExportService`: 结果导出模块

### 2. 数据结构

#### 2.1 批改任务 (MarkingTask)
```typescript
interface MarkingTask {
  id: string;                // 任务唯一ID
  questionFile: FileInfo;    // 题目文件
  schemeFile: FileInfo;      // 批改标准文件
  answerFiles: FileInfo[];   // 学生作答文件（可多个）
  status: "pending" | "processing" | "completed" | "failed"; // 任务状态
  result?: MarkingResult;    // 批改结果
  createdAt: number;         // 创建时间戳
}
```

#### 2.2 文件信息 (FileInfo)
```typescript
interface FileInfo {
  id: string;          // 文件唯一ID
  name: string;        // 文件名
  type: string;        // 文件类型
  size: number;        // 文件大小（字节）
  lastModified: number;// 最后修改时间
  content?: string;    // 文件内容（可选，用于预览）
}
```

#### 2.3 批改结果 (MarkingResult)
```typescript
interface MarkingResult {
  taskId: string;            // 对应任务ID
  studentResults: StudentResult[]; // 每个学生的批改结果
  overallStatistics?: {     // 整体统计（可选，多学生时使用）
    averageScore: number;    // 平均分
    highestScore: number;    // 最高分
    lowestScore: number;     // 最低分
    passRate: number;        // 通过率
  };
}
```

#### 2.4 学生结果 (StudentResult)
```typescript
interface StudentResult {
  studentId: string;         // 学生ID（可从文件名解析）
  studentName: string;       // 学生名称
  totalScore: number;        // 总分
  maxScore: number;          // 满分
  percentage: number;        // 得分百分比
  feedback: string;          // 总体评价
  detailedMarking: MarkingDetail[]; // 详细评分点
}
```

#### 2.5 详细评分 (MarkingDetail)
```typescript
interface MarkingDetail {
  pointId: string;           // 评分点ID
  description: string;       // 评分点描述
  score: number;             // 实际得分
  maxScore: number;          // 该点满分
  reason: string;            // 得分/扣分原因
  suggestion?: string;       // 改进建议（可选）
}
```

### 3. 接口设计

#### 3.1 FileUploader 模块
```typescript
interface FileUploader {
  uploadQuestionFile(file: File): Promise<FileInfo>;
  uploadSchemeFile(file: File): Promise<FileInfo>;
  uploadAnswerFiles(files: File[]): Promise<FileInfo[]>;
  validateFile(file: File, type: string): boolean;
  getFilePreview(fileInfo: FileInfo): Promise<string>;
}
```

#### 3.2 AIService 模块
```typescript
interface AIService {
  createMarkingTask(question: FileInfo, scheme: FileInfo, answers: FileInfo[]): Promise<MarkingTask>;
  processTask(task: MarkingTask): Promise<MarkingResult>;
  getTaskStatus(taskId: string): Promise<string>;
}
```

#### 3.3 ResultViewer 模块
```typescript
interface ResultViewer {
  displayResults(result: MarkingResult): void;
  showStudentResult(studentResult: StudentResult): void;
  renderDetailedMarking(details: MarkingDetail[]): void;
  toggleViewMode(mode: "summary" | "detailed"): void;
}
```

#### 3.4 ExportService 模块
```typescript
interface ExportService {
  exportToPDF(result: MarkingResult): Promise<Blob>;
  exportToExcel(result: MarkingResult): Promise<Blob>;
  downloadFile(blob: Blob, fileName: string): void;
  getBatchReport(results: MarkingResult[]): Promise<Blob>;
}
```

## 流程设计

1. 用户上传题目文件、批改标准文件和学生作答文件
2. 系统验证文件并创建批改任务
3. 系统调用AI服务进行批改
4. 系统展示批改结果
5. 用户可查看详细批改结果并下载报告

所有异步操作均返回Promise，并通过async/await处理。文件上传、结果渲染等操作采用原生JavaScript实现。