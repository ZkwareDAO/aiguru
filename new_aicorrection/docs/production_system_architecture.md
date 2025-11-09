# 生产级 LangGraph AI 批改系统 - 架构设计文档

## 🏗️ 系统架构概览

### 整体架构
```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                        │
│  (ai_correction/streamlit_simple.py)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              LangGraph Workflow Layer                        │
│  (ai_correction/functions/langgraph/)                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ InputParser  │→ │ Question     │→ │ Rubric       │      │
│  │ Agent        │  │ Analyzer     │  │ Interpreter │      │
│  └──────────────┘  │ Agent        │  │ Agent        │      │
│                    └──────────────┘  └──────────────┘      │
│                           ↓                                  │
│                    ┌──────────────┐                          │
│                    │ Question     │                          │
│                    │ Grader Agent │ (逐题批改)              │
│                    │ (并行处理)   │                          │
│                    └──────────────┘                          │
│                           ↓                                  │
│                    ┌──────────────┐                          │
│                    │ Result       │                          │
│                    │ Aggregator   │                          │
│                    │ Agent        │                          │
│                    └──────────────┘                          │
│                           ↓                                  │
│                    ┌──────────────┐                          │
│                    │ Data         │                          │
│                    │ Persistence  │                          │
│                    │ Agent        │                          │
│                    └──────────────┘                          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼──┐  ┌──────▼──┐  ┌─────▼──────┐
│  LLM API │  │Database  │  │ Cache      │
│(Gemini/  │  │(PostgreSQL│  │(Redis/    │
│ GPT)     │  │ MySQL)   │  │ Memory)    │
└──────────┘  └──────────┘  └────────────┘
```

---

## 🤖 Agent 架构设计

### 1. InputParser Agent
**职责**：解析输入文件，提取题目、答案、学生信息

**输入**：
```python
{
    'question_files': List[str],      # 题目文件路径
    'answer_files': List[str],        # 答案文件路径
    'marking_files': List[str],       # 评分标准文件路径
}
```

**输出**：
```python
{
    'questions': [
        {
            'id': 1,
            'text': '题目文本',
            'type': 'choice',  # choice/fill/essay/calculation
            'difficulty': 'medium',
            'keywords': ['关键词1', '关键词2']
        }
    ],
    'answers': [
        {
            'question_id': 1,
            'student_id': '001',
            'student_name': '张三',
            'text': '答案文本'
        }
    ],
    'student_info': {
        'id': '001',
        'name': '张三',
        'class': '高一(1)班'
    }
}
```

**核心算法**：
- 使用正则表达式识别题目边界（如"1."、"(1)"等）
- 使用NLP识别题型
- 从文件名和文本中提取学生信息

---

### 2. QuestionAnalyzer Agent
**职责**：分析题目特征，识别题型和难度

**输入**：
```python
{
    'questions': List[Dict]  # 题目列表
}
```

**输出**：
```python
{
    'questions_analyzed': [
        {
            'id': 1,
            'type': 'choice',
            'difficulty': 'medium',
            'keywords': ['关键词1'],
            'expected_answer_length': 'short',  # short/medium/long
            'grading_strategy': 'keyword_match'  # keyword_match/semantic/rubric
        }
    ]
}
```

**核心算法**：
- 题型识别：通过题目特征识别（选择题有选项、填空题有下划线等）
- 难度评估：通过关键词和长度评估
- 批改策略选择：根据题型选择不同的批改方法

---

### 3. RubricInterpreter Agent
**职责**：解析评分标准，生成结构化的评分规则

**输入**：
```python
{
    'marking_files': List[str]  # 评分标准文件
}
```

**输出**：
```python
{
    'rubric': {
        'dimensions': [
            {
                'name': '准确性',
                'weight': 0.5,
                'levels': [
                    {'score': 10, 'description': '完全正确'},
                    {'score': 8, 'description': '基本正确，有小错误'},
                    {'score': 5, 'description': '部分正确'},
                    {'score': 0, 'description': '完全错误'}
                ]
            }
        ],
        'total_score': 100,
        'passing_score': 60
    }
}
```

**核心算法**：
- 使用LLM解析评分标准
- 提取评分维度和权重
- 生成评分指南

---

### 4. QuestionGrader Agent
**职责**：对单个题目进行批改，生成得分和反馈

**输入**：
```python
{
    'question': Dict,        # 单个题目
    'answer': Dict,          # 单个答案
    'rubric': Dict,          # 评分标准
    'grading_strategy': str  # 批改策略
}
```

**输出**：
```python
{
    'question_id': 1,
    'score': 8,
    'max_score': 10,
    'grade_level': 'B',
    'feedback': {
        'summary': '总体评价',
        'strengths': ['优点1', '优点2'],
        'weaknesses': ['缺点1', '缺点2'],
        'suggestions': ['建议1', '建议2']
    },
    'errors': [
        {
            'type': 'grammar',  # grammar/logic/knowledge/spelling
            'severity': 'high',  # high/medium/low
            'location': '第2段第3句',
            'description': '错误描述',
            'correction': '改正建议'
        }
    ],
    'knowledge_points': [
        {
            'name': '知识点名称',
            'mastery_level': 0.8,  # 0-1
            'gaps': ['缺陷1', '缺陷2']
        }
    ]
}
```

**核心算法**：
- 根据题型选择批改策略
- 调用LLM进行批改
- 提取错误信息和知识点
- 生成改进建议

---

