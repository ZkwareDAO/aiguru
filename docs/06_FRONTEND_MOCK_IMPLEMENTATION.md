# 前端Mock实现文档

## 📌 文档概述

本文档详细描述前端Mock数据结构、Mock API实现、开发工作流和测试策略。

---

## 1. Mock数据结构设计

### 1.1 核心数据模型

```typescript
// ============ 用户相关 ============
interface User {
  id: string;
  username: string;
  email: string;
  role: 'teacher' | 'student' | 'admin';
  avatar?: string;
  fullName: string;
  createdAt: string;
}

// ============ 作业相关 ============
interface Assignment {
  id: string;
  title: string;
  description: string;
  instructions: string;
  dueDate: string;
  maxScore: number;
  classId: string;
  teacherId: string;
  gradingStandard: GradingStandard;
  status: 'draft' | 'published' | 'closed';
  createdAt: string;
  updatedAt: string;
  
  // 统计信息
  stats: {
    totalStudents: number;
    submittedCount: number;
    gradedCount: number;
    averageScore: number;
  };
}

interface GradingStandard {
  criteria: string;
  answer: string;
  rubric: RubricItem[];
  strictness: 'loose' | 'standard' | 'strict';
}

interface RubricItem {
  id: string;
  description: string;
  points: number;
  category: string;
}

// ============ 提交相关 ============
interface Submission {
  id: string;
  assignmentId: string;
  studentId: string;
  files: FileInfo[];
  submittedAt: string;
  status: 'pending' | 'grading' | 'graded' | 'reviewed';
  gradingResult?: GradingResult;
}

interface FileInfo {
  id: string;
  name: string;
  url: string;
  type: string;
  size: number;
  uploadedAt: string;
}

// ============ 批改结果 ============
interface GradingResult {
  id: string;
  submissionId: string;
  score: number;
  maxScore: number;
  percentage: number;
  confidence: number;
  
  // 错误标注
  errors: ErrorAnnotation[];
  annotations: CoordinateAnnotation[];
  
  // 反馈
  overallComment: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  knowledgePoints: KnowledgePoint[];
  
  // 元数据
  gradedAt: string;
  gradedBy: 'ai' | 'teacher';
  reviewStatus: 'pending' | 'approved' | 'adjusted' | 'rejected';
  processingTime: number; // ms
}

interface ErrorAnnotation {
  id: string;
  type: 'concept' | 'calculation' | 'expression' | 'missing' | 'other';
  severity: 'high' | 'medium' | 'low';
  location: string;
  description: string;
  correctAnswer: string;
  deduction: number;
  
  // 可视化相关
  coordinates?: {x: number, y: number, width: number, height: number};
  croppedImageUrl?: string;
  
  // 学习相关
  knowledgePoints: string[];
  suggestion: string;
}

interface CoordinateAnnotation {
  id: string;
  errorId: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  label: string;
}

interface KnowledgePoint {
  id: string;
  name: string;
  category: string;
  masteryLevel: number; // 0-100
}

// ============ 批改任务 ============
interface GradingTask {
  id: string;
  type: 'single' | 'batch';
  assignmentId: string;
  submissionIds: string[];
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number; // 0-100
  
  // 统计
  totalCount: number;
  completedCount: number;
  failedCount: number;
  
  // 时间
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  estimatedTimeRemaining?: number; // seconds
  
  // 配置
  config: {
    strictness: 'loose' | 'standard' | 'strict';
    enableReview: boolean;
    enableAnalytics: boolean;
  };
}

// ============ 通知 ============
interface Notification {
  id: string;
  userId: string;
  type: 'grading_completed' | 'assignment_published' | 'submission_received' | 'review_required';
  title: string;
  message: string;
  read: boolean;
  actionUrl?: string;
  createdAt: string;
}
```

---

## 2. Mock数据生成器

### 2.1 数据工厂

