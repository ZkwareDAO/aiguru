# 用户体验设计文档

## 📌 文档概述

本文档详细描述系统的用户体验设计、界面交互、实时反馈机制和前端架构。

---

## 1. 用户界面设计

### 1.1 教师端界面

#### 1.1.1 作业管理页面

**布局结构**:
```
┌─────────────────────────────────────────────────────────┐
│  导航栏: 首页 | 作业管理 | 批改记录 | 数据分析 | 设置    │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │  📝 作业列表                    [+ 创建作业]     │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  🔍 搜索: [_____________]  筛选: [全部▼]        │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ 📄 数学作业 - 第三章练习                 │  │   │
│  │  │ 截止: 2025-10-10  提交: 45/50  待批: 12  │  │   │
│  │  │ [查看详情] [批量批改] [导出报告]         │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ 📄 物理作业 - 力学综合                   │  │   │
│  │  │ 截止: 2025-10-12  提交: 38/50  待批: 5   │  │   │
│  │  │ [查看详情] [批量批改] [导出报告]         │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**交互流程**:
```typescript
// 创建作业流程
const createAssignmentFlow = {
  step1: {
    title: "基本信息",
    fields: ["标题", "描述", "截止日期", "班级选择"]
  },
  step2: {
    title: "批改设置",
    fields: ["评分标准", "批改指令", "严格程度", "最高分"]
  },
  step3: {
    title: "确认发布",
    preview: true,
    actions: ["保存草稿", "立即发布"]
  }
}
```

#### 1.1.2 批改管理页面

**实时批改进度**:
```tsx
interface BatchGradingProgress {
  batchId: string;
  totalCount: number;
  completedCount: number;
  failedCount: number;
  progress: number; // 0-100
  estimatedTimeRemaining: number; // seconds
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

const BatchGradingProgressView: React.FC<{batch: BatchGradingProgress}> = ({batch}) => {
  return (
    <div className="batch-progress-card">
      <div className="progress-header">
        <h3>批改进度</h3>
        <span className="status-badge">{batch.status}</span>
      </div>
      
      {/* 进度条 */}
      <div className="progress-bar-container">
        <div 
          className="progress-bar" 
          style={{width: `${batch.progress}%`}}
        />
        <span className="progress-text">{batch.progress}%</span>
      </div>
      
      {/* 统计信息 */}
      <div className="stats-grid">
        <div className="stat-item">
          <span className="stat-label">总数</span>
          <span className="stat-value">{batch.totalCount}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">已完成</span>
          <span className="stat-value success">{batch.completedCount}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">失败</span>
          <span className="stat-value error">{batch.failedCount}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">预计剩余</span>
          <span className="stat-value">{formatTime(batch.estimatedTimeRemaining)}</span>
        </div>
      </div>
      
      {/* 实时日志 */}
      <div className="live-log">
        <h4>实时日志</h4>
        <div className="log-entries">
          {/* WebSocket实时更新 */}
        </div>
      </div>
    </div>
  );
};
```

#### 1.1.3 批改结果审核页面

**批改结果卡片**:
```tsx
interface GradingResultCard {
  submissionId: string;
  studentName: string;
  score: number;
  maxScore: number;
  confidence: number;
  errors: ErrorAnnotation[];
  needsReview: boolean;
}

const GradingResultReviewView: React.FC = () => {
  const [results, setResults] = useState<GradingResultCard[]>([]);
  const [selectedResult, setSelectedResult] = useState<GradingResultCard | null>(null);
  
  return (
    <div className="review-layout">
      {/* 左侧列表 */}
      <div className="results-list">
        {results.map(result => (
          <div 
            key={result.submissionId}
            className={`result-card ${result.needsReview ? 'needs-review' : ''}`}
            onClick={() => setSelectedResult(result)}
          >
            <div className="student-info">
              <span className="student-name">{result.studentName}</span>
              {result.needsReview && <span className="review-badge">需审核</span>}
            </div>
            <div className="score-display">
              <span className="score">{result.score}</span>
              <span className="max-score">/ {result.maxScore}</span>
            </div>
            <div className="confidence-bar">
              <div 
                className="confidence-fill" 
                style={{width: `${result.confidence * 100}%`}}
              />
            </div>
          </div>
        ))}
      </div>
      
      {/* 右侧详情 */}
      <div className="result-detail">
        {selectedResult && (
          <GradingDetailView 
            result={selectedResult}
            onApprove={handleApprove}
            onAdjust={handleAdjust}
            onReject={handleReject}
          />
        )}
      </div>
    </div>
  );
};
```

### 1.2 学生端界面

#### 1.2.1 作业提交页面

**拖拽上传**:
```tsx
const AssignmentSubmissionView: React.FC<{assignmentId: string}> = ({assignmentId}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  };
  
