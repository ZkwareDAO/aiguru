# 阶段一实施计划 - 成本优化版

## 📌 计划概述

**目标**: 实现基础的AI批改系统,集成成本优化策略,单次批改成本控制在$0.010以内

**时间**: 2周 (10个工作日)

**预期成果**:
- ✅ 完成UnifiedGradingAgent实现
- ✅ 实现智能模式选择
- ✅ 添加相似度缓存
- ✅ 完成单份批改功能
- ✅ 基础前端界面
- ✅ 成本降低40%

---

## 📅 详细时间表

### Week 1: 后端核心功能

#### Day 1-2: 环境搭建与基础架构

**任务清单**:
- [ ] 搭建开发环境
- [ ] 配置LangChain/LangGraph
- [ ] 创建数据库模型
- [ ] 配置OpenRouter API

**详细任务**:

##### Task 1.1: 环境搭建 (2小时)
```bash
# 1. 创建虚拟环境
cd new_aicorrection/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 如果requirements.txt不存在,安装以下包:
pip install fastapi uvicorn sqlalchemy alembic
pip install langchain langgraph langchain-openai
pip install redis asyncpg python-multipart
pip install pydantic pydantic-settings
pip install python-jose passlib bcrypt
pip install pytest pytest-asyncio httpx
```

##### Task 1.2: 配置文件 (1小时)

创建 `backend/app/core/config.py`:
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "AI Grading System"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/aigrading"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI配置
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL: str = "google/gemini-2.0-flash-exp:free"
    
    # 成本优化配置
    ENABLE_UNIFIED_AGENT: bool = True  # 启用Agent融合
    ENABLE_SMART_CACHE: bool = True    # 启用智能缓存
    CACHE_SIMILARITY_THRESHOLD: float = 0.85
    
    # 模式配置
    DEFAULT_GRADING_MODE: str = "fast"  # fast/standard/premium
    
    class Config:
        env_file = ".env"

settings = Settings()
```

创建 `.env` 文件:
```bash
# .env
OPENROUTER_API_KEY=your_api_key_here
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/aigrading
REDIS_URL=redis://localhost:6379/0
DEBUG=True
```

##### Task 1.3: 数据库模型 (2小时)

创建 `backend/app/models/grading.py`:
```python
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base

class Assignment(Base):
    """作业表"""
    __tablename__ = "assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    subject = Column(String(50))
    grade_level = Column(String(20))
    max_score = Column(Float, default=100.0)
    
    # 批改标准
    grading_standard = Column(JSON)  # {criteria: str, answer: str, rubric: dict}
    
    # 配置
    config = Column(JSON)  # {strictness: str, enable_review: bool}
    
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    submissions = relationship("Submission", back_populates="assignment")


class Submission(Base):
    """提交表"""
    __tablename__ = "submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # 文件信息
    files = Column(JSON)  # [{file_id, file_path, file_type}]
    
    # 状态
    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    assignment = relationship("Assignment", back_populates="submissions")
    grading_result = relationship("GradingResult", back_populates="submission", uselist=False)


class GradingResult(Base):
    """批改结果表"""
    __tablename__ = "grading_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id"), unique=True)
    
    # 批改结果
    score = Column(Float)
    max_score = Column(Float)
    confidence = Column(Float)
    
    # 错误和标注
    errors = Column(JSON)  # [{type, description, location, severity}]
    annotations = Column(JSON)  # [{x, y, width, height, label}]
    
    # 反馈
    feedback_text = Column(Text)
    suggestions = Column(JSON)  # [str]
    knowledge_points = Column(JSON)  # [{name, mastery_level, suggestion}]
    
    # 元数据
    grading_mode = Column(String(20))  # fast/standard/premium
    processing_time_ms = Column(Integer)
    from_cache = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    submission = relationship("Submission", back_populates="grading_result")
```

##### Task 1.4: 数据库迁移 (1小时)
```bash
# 初始化Alembic
cd backend
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Initial tables"

# 执行迁移
alembic upgrade head
```

**验收标准**:
- ✅ 虚拟环境创建成功
- ✅ 所有依赖安装完成
- ✅ 配置文件正确加载
- ✅ 数据库连接成功
- ✅ 数据表创建成功

---

#### Day 3-4: UnifiedGradingAgent实现

**任务清单**:
- [ ] 实现UnifiedGradingAgent
- [ ] 实现PreprocessAgent
- [ ] 集成LangChain LLM
- [ ] 编写单元测试

**详细任务**:

##### Task 2.1: 状态定义 (1小时)

创建 `backend/app/agents/state.py`:
```python
from typing import TypedDict, List, Dict, Optional, Annotated
from uuid import UUID
from datetime import datetime
from operator import add

class GradingState(TypedDict):
    """批改流程状态"""
    # 基础信息
    submission_id: UUID
    assignment_id: UUID
    status: str  # pending/preprocessing/grading/completed/failed
    
    # 配置
    grading_mode: str  # fast/standard/premium
    config: Dict
    
    # 预处理结果
    preprocessed_files: List[Dict]
    extracted_text: str
    file_metadata: Dict
    
    # 批改结果
    score: Optional[float]
    max_score: float
    errors: List[Dict]
    annotations: List[Dict]
    confidence: float
    
    # 反馈结果
    feedback_text: str
    suggestions: List[str]
    knowledge_points: List[Dict]
    
    # 元数据
    processing_start_time: datetime
    processing_end_time: Optional[datetime]
    from_cache: bool
    error_message: Optional[str]
    
    # 消息历史 (用于LangGraph)
    messages: Annotated[List[Dict], add]
```

##### Task 2.2: UnifiedGradingAgent实现 (4小时)

创建 `backend/app/agents/unified_grading_agent.py`:
```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import Dict
import json
import logging