```typescript
// mock/factories.ts
import { faker } from '@faker-js/faker';

export class MockDataFactory {
  // 生成用户
  static createUser(overrides?: Partial<User>): User {
    return {
      id: faker.string.uuid(),
      username: faker.internet.userName(),
      email: faker.internet.email(),
      role: faker.helpers.arrayElement(['teacher', 'student']),
      avatar: faker.image.avatar(),
      fullName: faker.person.fullName(),
      createdAt: faker.date.past().toISOString(),
      ...overrides
    };
  }
  
  // 生成作业
  static createAssignment(overrides?: Partial<Assignment>): Assignment {
    const totalStudents = faker.number.int({ min: 30, max: 50 });
    const submittedCount = faker.number.int({ min: 0, max: totalStudents });
    const gradedCount = faker.number.int({ min: 0, max: submittedCount });
    
    return {
      id: faker.string.uuid(),
      title: faker.lorem.sentence(),
      description: faker.lorem.paragraph(),
      instructions: faker.lorem.paragraphs(2),
      dueDate: faker.date.future().toISOString(),
      maxScore: 100,
      classId: faker.string.uuid(),
      teacherId: faker.string.uuid(),
      gradingStandard: this.createGradingStandard(),
      status: faker.helpers.arrayElement(['draft', 'published', 'closed']),
      createdAt: faker.date.past().toISOString(),
      updatedAt: faker.date.recent().toISOString(),
      stats: {
        totalStudents,
        submittedCount,
        gradedCount,
        averageScore: faker.number.float({ min: 60, max: 95, precision: 0.1 })
      },
      ...overrides
    };
  }
  
  // 生成批改标准
  static createGradingStandard(): GradingStandard {
    return {
      criteria: faker.lorem.paragraph(),
      answer: faker.lorem.paragraphs(3),
      rubric: Array.from({ length: 5 }, () => ({
        id: faker.string.uuid(),
        description: faker.lorem.sentence(),
        points: faker.number.int({ min: 5, max: 20 }),
        category: faker.helpers.arrayElement(['知识点', '计算', '表述', '完整性'])
      })),
      strictness: faker.helpers.arrayElement(['loose', 'standard', 'strict'])
    };
  }
  
  // 生成提交
  static createSubmission(overrides?: Partial<Submission>): Submission {
    return {
      id: faker.string.uuid(),
      assignmentId: faker.string.uuid(),
      studentId: faker.string.uuid(),
      files: Array.from({ length: faker.number.int({ min: 1, max: 3 }) }, () => 
        this.createFileInfo()
      ),
      submittedAt: faker.date.recent().toISOString(),
      status: faker.helpers.arrayElement(['pending', 'grading', 'graded', 'reviewed']),
      ...overrides
    };
  }
  
  // 生成文件信息
  static createFileInfo(): FileInfo {
    return {
      id: faker.string.uuid(),
      name: faker.system.fileName(),
      url: faker.image.url(),
      type: faker.helpers.arrayElement(['image/jpeg', 'image/png', 'application/pdf']),
      size: faker.number.int({ min: 100000, max: 5000000 }),
      uploadedAt: faker.date.recent().toISOString()
    };
  }
  
  // 生成批改结果
  static createGradingResult(overrides?: Partial<GradingResult>): GradingResult {
    const maxScore = 100;
    const score = faker.number.float({ min: 60, max: 100, precision: 0.5 });
    const errorCount = faker.number.int({ min: 0, max: 5 });
    
    return {
      id: faker.string.uuid(),
      submissionId: faker.string.uuid(),
      score,
      maxScore,
      percentage: (score / maxScore) * 100,
      confidence: faker.number.float({ min: 0.7, max: 1.0, precision: 0.01 }),
      errors: Array.from({ length: errorCount }, () => this.createErrorAnnotation()),
      annotations: Array.from({ length: errorCount }, () => this.createCoordinateAnnotation()),
      overallComment: faker.lorem.paragraph(),
      strengths: Array.from({ length: 2 }, () => faker.lorem.sentence()),
      weaknesses: Array.from({ length: 2 }, () => faker.lorem.sentence()),
      suggestions: Array.from({ length: 3 }, () => faker.lorem.sentence()),
      knowledgePoints: Array.from({ length: 3 }, () => this.createKnowledgePoint()),
      gradedAt: faker.date.recent().toISOString(),
      gradedBy: faker.helpers.arrayElement(['ai', 'teacher']),
      reviewStatus: faker.helpers.arrayElement(['pending', 'approved', 'adjusted']),
      processingTime: faker.number.int({ min: 2000, max: 30000 }),
      ...overrides
    };
  }
  
  // 生成错误标注
  static createErrorAnnotation(): ErrorAnnotation {
    return {
      id: faker.string.uuid(),
      type: faker.helpers.arrayElement(['concept', 'calculation', 'expression', 'missing']),
      severity: faker.helpers.arrayElement(['high', 'medium', 'low']),
      location: `第${faker.number.int({ min: 1, max: 5 })}题`,
      description: faker.lorem.sentence(),
      correctAnswer: faker.lorem.sentence(),
      deduction: faker.number.int({ min: 2, max: 10 }),
      coordinates: {
        x: faker.number.int({ min: 50, max: 500 }),
        y: faker.number.int({ min: 50, max: 500 }),
        width: faker.number.int({ min: 100, max: 300 }),
        height: faker.number.int({ min: 50, max: 150 })
      },
      croppedImageUrl: faker.image.url(),
      knowledgePoints: Array.from({ length: 2 }, () => faker.lorem.word()),
      suggestion: faker.lorem.sentence()
    };
  }
  
  // 生成坐标标注
  static createCoordinateAnnotation(): CoordinateAnnotation {
    return {
      id: faker.string.uuid(),
      errorId: faker.string.uuid(),
      x: faker.number.int({ min: 50, max: 500 }),
      y: faker.number.int({ min: 50, max: 500 }),
      width: faker.number.int({ min: 100, max: 300 }),
      height: faker.number.int({ min: 50, max: 150 }),
      color: faker.helpers.arrayElement(['#FF6B6B', '#FFA500', '#FFD700']),
      label: `错误${faker.number.int({ min: 1, max: 10 })}`
    };
  }
  
  // 生成知识点
  static createKnowledgePoint(): KnowledgePoint {
    return {
      id: faker.string.uuid(),
      name: faker.lorem.words(3),
      category: faker.helpers.arrayElement(['数学', '物理', '化学', '语文']),
      masteryLevel: faker.number.int({ min: 0, max: 100 })
    };
  }
  
  // 生成批改任务
  static createGradingTask(overrides?: Partial<GradingTask>): GradingTask {
    const totalCount = faker.number.int({ min: 10, max: 100 });
    const completedCount = faker.number.int({ min: 0, max: totalCount });
    const failedCount = faker.number.int({ min: 0, max: totalCount - completedCount });
    
    return {
      id: faker.string.uuid(),
      type: faker.helpers.arrayElement(['single', 'batch']),
      assignmentId: faker.string.uuid(),
      submissionIds: Array.from({ length: totalCount }, () => faker.string.uuid()),
      status: faker.helpers.arrayElement(['pending', 'processing', 'completed']),
      progress: (completedCount / totalCount) * 100,
      totalCount,
      completedCount,
      failedCount,
      createdAt: faker.date.recent().toISOString(),
      startedAt: faker.date.recent().toISOString(),
      estimatedTimeRemaining: faker.number.int({ min: 60, max: 600 }),
      config: {
        strictness: faker.helpers.arrayElement(['loose', 'standard', 'strict']),
        enableReview: faker.datatype.boolean(),
        enableAnalytics: faker.datatype.boolean()
      },
      ...overrides
    };
  }
  
  // 生成通知
  static createNotification(overrides?: Partial<Notification>): Notification {
    return {
      id: faker.string.uuid(),
      userId: faker.string.uuid(),
      type: faker.helpers.arrayElement([
        'grading_completed',
        'assignment_published',
        'submission_received',
        'review_required'
      ]),
      title: faker.lorem.sentence(),
      message: faker.lorem.paragraph(),
      read: faker.datatype.boolean(),
      actionUrl: faker.internet.url(),
      createdAt: faker.date.recent().toISOString(),
      ...overrides
    };
  }
}
```