  const handleSubmit = async () => {
    setUploading(true);
    
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('assignment_id', assignmentId);
    
    try {
      await uploadWithProgress(formData, (progress) => {
        setUploadProgress(progress);
      });
      
      toast.success('提交成功!预计10分钟内完成批改');
      
    } catch (error) {
      toast.error('提交失败,请重试');
    } finally {
      setUploading(false);
    }
  };
  
  return (
    <div className="submission-container">
      <div 
        className="dropzone"
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
      >
        <div className="dropzone-content">
          <UploadIcon />
          <p>拖拽文件到此处或点击上传</p>
          <p className="hint">支持 JPG, PNG, PDF 格式</p>
        </div>
      </div>
      
      {files.length > 0 && (
        <div className="file-list">
          {files.map((file, index) => (
            <div key={index} className="file-item">
              <FileIcon type={file.type} />
              <span className="file-name">{file.name}</span>
              <span className="file-size">{formatFileSize(file.size)}</span>
              <button onClick={() => removeFile(index)}>删除</button>
            </div>
          ))}
        </div>
      )}
      
      {uploading && (
        <div className="upload-progress">
          <div className="progress-bar" style={{width: `${uploadProgress}%`}} />
          <span>{uploadProgress}%</span>
        </div>
      )}
      
      <button 
        className="submit-button"
        onClick={handleSubmit}
        disabled={files.length === 0 || uploading}
      >
        {uploading ? '提交中...' : '提交作业'}
      </button>
    </div>
  );
};
```

#### 1.2.2 批改结果查看页面

**交互式错误标注**:
```tsx
const GradingResultView: React.FC<{submissionId: string}> = ({submissionId}) => {
  const [result, setResult] = useState<GradingResult | null>(null);
  const [displayMode, setDisplayMode] = useState<'coordinate' | 'cropped'>('coordinate');
  const [selectedError, setSelectedError] = useState<ErrorAnnotation | null>(null);
  
  return (
    <div className="grading-result-container">
      {/* 头部信息 */}
      <div className="result-header">
        <div className="score-section">
          <div className="score-circle">
            <span className="score-value">{result?.score}</span>
            <span className="score-max">/ {result?.maxScore}</span>
          </div>
          <div className="score-label">
            {getScoreLabel(result?.score, result?.maxScore)}
          </div>
        </div>
        
        <div className="display-mode-toggle">
          <button 
            className={displayMode === 'coordinate' ? 'active' : ''}
            onClick={() => setDisplayMode('coordinate')}
          >
            坐标标注
          </button>
          <button 
            className={displayMode === 'cropped' ? 'active' : ''}
            onClick={() => setDisplayMode('cropped')}
          >
            局部图卡片
          </button>
        </div>
      </div>
      
      {/* 批改内容 */}
      <div className="result-content">
        {displayMode === 'coordinate' ? (
          <CoordinateAnnotationView 
            imageUrl={result?.originalImageUrl}
            annotations={result?.annotations}
            onAnnotationClick={setSelectedError}
          />
        ) : (
          <CroppedRegionView 
            errors={result?.errors}
            onErrorClick={setSelectedError}
          />
        )}
      </div>
      
      {/* 错误详情侧边栏 */}
      {selectedError && (
        <div className="error-detail-sidebar">
          <h3>错误详情</h3>
          <div className="error-type">
            <span className="label">错误类型:</span>
            <span className="value">{selectedError.type}</span>
          </div>
          <div className="error-description">
            <span className="label">错误说明:</span>
            <p>{selectedError.description}</p>
          </div>
          <div className="correct-answer">
            <span className="label">正确答案:</span>
            <p>{selectedError.correctAnswer}</p>
          </div>
          <div className="knowledge-points">
            <span className="label">相关知识点:</span>
            <ul>
              {selectedError.knowledgePoints.map((kp, i) => (
                <li key={i}>{kp}</li>
              ))}
            </ul>
          </div>
          <div className="suggestions">
            <span className="label">改进建议:</span>
            <p>{selectedError.suggestion}</p>
          </div>
        </div>
      )}
      
      {/* 总体反馈 */}
      <div className="overall-feedback">
        <h3>总体评价</h3>
        <p>{result?.overallComment}</p>
        
        <div className="strengths-weaknesses">
          <div className="strengths">
            <h4>✅ 优点</h4>
            <ul>
              {result?.strengths.map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
          <div className="weaknesses">
            <h4>⚠️ 需要改进</h4>
            <ul>
              {result?.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

## 2. 实时反馈机制

### 2.1 WebSocket通信

**连接管理**:
```typescript
class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: Map<string, (data: any) => void> = new Map();
  
  connect(userId: string) {
    const wsUrl = `${WS_BASE_URL}/ws/${userId}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect(userId);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  private handleMessage(message: WebSocketMessage) {
    const handler = this.messageHandlers.get(message.type);
    if (handler) {
      handler(message.data);
    }
  }
  
  subscribe(messageType: string, handler: (data: any) => void) {
    this.messageHandlers.set(messageType, handler);
  }
  
  send(type: string, data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }
  
  private attemptReconnect(userId: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      setTimeout(() => {
        console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
        this.connect(userId);
      }, delay);
    }
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// 使用
const wsManager = new WebSocketManager();

// 订阅批改进度更新
wsManager.subscribe('grading_progress', (data) => {
  updateGradingProgress(data);
});

// 订阅批改完成通知
wsManager.subscribe('grading_completed', (data) => {
  showNotification('批改完成', data.message);
  refreshGradingResults();
});
```

### 2.2 进度追踪

**实时进度组件**:
```tsx
const RealTimeProgressTracker: React.FC<{taskId: string}> = ({taskId}) => {
  const [progress, setProgress] = useState<TaskProgress>({
    status: 'pending',
    progress: 0,
    currentStep: '',
    message: ''
  });
  
  useEffect(() => {
    // 订阅进度更新
    const unsubscribe = wsManager.subscribe('task_progress', (data) => {
      if (data.taskId === taskId) {
        setProgress(data);
      }
    });
    
    return () => unsubscribe();
  }, [taskId]);
  
  return (
    <div className="progress-tracker">
      <div className="progress-steps">
        <Step 
          name="预处理" 
          status={getStepStatus('preprocess', progress.currentStep)}
          icon={<FileIcon />}
        />
        <Step 
          name="AI批改" 
          status={getStepStatus('grading', progress.currentStep)}
          icon={<BrainIcon />}
        />
        <Step 
          name="质量审核" 
          status={getStepStatus('review', progress.currentStep)}
          icon={<CheckIcon />}
        />
        <Step 
          name="生成反馈" 
          status={getStepStatus('feedback', progress.currentStep)}
          icon={<MessageIcon />}
        />
      </div>
      
      <div className="progress-bar">
        <div 
          className="progress-fill"
          style={{width: `${progress.progress}%`}}
        />
      </div>
      
      <div className="progress-message">
        {progress.message}
      </div>
    </div>
  );
};
```

### 2.3 通知系统

**多渠道通知**:
```typescript
interface Notification {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  actionUrl?: string;
}

class NotificationManager {
  private notifications: Notification[] = [];
  private listeners: ((notifications: Notification[]) => void)[] = [];
  
  // 添加通知
  add(notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) {
    const newNotification: Notification = {
      ...notification,
      id: uuid(),
      timestamp: new Date(),
      read: false
    };
    
    this.notifications.unshift(newNotification);
    this.notify();
    
    // 显示Toast
    this.showToast(newNotification);
    
    // 浏览器通知
    if (Notification.permission === 'granted') {
      new Notification(newNotification.title, {
        body: newNotification.message,
        icon: '/icon.png'
      });
    }
  }
  
  // 标记为已读
  markAsRead(id: string) {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      notification.read = true;
      this.notify();
    }
  }
  
  // 获取未读数量
  getUnreadCount(): number {
    return this.notifications.filter(n => !n.read).length;
  }
  
  // 订阅通知变化
  subscribe(listener: (notifications: Notification[]) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }
  
  private notify() {
    this.listeners.forEach(listener => listener(this.notifications));
  }
  
  private showToast(notification: Notification) {
    toast[notification.type](notification.message, {
      duration: 5000,
      position: 'top-right'
    });
  }
}

// 使用
const notificationManager = new NotificationManager();

// WebSocket接收通知
wsManager.subscribe('notification', (data) => {
  notificationManager.add({
    type: data.type,
    title: data.title,
    message: data.message,
    actionUrl: data.actionUrl
  });
});
```

---

## 3. 响应式设计

### 3.1 移动端适配

**响应式布局**:
```scss
// 断点定义
$breakpoints: (
  'mobile': 320px,
  'tablet': 768px,
  'desktop': 1024px,
  'wide': 1440px
);

// 响应式Mixin
@mixin respond-to($breakpoint) {
  @media (min-width: map-get($breakpoints, $breakpoint)) {
    @content;
  }
}

// 使用
.grading-result-container {
  display: flex;
  flex-direction: column;
  
  @include respond-to('tablet') {
    flex-direction: row;
  }
  
  .result-content {
    width: 100%;
    
    @include respond-to('tablet') {
      width: 70%;
    }
  }
  
  .error-detail-sidebar {
    width: 100%;
    margin-top: 20px;
    
    @include respond-to('tablet') {
      width: 30%;
      margin-top: 0;
      margin-left: 20px;
    }
  }
}
```

### 3.2 触摸优化

**手势支持**:
```typescript
const useTouchGestures = (elementRef: React.RefObject<HTMLElement>) => {
  const [touchStart, setTouchStart] = useState<{x: number, y: number} | null>(null);
  const [scale, setScale] = useState(1);
  
  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    
    // 缩放手势
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const distance = Math.hypot(
          touch2.clientX - touch1.clientX,
          touch2.clientY - touch1.clientY
        );
        setTouchStart({x: distance, y: scale});
      }
    };
    
    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2 && touchStart) {
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const distance = Math.hypot(
          touch2.clientX - touch1.clientX,
          touch2.clientY - touch1.clientY
        );
        const newScale = touchStart.y * (distance / touchStart.x);
        setScale(Math.max(0.5, Math.min(3, newScale)));
      }
    };
    
    element.addEventListener('touchstart', handleTouchStart);
    element.addEventListener('touchmove', handleTouchMove);
    
    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchmove', handleTouchMove);
    };
  }, [elementRef, touchStart]);
  
  return { scale };
};
```

---

## 4. 性能优化

### 4.1 虚拟滚动

**大列表优化**:
```tsx
import { FixedSizeList } from 'react-window';

const VirtualizedResultList: React.FC<{results: GradingResult[]}> = ({results}) => {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style} className="result-row">
      <GradingResultCard result={results[index]} />
    </div>
  );
  
  return (
    <FixedSizeList
      height={600}
      itemCount={results.length}
      itemSize={120}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};
```

### 4.2 图片懒加载

```tsx
const LazyImage: React.FC<{src: string, alt: string}> = ({src, alt}) => {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setImageSrc(src);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.1 }
    );
    
    if (imgRef.current) {
      observer.observe(imgRef.current);
    }
    
    return () => observer.disconnect();
  }, [src]);
  
  return (
    <img 
      ref={imgRef}
      src={imageSrc || '/placeholder.png'}
      alt={alt}
      className="lazy-image"
    />
  );
};
```

---

**下一步**: 查看 `06_FRONTEND_MOCK_IMPLEMENTATION.md` 了解前端Mock实现