### 5. ResultAggregator Agent
**职责**：聚合所有题目的批改结果，生成整体报告

**输入**：
```python
{
    'grading_results': List[Dict],  # 所有题目的批改结果
    'student_info': Dict            # 学生信息
}
```

**输出**：
```python
{
    'student_id': '001',
    'student_name': '张三',
    'total_score': 85,
    'max_score': 100,
    'grade_level': 'A',
    'pass': True,
    'question_results': [...],  # 所有题目的结果
    'statistics': {
        'error_distribution': {'grammar': 2, 'logic': 1},
        'knowledge_points': [
            {'name': '知识点1', 'mastery': 0.8},
            {'name': '知识点2', 'mastery': 0.6}
        ],
        'strengths': ['优点1', '优点2'],
        'improvement_areas': ['改进方向1', '改进方向2']
    }
}
```

**核心算法**：
- 计算总分（加权求和）
- 计算等级（根据总分）
- 统计错误分布
- 分析知识点掌握度
- 生成改进建议

---

### 6. DataPersistence Agent
**职责**：将批改结果存储到数据库

**输入**：
```python
{
    'grading_result': Dict,  # 完整的批改结果
    'user_id': str,
    'task_id': str
}
```

**输出**：
```python
{
    'success': True,
    'task_id': str,
    'records_created': int,
    'database_ids': {
        'grading_task_id': 123,
        'student_id': 456,
        'result_records': [789, 790, 791]
    }
}
```

**核心算法**：
- 存储批改任务信息
- 存储学生信息
- 存储逐题批改结果
- 存储统计数据
- 建立关联关系

---

## 📊 GradingState 数据模型

```python
class GradingState(TypedDict):
    # 基本信息
    task_id: str
    user_id: str
    timestamp: str
    
    # 输入数据
    question_files: List[str]
    answer_files: List[str]
    marking_files: List[str]
    
    # 解析后的数据
    questions: List[Dict]
    answers: List[Dict]
    rubric: Dict
    
    # 学生信息
    student_info: Dict
    
    # 处理状态
    current_question_id: int
    processed_questions: List[int]
    progress: float  # 0-1
    
    # 批改结果
    grading_results: List[Dict]
    total_score: float
    grade_level: str
    
    # 统计数据
    statistics: Dict
    
    # 配置
    mode: str  # 'fast' / 'detailed'
    strictness_level: str
    language: str
    
    # 错误处理
    errors: List[str]
    retry_count: int
```

---

## 🔄 工作流编排

### 工作流图
```
InputParser
    ↓
    ├→ QuestionAnalyzer (并行)
    └→ RubricInterpreter (并行)
        ↓
        ├→ QuestionGrader (对每个题目，可并行)
        │   ↓
        │   (流式返回中间结果)
        │
        └→ ResultAggregator
            ↓
            DataPersistence
                ↓
                END
```

### 关键特性
1. **并行处理**：QuestionAnalyzer 和 RubricInterpreter 并行执行
2. **逐题批改**：QuestionGrader 对每道题单独处理
3. **流式返回**：每完成一道题就返回结果，不等待全部完成
4. **条件路由**：根据题型选择不同的批改策略
5. **错误处理**：失败自动重试，最多3次

---

## 💾 数据库表结构

### 1. students 表
```sql
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    class VARCHAR(100),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. grading_tasks 表
```sql
CREATE TABLE grading_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    student_id VARCHAR(50),
    status VARCHAR(20),  -- pending/processing/completed/failed
    total_questions INT,
    processed_questions INT,
    progress FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);
```

### 3. grading_results 表
```sql
CREATE TABLE grading_results (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    question_id INT NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    score FLOAT NOT NULL,
    max_score FLOAT NOT NULL,
    feedback TEXT,
    errors JSONB,
    knowledge_points JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES grading_tasks(task_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);
```

### 4. grading_statistics 表
```sql
CREATE TABLE grading_statistics (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    total_score FLOAT,
    grade_level VARCHAR(10),
    error_distribution JSONB,
    knowledge_mastery JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES grading_tasks(task_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);
```

### 5. error_analysis 表
```sql
CREATE TABLE error_analysis (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    question_id INT NOT NULL,
    error_type VARCHAR(50),  -- grammar/logic/knowledge/spelling
    severity VARCHAR(20),    -- high/medium/low
    count INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES grading_tasks(task_id)
);
```

---

## 🚀 性能优化策略

### 1. Token 优化
- **压缩输入**：只发送必要的信息
- **缓存结果**：相同题目的批改结果缓存
- **分批处理**：避免一次性发送过多内容

### 2. 并行处理
- **题目并行**：多个题目同时批改（受API限制）
- **Agent并行**：QuestionAnalyzer 和 RubricInterpreter 并行

### 3. 流式处理
- **实时返回**：每完成一道题就返回结果
- **进度显示**：实时更新处理进度

### 4. 缓存机制
- **题目缓存**：相同题目的批改结果
- **学生缓存**：学生信息缓存
- **评分标准缓存**：评分标准缓存

---

## 🔐 安全性考虑

1. **数据隐私**：学生信息加密存储
2. **访问控制**：基于Firebase Auth的权限管理
3. **审计日志**：记录所有批改操作
4. **数据备份**：定期备份数据库

---

## 📈 可扩展性设计

1. **模块化**：每个Agent独立，易于替换
2. **插件化**：支持自定义Agent
3. **配置化**：支持不同的批改策略配置
4. **多租户**：支持多个教育机构使用