---

## 3. Mock API实现

### 3.1 Mock服务基础

```typescript
// mock/mockService.ts
class MockAPIService {
  private delay = 500; // 模拟网络延迟
  private failureRate = 0.05; // 5%失败率
  
  // 模拟网络延迟
  private async simulateDelay() {
    const delay = this.delay + Math.random() * 500;
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  // 模拟随机失败
  private shouldFail(): boolean {
    return Math.random() < this.failureRate;
  }
  
  // 包装响应
  private async wrapResponse<T>(
    handler: () => T | Promise<T>
  ): Promise<APIResponse<T>> {
    await this.simulateDelay();
    
    if (this.shouldFail()) {
      throw new Error('Mock API Error: Random failure');
    }
    
    const data = await handler();
    
    return {
      success: true,
      data,
      message: 'Success',
      timestamp: new Date().toISOString()
    };
  }
  
  // ============ 作业相关API ============
  async getAssignments(params: {
    page?: number;
    pageSize?: number;
    status?: string;
  }): Promise<APIResponse<PaginatedResponse<Assignment>>> {
    return this.wrapResponse(() => {
      const assignments = Array.from(
        { length: params.pageSize || 10 },
        () => MockDataFactory.createAssignment()
      );
      
      return {
        items: assignments,
        total: 100,
        page: params.page || 1,
        pageSize: params.pageSize || 10,
        totalPages: 10
      };
    });
  }
  
  async getAssignment(id: string): Promise<APIResponse<Assignment>> {
    return this.wrapResponse(() => {
      return MockDataFactory.createAssignment({ id });
    });
  }
  
  async createAssignment(data: Partial<Assignment>): Promise<APIResponse<Assignment>> {
    return this.wrapResponse(() => {
      return MockDataFactory.createAssignment(data);
    });
  }
  
  // ============ 提交相关API ============
  async submitAssignment(
    assignmentId: string,
    files: File[]
  ): Promise<APIResponse<Submission>> {
    return this.wrapResponse(async () => {
      // 模拟文件上传
      const fileInfos = files.map(file => ({
        id: faker.string.uuid(),
        name: file.name,
        url: URL.createObjectURL(file),
        type: file.type,
        size: file.size,
        uploadedAt: new Date().toISOString()
      }));
      
      return MockDataFactory.createSubmission({
        assignmentId,
        files: fileInfos,
        status: 'pending'
      });
    });
  }
  
  async getSubmissions(assignmentId: string): Promise<APIResponse<Submission[]>> {
    return this.wrapResponse(() => {
      return Array.from({ length: 20 }, () =>
        MockDataFactory.createSubmission({ assignmentId })
      );
    });
  }
  
  // ============ 批改相关API ============
  async startGrading(submissionIds: string[]): Promise<APIResponse<GradingTask>> {
    return this.wrapResponse(() => {
      return MockDataFactory.createGradingTask({
        submissionIds,
        status: 'pending',
        progress: 0
      });
    });
  }
  
  async getGradingTask(taskId: string): Promise<APIResponse<GradingTask>> {
    return this.wrapResponse(() => {
      // 模拟进度增长
      const progress = Math.min(100, Math.random() * 100);
      const status = progress === 100 ? 'completed' : 'processing';
      
      return MockDataFactory.createGradingTask({
        id: taskId,
        status,
        progress
      });
    });
  }
  
  async getGradingResult(submissionId: string): Promise<APIResponse<GradingResult>> {
    return this.wrapResponse(() => {
      return MockDataFactory.createGradingResult({ submissionId });
    });
  }
  
  // ============ 通知相关API ============
  async getNotifications(userId: string): Promise<APIResponse<Notification[]>> {
    return this.wrapResponse(() => {
      return Array.from({ length: 10 }, () =>
        MockDataFactory.createNotification({ userId })
      );
    });
  }
  
  async markNotificationAsRead(notificationId: string): Promise<APIResponse<void>> {
    return this.wrapResponse(() => undefined);
  }
}

export const mockAPI = new MockAPIService();
```