from app.core.config import settings
from app.agents.state import GradingState

logger = logging.getLogger(__name__)

class UnifiedGradingAgent:
    """统一批改Agent - 一次LLM调用完成批改+反馈"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.DEFAULT_MODEL,
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base=settings.OPENROUTER_BASE_URL,
            temperature=0.3,
            max_tokens=2000
        )
        
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """创建统一提示词模板"""
        return ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的教师,正在批改学生作业。
请一次性完成以下所有任务:
1. 批改评分 - 找出错误,计算分数
2. 错误分析 - 详细说明每个错误
3. 总体反馈 - 优点、不足、改进建议
4. 知识点关联 - 相关知识点和学习建议

请严格按照JSON格式输出,不要添加任何额外的文字说明。"""),
            ("user", """{grading_prompt}""")
        ])
    
    async def process(self, state: GradingState) -> GradingState:
        """执行统一批改"""
        try:
            logger.info(f"UnifiedGradingAgent processing submission {state['submission_id']}")
            
            # 1. 构建提示词
            prompt = self._build_grading_prompt(state)
            
            # 2. 调用LLM
            messages = self.prompt_template.format_messages(grading_prompt=prompt)
            response = await self.llm.ainvoke(messages)
            
            # 3. 解析结果
            result = self._parse_result(response.content)
            
            # 4. 更新状态
            state["score"] = result["score"]
            state["confidence"] = result["confidence"]
            state["errors"] = result["errors"]
            state["feedback_text"] = result["overall_comment"]
            state["suggestions"] = result["suggestions"]
            state["knowledge_points"] = result.get("knowledge_points", [])
            state["status"] = "completed"
            
            logger.info(f"Grading completed: score={result['score']}, confidence={result['confidence']}")
            
            return state
            
        except Exception as e:
            logger.error(f"UnifiedGradingAgent error: {str(e)}")
            state["status"] = "failed"
            state["error_message"] = str(e)
            return state
    
    def _build_grading_prompt(self, state: GradingState) -> str:
        """构建批改提示词"""
        grading_standard = state["config"].get("grading_standard", {})
        
        prompt = f"""
【批改标准】
{grading_standard.get('criteria', '请根据标准答案批改')}

【标准答案】
{grading_standard.get('answer', '')}

【学生答案】
{state['extracted_text']}

【批改要求】
- 满分: {state['max_score']}分
- 严格程度: {state['config'].get('strictness', 'standard')}
- 请逐项对照标准答案,找出学生答案中的错误
- 对每个错误,请说明错误类型、位置、原因和正确答案
- 请给出总体评价和改进建议
- 请关联相关知识点并给出学习建议

【输出格式】
请严格按照以下JSON格式输出:
{{
    "score": 分数(0-{state['max_score']}),
    "confidence": 置信度(0-1),
    "errors": [
        {{
            "type": "错误类型(概念错误/计算错误/表述错误等)",
            "location": "错误位置描述",
            "description": "错误说明",
            "correct_answer": "正确答案",
            "severity": "high|medium|low",
            "deduction": 扣分
        }}
    ],
    "overall_comment": "总体评价(100字以内)",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["改进建议1", "改进建议2", "改进建议3"],
    "knowledge_points": [
        {{
            "name": "知识点名称",
            "mastery_level": 掌握程度(0-100),
            "suggestion": "学习建议"
        }}
    ]
}}
"""
        return prompt
    
    def _parse_result(self, content: str) -> Dict:
        """解析LLM返回结果"""
        try:
            # 尝试直接解析JSON
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # 如果解析失败,尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                raise ValueError("Failed to parse LLM response as JSON")
```

**验收标准**:
- ✅ UnifiedGradingAgent能成功调用LLM
- ✅ 能正确解析JSON响应
- ✅ 单元测试通过
- ✅ 单次调用成本 < $0.012

---

#### Day 5-6: 智能模式选择与缓存

**任务清单**:
- [ ] 实现SmartOrchestrator
- [ ] 实现复杂度评估
- [ ] 实现智能缓存
- [ ] 集成Redis

##### Task 3.1: 复杂度评估器 (2小时)

创建 `backend/app/agents/complexity_assessor.py`:
```python
from typing import Dict
from app.agents.state import GradingState

class ComplexityAssessor:
    """任务复杂度评估器"""

    def assess(self, state: GradingState) -> str:
        """评估任务复杂度

        Returns:
            "simple" | "medium" | "complex"
        """
        factors = self._extract_factors(state)
        score = self._calculate_complexity_score(factors)

        if score < 30:
            return "simple"
        elif score < 70:
            return "medium"
        else:
            return "complex"

    def _extract_factors(self, state: GradingState) -> Dict:
        """提取复杂度因素"""
        return {
            "file_count": len(state.get("preprocessed_files", [])),
            "text_length": len(state.get("extracted_text", "")),
            "question_count": state["config"].get("question_count", 1),
            "has_images": any(f.get("type") == "image" for f in state.get("preprocessed_files", [])),
            "subject": state["config"].get("subject", ""),
        }

    def _calculate_complexity_score(self, factors: Dict) -> int:
        """计算复杂度分数 (0-100)"""
        score = 0

        # 文件数量 (0-20分)
        if factors["file_count"] == 1:
            score += 0
        elif factors["file_count"] <= 3:
            score += 10
        else:
            score += 20

        # 文本长度 (0-30分)
        text_length = factors["text_length"]
        if text_length < 500:
            score += 0
        elif text_length < 2000:
            score += 15
        else:
            score += 30

        # 题目数量 (0-20分)
        question_count = factors["question_count"]
        if question_count <= 3:
            score += 0
        elif question_count <= 10:
            score += 10
        else:
            score += 20

        # 是否包含图片 (0-15分)
        if factors["has_images"]:
            score += 15

        # 学科难度 (0-15分)
        difficult_subjects = ["数学", "物理", "化学", "math", "physics"]
        if factors["subject"].lower() in difficult_subjects:
            score += 15

        return min(score, 100)
```

##### Task 3.2: SmartOrchestrator实现 (3小时)

创建 `backend/app/agents/smart_orchestrator.py`:
```python
from langgraph.graph import StateGraph, END
from typing import Dict
import logging
from datetime import datetime

from app.agents.state import GradingState
from app.agents.unified_grading_agent import UnifiedGradingAgent
from app.agents.preprocess_agent import PreprocessAgent
from app.agents.complexity_assessor import ComplexityAssessor
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class SmartOrchestrator:
    """智能编排器 - 根据复杂度选择Agent组合"""

    def __init__(self):
        self.unified_agent = UnifiedGradingAgent()
        self.preprocess_agent = PreprocessAgent()
        self.complexity_assessor = ComplexityAssessor()
        self.cache_service = CacheService()

        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流"""
        workflow = StateGraph(GradingState)

        # 添加节点
        workflow.add_node("check_cache", self._check_cache)
        workflow.add_node("preprocess", self._preprocess_step)
        workflow.add_node("assess_complexity", self._assess_complexity_step)
        workflow.add_node("unified_grading", self._unified_grading_step)
        workflow.add_node("finalize", self._finalize_step)

        # 定义流程
        workflow.set_entry_point("check_cache")

        workflow.add_conditional_edges(
            "check_cache",
            self._should_use_cache,
            {
                "use_cache": "finalize",
                "process": "preprocess"
            }
        )

        workflow.add_edge("preprocess", "assess_complexity")
        workflow.add_edge("assess_complexity", "unified_grading")
        workflow.add_edge("unified_grading", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def execute(self, input_data: Dict) -> Dict:
        """执行批改流程"""
        # 初始化状态
        initial_state = GradingState(
            submission_id=input_data["submission_id"],
            assignment_id=input_data["assignment_id"],
            status="pending",
            grading_mode=input_data.get("mode", "fast"),
            config=input_data.get("config", {}),
            max_score=input_data.get("max_score", 100.0),
            processing_start_time=datetime.utcnow(),
            from_cache=False,
            messages=[]
        )

        # 执行工作流
        result = await self.workflow.ainvoke(initial_state)

        return result

    async def _check_cache(self, state: GradingState) -> GradingState:
        """检查缓存"""
        cached_result = await self.cache_service.get_similar(
            submission_id=state["submission_id"]
        )

        if cached_result:
            logger.info(f"Cache hit for submission {state['submission_id']}")
            state.update(cached_result)
            state["from_cache"] = True
            state["status"] = "completed"

        return state

    def _should_use_cache(self, state: GradingState) -> str:
        """判断是否使用缓存"""
        return "use_cache" if state["from_cache"] else "process"

    async def _preprocess_step(self, state: GradingState) -> GradingState:
        """预处理步骤"""
        return await self.preprocess_agent.process(state)

    async def _assess_complexity_step(self, state: GradingState) -> GradingState:
        """评估复杂度"""
        complexity = self.complexity_assessor.assess(state)
        state["config"]["complexity"] = complexity
        logger.info(f"Assessed complexity: {complexity}")
        return state

    async def _unified_grading_step(self, state: GradingState) -> GradingState:
        """统一批改步骤"""
        return await self.unified_agent.process(state)

    async def _finalize_step(self, state: GradingState) -> GradingState:
        """完成步骤"""
        state["processing_end_time"] = datetime.utcnow()

        # 计算处理时间
        processing_time = (
            state["processing_end_time"] - state["processing_start_time"]
        ).total_seconds() * 1000

        state["processing_time_ms"] = int(processing_time)

        # 缓存结果
        if not state["from_cache"]:
            await self.cache_service.store(state)

        logger.info(f"Grading completed in {processing_time}ms")

        return state
```

##### Task 3.3: 智能缓存实现 (3小时)

创建 `backend/app/services/cache_service.py`:
```python
import redis.asyncio as redis
from typing import Optional, Dict
import json
import hashlib
from uuid import UUID

from app.core.config import settings
from app.agents.state import GradingState

class CacheService:
    """智能缓存服务"""

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
        self.similarity_threshold = settings.CACHE_SIMILARITY_THRESHOLD
        self.ttl = 7 * 24 * 3600  # 7天

    async def get_similar(self, submission_id: UUID) -> Optional[Dict]:
        """获取相似的缓存结果"""
        if not settings.ENABLE_SMART_CACHE:
            return None

        # 1. 获取提交内容
        from app.services.submission_service import SubmissionService
        submission_service = SubmissionService()
        submission = await submission_service.get(submission_id)

        if not submission:
            return None

        # 2. 计算内容哈希
        content_hash = self._compute_hash(submission.extracted_text)

        # 3. 查找相似的缓存
        cache_key = f"grading_cache:{content_hash}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        return None

    async def store(self, state: GradingState) -> None:
        """存储批改结果到缓存"""
        if not settings.ENABLE_SMART_CACHE:
            return

        # 计算内容哈希
        content_hash = self._compute_hash(state["extracted_text"])

        # 准备缓存数据
        cache_data = {
            "score": state["score"],
            "confidence": state["confidence"],
            "errors": state["errors"],
            "feedback_text": state["feedback_text"],
            "suggestions": state["suggestions"],
            "knowledge_points": state["knowledge_points"],
        }

        # 存储到Redis
        cache_key = f"grading_cache:{content_hash}"
        await self.redis.setex(
            cache_key,
            self.ttl,
            json.dumps(cache_data, ensure_ascii=False)
        )

    def _compute_hash(self, text: str) -> str:
        """计算文本哈希"""
        # 使用MD5快速哈希
        return hashlib.md5(text.encode('utf-8')).hexdigest()
```

**验收标准**:
- ✅ SmartOrchestrator能根据复杂度选择模式
- ✅ 缓存命中率 > 20%
- ✅ 缓存响应时间 < 100ms

---

#### Day 7: API接口实现

##### Task 4.1: 批改API (3小时)

创建 `backend/app/api/v1/endpoints/grading.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.api import deps
from app.schemas.grading import GradingRequest, GradingResponse, GradingStatusResponse
from app.services.grading_service import GradingService
from app.models.user import User

router = APIRouter()

@router.post("/submit", response_model=GradingResponse)
async def submit_grading(
    request: GradingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """提交批改请求"""
    grading_service = GradingService(db)

    # 创建批改任务
    task = await grading_service.create_grading_task(
        submission_id=request.submission_id,
        mode=request.mode,
        user_id=current_user.id
    )

    # 异步执行批改
    background_tasks.add_task(
        grading_service.execute_grading,
        task_id=task.id
    )

    return GradingResponse(
        task_id=task.id,
        status="pending",
        message="批改任务已创建,正在处理中..."
    )

@router.get("/status/{task_id}", response_model=GradingStatusResponse)
async def get_grading_status(
    task_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """查询批改状态"""
    grading_service = GradingService(db)

    status = await grading_service.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status

@router.get("/result/{submission_id}")
async def get_grading_result(
    submission_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """获取批改结果"""
    grading_service = GradingService(db)

    result = await grading_service.get_result(submission_id)

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return result
```

创建 `backend/app/schemas/grading.py`:
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, List, Dict
from datetime import datetime

class GradingRequest(BaseModel):
    submission_id: UUID
    mode: str = "fast"  # fast/standard/premium

class GradingResponse(BaseModel):
    task_id: UUID
    status: str
    message: str

class GradingStatusResponse(BaseModel):
    task_id: UUID
    status: str
    progress: int  # 0-100
    result: Optional[Dict] = None
    error: Optional[str] = None

class ErrorDetail(BaseModel):
    type: str
    location: str
    description: str
    correct_answer: str
    severity: str
    deduction: float

class KnowledgePoint(BaseModel):
    name: str
    mastery_level: int
    suggestion: str

class GradingResultDetail(BaseModel):
    submission_id: UUID
    score: float
    max_score: float
    confidence: float
    errors: List[ErrorDetail]
    feedback_text: str
    suggestions: List[str]
    knowledge_points: List[KnowledgePoint]
    grading_mode: str
    processing_time_ms: int
    from_cache: bool
    created_at: datetime
```

**验收标准**:
- ✅ API能成功接收批改请求
- ✅ 能查询批改状态
- ✅ 能获取批改结果
- ✅ API文档自动生成

---

## 📋 完整任务清单

### 后端任务 (Day 1-7)

#### 基础架构 (Day 1-2)
- [ ] 1.1 创建虚拟环境并安装依赖
- [ ] 1.2 配置环境变量和设置文件
- [ ] 1.3 创建数据库模型
- [ ] 1.4 执行数据库迁移
- [ ] 1.5 配置Redis连接

#### 核心Agent (Day 3-4)
- [ ] 2.1 实现GradingState状态定义
- [ ] 2.2 实现UnifiedGradingAgent
- [ ] 2.3 实现PreprocessAgent
- [ ] 2.4 编写Agent单元测试

#### 智能优化 (Day 5-6)
- [ ] 3.1 实现复杂度评估器
- [ ] 3.2 实现SmartOrchestrator
- [ ] 3.3 实现智能缓存系统
- [ ] 3.4 实现相似度计算

#### API接口 (Day 7)
- [ ] 4.1 实现批改API端点
- [ ] 4.2 实现结果查询API
- [ ] 4.3 实现WebSocket实时通知
- [ ] 4.4 编写API测试

### 前端任务 (Day 8-10)

#### 基础界面 (Day 8)
- [ ] 5.1 创建作业提交页面
- [ ] 5.2 创建批改进度页面
- [ ] 5.3 创建结果展示页面

##### Task 5.1: 作业提交页面 (2小时)

创建 `frontend/app/grading/submit/page.tsx`:
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { FileUpload } from '@/components/FileUpload';
import { gradingAPI } from '@/services/api';

export default function SubmitGradingPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [mode, setMode] = useState<'fast' | 'standard' | 'premium'>('fast');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (files.length === 0) {
      alert('请先上传文件');
      return;
    }

    setLoading(true);
    try {
      // 1. 上传文件
      const uploadedFiles = await gradingAPI.uploadFiles(files);

      // 2. 创建提交
      const submission = await gradingAPI.createSubmission({
        assignmentId: 'xxx', // 从路由获取
        files: uploadedFiles,
      });

      // 3. 提交批改
      const result = await gradingAPI.submitGrading({
        submissionId: submission.id,
        mode,
      });

      // 4. 跳转到进度页面
      router.push(`/grading/progress/${result.taskId}`);
    } catch (error) {
      console.error('提交失败:', error);
      alert('提交失败,请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto py-8">
      <Card className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">提交作业</h1>

        {/* 文件上传 */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            上传作业文件
          </label>
          <FileUpload
            files={files}
            onChange={setFiles}
            accept="image/*,.pdf"
            maxSize={10 * 1024 * 1024}
          />
        </div>

        {/* 批改模式选择 */}
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            批改模式
          </label>
          <Select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="fast">快速模式 (¥0.5)</option>
            <option value="standard">标准模式 (¥1.0)</option>
            <option value="premium">精品模式 (¥2.0)</option>
          </Select>

          <div className="mt-2 text-sm text-gray-600">
            {mode === 'fast' && '快速批改,适合简单题目'}
            {mode === 'standard' && '标准批改,包含详细反馈'}
            {mode === 'premium' && '精品批改,包含学习建议'}
          </div>
        </div>

        {/* 提交按钮 */}
        <Button
          onClick={handleSubmit}
          disabled={loading || files.length === 0}
          className="w-full"
        >
          {loading ? '提交中...' : '提交批改'}
        </Button>
      </Card>
    </div>
  );
}
```

##### Task 5.2: 批改进度页面 (2小时)

创建 `frontend/app/grading/progress/[taskId]/page.tsx`:
```typescript
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { gradingAPI } from '@/services/api';

interface GradingStatus {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: any;
  error?: string;
}

export default function GradingProgressPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskId as string;

  const [status, setStatus] = useState<GradingStatus | null>(null);

  useEffect(() => {
    // 轮询查询状态
    const interval = setInterval(async () => {
      try {
        const data = await gradingAPI.getGradingStatus(taskId);
        setStatus(data);

        // 如果完成,跳转到结果页面
        if (data.status === 'completed') {
          clearInterval(interval);
          setTimeout(() => {
            router.push(`/grading/result/${data.result.submissionId}`);
          }, 1000);
        }

        // 如果失败,显示错误
        if (data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('查询状态失败:', error);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [taskId, router]);

  if (!status) {
    return <div>加载中...</div>;
  }

  return (
    <div className="container mx-auto py-8">
      <Card className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">批改进度</h1>

        {/* 进度条 */}
        <div className="mb-6">
          <Progress value={status.progress} className="h-4" />
          <div className="mt-2 text-center text-sm text-gray-600">
            {status.progress}%
          </div>
        </div>

        {/* 状态信息 */}
        <div className="space-y-4">
          {status.status === 'pending' && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p>等待处理中...</p>
            </div>
          )}

          {status.status === 'processing' && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p>正在批改中...</p>
            </div>
          )}

          {status.status === 'completed' && (
            <div className="text-center text-green-600">
              <svg className="h-12 w-12 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <p>批改完成!</p>
              <p className="text-sm text-gray-600 mt-2">正在跳转到结果页面...</p>
            </div>
          )}

          {status.status === 'failed' && (
            <div className="text-center text-red-600">
              <svg className="h-12 w-12 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <p>批改失败</p>
              <p className="text-sm text-gray-600 mt-2">{status.error}</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
```

##### Task 5.3: 结果展示页面 (3小时)

创建 `frontend/app/grading/result/[submissionId]/page.tsx`:
```typescript
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { gradingAPI } from '@/services/api';

interface GradingResult {
  submissionId: string;
  score: number;
  maxScore: number;
  confidence: number;
  errors: Array<{
    type: string;
    location: string;
    description: string;
    correctAnswer: string;
    severity: 'high' | 'medium' | 'low';
    deduction: number;
  }>;
  feedbackText: string;
  suggestions: string[];
  knowledgePoints: Array<{
    name: string;
    masteryLevel: number;
    suggestion: string;
  }>;
  gradingMode: string;
  processingTimeMs: number;
  fromCache: boolean;
}

export default function GradingResultPage() {
  const params = useParams();
  const submissionId = params.submissionId as string;

  const [result, setResult] = useState<GradingResult | null>(null);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const data = await gradingAPI.getGradingResult(submissionId);
        setResult(data);
      } catch (error) {
        console.error('获取结果失败:', error);
      }
    };

    fetchResult();
  }, [submissionId]);

  if (!result) {
    return <div>加载中...</div>;
  }

  const scorePercentage = (result.score / result.maxScore) * 100;
  const scoreColor = scorePercentage >= 80 ? 'text-green-600' :
                     scorePercentage >= 60 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="container mx-auto py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 分数卡片 */}
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold mb-2">批改结果</h1>
              <div className="flex items-center gap-2">
                <Badge variant={result.fromCache ? 'secondary' : 'default'}>
                  {result.fromCache ? '缓存结果' : '实时批改'}
                </Badge>
                <Badge variant="outline">
                  {result.gradingMode === 'fast' ? '快速模式' :
                   result.gradingMode === 'standard' ? '标准模式' : '精品模式'}
                </Badge>
                <span className="text-sm text-gray-600">
                  耗时: {result.processingTimeMs}ms
                </span>
              </div>
            </div>

            <div className="text-right">
              <div className={`text-5xl font-bold ${scoreColor}`}>
                {result.score}
              </div>
              <div className="text-gray-600">/ {result.maxScore}</div>
              <div className="text-sm text-gray-500 mt-1">
                置信度: {(result.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </Card>

        {/* 错误列表 */}
        {result.errors.length > 0 && (
          <Card className="p-6">
            <h2 className="text-xl font-bold mb-4">错误详情</h2>
            <div className="space-y-4">
              {result.errors.map((error, index) => (
                <div key={index} className="border-l-4 border-red-500 pl-4 py-2">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant={
                      error.severity === 'high' ? 'destructive' :
                      error.severity === 'medium' ? 'warning' : 'secondary'
                    }>
                      {error.type}
                    </Badge>
                    <span className="text-sm text-gray-600">
                      扣{error.deduction}分
                    </span>
                  </div>
                  <p className="text-sm mb-1">
                    <strong>位置:</strong> {error.location}
                  </p>
                  <p className="text-sm mb-1">
                    <strong>说明:</strong> {error.description}
                  </p>
                  <p className="text-sm text-green-600">
                    <strong>正确答案:</strong> {error.correctAnswer}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* 总体反馈 */}
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">总体反馈</h2>
          <p className="text-gray-700 whitespace-pre-wrap">
            {result.feedbackText}
          </p>
        </Card>

        {/* 改进建议 */}
        {result.suggestions.length > 0 && (
          <Card className="p-6">
            <h2 className="text-xl font-bold mb-4">改进建议</h2>
            <ul className="list-disc list-inside space-y-2">
              {result.suggestions.map((suggestion, index) => (
                <li key={index} className="text-gray-700">{suggestion}</li>
              ))}
            </ul>
          </Card>
        )}

        {/* 知识点分析 */}
        {result.knowledgePoints.length > 0 && (
          <Card className="p-6">
            <h2 className="text-xl font-bold mb-4">知识点掌握情况</h2>
            <div className="space-y-4">
              {result.knowledgePoints.map((kp, index) => (
                <div key={index}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{kp.name}</span>
                    <span className="text-sm text-gray-600">
                      {kp.masteryLevel}%
                    </span>
                  </div>
                  <Progress value={kp.masteryLevel} className="h-2 mb-2" />
                  <p className="text-sm text-gray-600">{kp.suggestion}</p>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
```

**验收标准**:
- ✅ 能成功提交作业
- ✅ 能实时查看批改进度
- ✅ 能查看完整的批改结果
- ✅ 界面美观,交互流畅

---

#### Mock数据 (Day 9)
- [ ] 6.1 实现Mock数据工厂
- [ ] 6.2 实现Mock API服务
- [ ] 6.3 实现Mock WebSocket

##### Task 6.1: Mock API服务 (2小时)

创建 `frontend/services/api.ts`:
```typescript
import { v4 as uuidv4 } from 'uuid';

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Mock延迟
const mockDelay = (ms: number = 500) => new Promise(resolve => setTimeout(resolve, ms));

class GradingAPI {
  async submitGrading(data: { submissionId: string; mode: string }) {
    if (USE_MOCK) {
      await mockDelay();
      return {
        taskId: uuidv4(),
        status: 'pending',
        message: '批改任务已创建',
      };
    }

    const response = await fetch(`${API_BASE_URL}/grading/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    return response.json();
  }

  async getGradingStatus(taskId: string) {
    if (USE_MOCK) {
      await mockDelay(300);

      // 模拟进度
      const progress = Math.min(100, (Date.now() % 10000) / 100);
      const status = progress >= 100 ? 'completed' : 'processing';

      return {
        taskId,
        status,
        progress: Math.floor(progress),
        result: status === 'completed' ? {
          submissionId: uuidv4(),
        } : undefined,
      };
    }

    const response = await fetch(`${API_BASE_URL}/grading/status/${taskId}`);
    return response.json();
  }

  async getGradingResult(submissionId: string) {
    if (USE_MOCK) {
      await mockDelay();

      return {
        submissionId,
        score: 85.5,
        maxScore: 100,
        confidence: 0.92,
        errors: [
          {
            type: '计算错误',
            location: '第2题',
            description: '计算过程中符号错误',
            correctAnswer: '应该是 -3 而不是 3',
            severity: 'high',
            deduction: 5,
          },
        ],
        feedbackText: '整体完成良好,基础知识掌握扎实,但需要注意计算细节。',
        suggestions: [
          '加强符号运算练习',
          '做题时仔细检查',
          '建立错题本',
        ],
        knowledgePoints: [
          {
            name: '有理数运算',
            masteryLevel: 85,
            suggestion: '掌握较好,继续保持',
          },
        ],
        gradingMode: 'fast',
        processingTimeMs: 1250,
        fromCache: false,
      };
    }

    const response = await fetch(`${API_BASE_URL}/grading/result/${submissionId}`);
    return response.json();
  }
}

export const gradingAPI = new GradingAPI();
```

**验收标准**:
- ✅ Mock模式能正常工作
- ✅ 真实API能正常调用
- ✅ 错误处理完善

---

#### 集成测试 (Day 10)
- [ ] 7.1 前后端联调
- [ ] 7.2 端到端测试
- [ ] 7.3 性能测试
- [ ] 7.4 成本验证

##### Task 7.1: 端到端测试 (3小时)

创建 `tests/e2e/test_grading_flow.py`:
```python
import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_complete_grading_flow(client: AsyncClient):
    """测试完整的批改流程"""

    # 1. 创建作业
    assignment_data = {
        "title": "数学作业1",
        "max_score": 100,
        "grading_standard": {
            "criteria": "根据标准答案批改",
            "answer": "答案是42"
        }
    }
    response = await client.post("/api/v1/assignments", json=assignment_data)
    assert response.status_code == 200
    assignment_id = response.json()["id"]

    # 2. 创建提交
    submission_data = {
        "assignment_id": assignment_id,
        "files": [{"file_path": "test.txt", "file_type": "text"}]
    }
    response = await client.post("/api/v1/submissions", json=submission_data)
    assert response.status_code == 200
    submission_id = response.json()["id"]

    # 3. 提交批改
    grading_data = {
        "submission_id": submission_id,
        "mode": "fast"
    }
    response = await client.post("/api/v1/grading/submit", json=grading_data)
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # 4. 等待完成
    import asyncio
    for _ in range(30):  # 最多等待30秒
        await asyncio.sleep(1)
        response = await client.get(f"/api/v1/grading/status/{task_id}")
        status = response.json()

        if status["status"] == "completed":
            break

    assert status["status"] == "completed"

    # 5. 获取结果
    response = await client.get(f"/api/v1/grading/result/{submission_id}")
    assert response.status_code == 200
    result = response.json()

    assert "score" in result
    assert "errors" in result
    assert "feedback_text" in result
    assert result["grading_mode"] == "fast"

@pytest.mark.asyncio
async def test_cost_optimization(client: AsyncClient):
    """测试成本优化"""

    # 测试缓存命中
    submission_id = uuid4()

    # 第一次调用
    response1 = await client.post("/api/v1/grading/submit", json={
        "submission_id": submission_id,
        "mode": "fast"
    })

    # 第二次调用相同内容
    response2 = await client.post("/api/v1/grading/submit", json={
        "submission_id": submission_id,
        "mode": "fast"
    })

    # 验证第二次使用了缓存
    result2 = response2.json()
    assert result2.get("from_cache") == True
```

##### Task 7.2: 成本验证 (2小时)

创建 `scripts/cost_analyzer.py`:
```python
import asyncio
from app.agents.smart_orchestrator import SmartOrchestrator
from app.core.config import settings

async def analyze_cost():
    """分析批改成本"""

    orchestrator = SmartOrchestrator()

    # 测试不同模式的成本
    test_cases = [
        {"mode": "fast", "complexity": "simple", "expected_cost": 0.008},
        {"mode": "standard", "complexity": "medium", "expected_cost": 0.010},
        {"mode": "premium", "complexity": "complex", "expected_cost": 0.015},
    ]

    results = []

    for case in test_cases:
        # 执行批改
        result = await orchestrator.execute({
            "submission_id": "test",
            "mode": case["mode"],
            "config": {"complexity": case["complexity"]}
        })

        # 计算实际成本
        actual_cost = calculate_cost(result)

        results.append({
            "mode": case["mode"],
            "expected": case["expected_cost"],
            "actual": actual_cost,
            "diff": actual_cost - case["expected_cost"]
        })

    # 打印结果
    print("\n成本分析报告:")
    print("-" * 60)
    for r in results:
        print(f"模式: {r['mode']}")
        print(f"  预期成本: ${r['expected']:.4f}")
        print(f"  实际成本: ${r['actual']:.4f}")
        print(f"  差异: ${r['diff']:.4f}")
        print()

    # 计算平均成本
    avg_cost = sum(r["actual"] for r in results) / len(results)
    print(f"平均成本: ${avg_cost:.4f}")
    print(f"目标成本: $0.009")
    print(f"节省比例: {(1 - avg_cost / 0.015) * 100:.1f}%")

def calculate_cost(result):
    """计算批改成本"""
    # 基于token数量估算
    # 假设: 1K tokens = $0.001
    tokens = len(result.get("extracted_text", "")) / 4  # 粗略估算
    return tokens / 1000 * 0.001

if __name__ == "__main__":
    asyncio.run(analyze_cost())
```

**验收标准**:
- ✅ 端到端测试通过
- ✅ 平均成本 < $0.009
- ✅ 缓存命中率 > 20%
- ✅ 批改时间 < 15秒

---

## 🎯 验收标准

### 功能验收
- [ ] 能成功提交作业并获得批改结果
- [ ] 批改结果包含分数、错误、反馈、建议
- [ ] 支持快速/标准/完整三种模式
- [ ] 缓存命中率 > 20%

### 性能验收
- [ ] 单份批改时间 < 15秒
- [ ] API响应时间 < 500ms
- [ ] 并发10个请求无错误

### 成本验收
- [ ] 快速模式成本 < $0.008
- [ ] 标准模式成本 < $0.010
- [ ] 完整模式成本 < $0.015
- [ ] 平均成本 < $0.009 (节省40%)

---

## 📊 进度跟踪

使用以下命令查看进度:
```bash
# 查看任务完成情况
grep -c "✅" docs/10_PHASE1_IMPLEMENTATION_PLAN.md

# 运行测试
pytest tests/ -v

# 检查成本
python scripts/cost_analyzer.py
```

---

## 🚀 快速启动指南

### 第一天开始前的准备

#### 1. 确认环境要求
```bash
# Python版本
python --version  # 需要 3.11+

# Node.js版本
node --version    # 需要 18+

# 数据库
psql --version    # PostgreSQL 15+

# Redis
redis-cli --version  # Redis 7+
```

#### 2. 克隆项目并安装依赖

**后端**:
```bash
cd new_aicorrection/backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 如果requirements.txt不完整,手动安装:
pip install fastapi uvicorn sqlalchemy alembic
pip install langchain langgraph langchain-openai
pip install redis asyncpg python-multipart
pip install pydantic pydantic-settings python-jose
pip install pytest pytest-asyncio httpx faker
```

**前端**:
```bash
cd new_aicorrection/frontend

# 安装依赖
npm install
# 或
pnpm install
```

#### 3. 配置环境变量

创建 `backend/.env`:
```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/aigrading

# Redis
REDIS_URL=redis://localhost:6379/0

# AI API
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=google/gemini-2.0-flash-exp:free

# 成本优化
ENABLE_UNIFIED_AGENT=true
ENABLE_SMART_CACHE=true
CACHE_SIMILARITY_THRESHOLD=0.85
DEFAULT_GRADING_MODE=fast

# 开发模式
DEBUG=true
```

创建 `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_USE_MOCK=false
```

#### 4. 初始化数据库
```bash
cd backend

# 创建数据库
createdb aigrading

# 运行迁移
alembic upgrade head

# 创建测试数据(可选)
python scripts/seed_data.py
```

#### 5. 启动服务

**后端**:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**前端**:
```bash
cd frontend
npm run dev
# 或
pnpm dev
```

**Redis** (如果未运行):
```bash
redis-server
```

#### 6. 验证安装
```bash
# 测试后端API
curl http://localhost:8000/api/v1/health

# 测试前端
open http://localhost:3000

# 运行测试
cd backend
pytest tests/ -v
```

---

## ✅ 每日检查清单

### Day 1 检查清单
- [ ] Python 3.11+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] PostgreSQL 15+ 已安装并运行
- [ ] Redis 7+ 已安装并运行
- [ ] 虚拟环境已创建
- [ ] 后端依赖已安装
- [ ] 前端依赖已安装
- [ ] 环境变量已配置
- [ ] 数据库已创建
- [ ] 数据库迁移已执行
- [ ] 后端服务能启动
- [ ] 前端服务能启动
- [ ] API健康检查通过

### Day 2 检查清单
- [ ] 数据库模型已创建
- [ ] Assignment表已创建
- [ ] Submission表已创建
- [ ] GradingResult表已创建
- [ ] 表关系正确
- [ ] 能成功插入测试数据
- [ ] 能成功查询数据

### Day 3 检查清单
- [ ] GradingState已定义
- [ ] UnifiedGradingAgent已实现
- [ ] 能成功调用OpenRouter API
- [ ] 能正确解析JSON响应
- [ ] 单元测试已编写
- [ ] 单元测试通过
- [ ] 单次调用成本 < $0.012

### Day 4 检查清单
- [ ] PreprocessAgent已实现
- [ ] 支持图片文件处理
- [ ] 支持PDF文件处理
- [ ] OCR集成完成
- [ ] 文本提取正确
- [ ] 数据验证完善

### Day 5 检查清单
- [ ] ComplexityAssessor已实现
- [ ] 复杂度评估准确
- [ ] SmartOrchestrator已实现
- [ ] LangGraph工作流正确
- [ ] 能根据复杂度选择模式

### Day 6 检查清单
- [ ] CacheService已实现
- [ ] Redis连接正常
- [ ] 能成功存储缓存
- [ ] 能成功读取缓存
- [ ] 相似度计算正确
- [ ] 缓存命中率 > 20%

### Day 7 检查清单
- [ ] 批改API已实现
- [ ] 状态查询API已实现
- [ ] 结果查询API已实现
- [ ] API文档自动生成
- [ ] Postman测试通过
- [ ] 错误处理完善

### Day 8 检查清单
- [ ] 作业提交页面已创建
- [ ] 批改进度页面已创建
- [ ] 结果展示页面已创建
- [ ] 页面样式美观
- [ ] 交互流畅
- [ ] 响应式设计

### Day 9 检查清单
- [ ] Mock数据工厂已实现
- [ ] Mock API已实现
- [ ] Mock模式能正常工作
- [ ] 真实API能正常调用
- [ ] 前端能独立开发

### Day 10 检查清单
- [ ] 前后端联调成功
- [ ] 端到端测试通过
- [ ] 性能测试通过
- [ ] 成本验证通过
- [ ] 平均成本 < $0.009
- [ ] 批改时间 < 15秒
- [ ] 所有功能正常

---

## 🎯 最终验收清单

### 功能验收
- [ ] ✅ 能成功提交作业
- [ ] ✅ 能实时查看批改进度
- [ ] ✅ 能查看完整的批改结果
- [ ] ✅ 支持快速/标准/完整三种模式
- [ ] ✅ 缓存功能正常工作
- [ ] ✅ 错误处理完善
- [ ] ✅ 日志记录完整

### 性能验收
- [ ] ✅ 单份批改时间 < 15秒
- [ ] ✅ API响应时间 < 500ms (P95)
- [ ] ✅ 并发10个请求无错误
- [ ] ✅ 缓存命中率 > 20%
- [ ] ✅ 数据库查询优化

### 成本验收
- [ ] ✅ 快速模式成本 < $0.008
- [ ] ✅ 标准模式成本 < $0.010
- [ ] ✅ 完整模式成本 < $0.015
- [ ] ✅ 平均成本 < $0.009
- [ ] ✅ 相比原设计节省 40%+

### 代码质量
- [ ] ✅ 代码符合PEP 8规范
- [ ] ✅ 类型注解完整
- [ ] ✅ 文档字符串完整
- [ ] ✅ 单元测试覆盖率 > 80%
- [ ] ✅ 集成测试通过
- [ ] ✅ 无严重的代码异味

### 文档完整性
- [ ] ✅ API文档完整
- [ ] ✅ 部署文档完整
- [ ] ✅ 用户手册完整
- [ ] ✅ 开发文档完整

---

## 📞 遇到问题?

### 常见问题

**Q1: OpenRouter API调用失败**
```bash
# 检查API Key
echo $OPENROUTER_API_KEY

# 测试API连接
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models
```

**Q2: 数据库连接失败**
```bash
# 检查PostgreSQL是否运行
pg_isready

# 检查连接字符串
psql $DATABASE_URL
```

**Q3: Redis连接失败**
```bash
# 检查Redis是否运行
redis-cli ping

# 应该返回: PONG
```

**Q4: 前端无法连接后端**
```bash
# 检查后端是否运行
curl http://localhost:8000/api/v1/health

# 检查CORS配置
# 在 backend/app/main.py 中确认:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Q5: 成本超出预期**
```bash
# 运行成本分析
python scripts/cost_analyzer.py

# 检查是否启用了优化
echo $ENABLE_UNIFIED_AGENT
echo $ENABLE_SMART_CACHE

# 查看缓存命中率
redis-cli INFO stats | grep keyspace_hits
```

### 获取帮助

- 📖 查看文档: `docs/`
- 🐛 提交Issue: GitHub Issues
- 💬 讨论: GitHub Discussions
- 📧 联系: [项目邮箱]

---

## 🎉 完成阶段一后

恭喜完成阶段一!接下来:

1. **代码审查**: 组织团队进行代码审查
2. **性能优化**: 根据测试结果进行优化
3. **用户测试**: 邀请真实用户测试
4. **准备阶段二**: 开始规划批量批改、审核机制等功能

**阶段二预览**:
- 批量批改功能
- ReviewAgent实现
- FeedbackAgent优化
- 学习分析功能
- 性能进一步优化

---

**祝您实施顺利!** 🚀

如有任何问题,请随时查阅文档或寻求帮助。