### 3.2 Mock WebSocket

```typescript
// mock/mockWebSocket.ts
class MockWebSocketService {
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private connected = false;
  private simulationIntervals: NodeJS.Timeout[] = [];
  
  connect(userId: string) {
    console.log('[Mock WS] Connecting...');
    
    setTimeout(() => {
      this.connected = true;
      console.log('[Mock WS] Connected');
      
      // 开始模拟实时更新
      this.startSimulations();
    }, 1000);
  }
  
  disconnect() {
    this.connected = false;
    this.simulationIntervals.forEach(clearInterval);
    this.simulationIntervals = [];
    console.log('[Mock WS] Disconnected');
  }
  
  subscribe(event: string, handler: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);
    
    return () => {
      this.listeners.get(event)?.delete(handler);
    };
  }
  
  private emit(event: string, data: any) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }
  
  private startSimulations() {
    // 模拟批改进度更新
    const progressInterval = setInterval(() => {
      if (!this.connected) return;
      
      this.emit('grading_progress', {
        taskId: faker.string.uuid(),
        progress: Math.random() * 100,
        currentStep: faker.helpers.arrayElement(['preprocess', 'grading', 'review', 'feedback']),
        message: faker.lorem.sentence()
      });
    }, 2000);
    
    this.simulationIntervals.push(progressInterval);
    
    // 模拟批改完成通知
    const completionInterval = setInterval(() => {
      if (!this.connected) return;
      
      if (Math.random() < 0.1) { // 10%概率
        this.emit('grading_completed', {
          submissionId: faker.string.uuid(),
          score: faker.number.float({ min: 60, max: 100, precision: 0.5 }),
          message: '批改已完成,点击查看详情'
        });
      }
    }, 5000);
    
    this.simulationIntervals.push(completionInterval);
  }
}

export const mockWS = new MockWebSocketService();
```

---

## 4. 开发工作流

### 4.1 Mock开关配置

```typescript
// config/mock.config.ts
export const mockConfig = {
  enabled: process.env.NEXT_PUBLIC_MOCK_ENABLED === 'true',
  delay: parseInt(process.env.NEXT_PUBLIC_MOCK_DELAY || '500'),
  failureRate: parseFloat(process.env.NEXT_PUBLIC_MOCK_FAILURE_RATE || '0.05')
};

// API客户端
export const apiClient = mockConfig.enabled ? mockAPI : realAPI;
export const wsClient = mockConfig.enabled ? mockWS : realWS;
```

### 4.2 开发模式切换

```bash
# .env.development
NEXT_PUBLIC_MOCK_ENABLED=true
NEXT_PUBLIC_MOCK_DELAY=500
NEXT_PUBLIC_MOCK_FAILURE_RATE=0.05

# .env.production
NEXT_PUBLIC_MOCK_ENABLED=false
```

---

**文档完成!** 🎉

现在您可以查看完整的设计文档系列:
1. `01_REQUIREMENTS_DOCUMENT.md` - 需求文档
2. `02_AGENT_ARCHITECTURE_DESIGN.md` - Agent架构设计
3. `03_COLLABORATION_STRATEGY.md` - 协作策略
4. `04_SCALABILITY_RELIABILITY.md` - 可扩展性与可靠性
5. `05_USER_EXPERIENCE_DESIGN.md` - 用户体验设计
6. `06_FRONTEND_MOCK_IMPLEMENTATION.md` - 前端Mock实现

