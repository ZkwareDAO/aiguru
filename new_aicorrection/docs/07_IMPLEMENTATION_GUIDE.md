# 实现指南

## 📌 文档概述

本文档提供基于设计文档的具体实现指南,包括代码示例、最佳实践和常见问题解决方案。

---

## 1. LangGraph Agent实现

### 1.1 环境准备

```bash
# 安装依赖
pip install langchain langgraph langchain-openai
pip install fastapi uvicorn sqlalchemy asyncpg redis

# 或使用项目的requirements.txt
pip install -r backend/requirements.txt
```

### 1.2 基础Agent实现

**Step 1: 定义状态**

```python
# backend/app/agents/state.py
from typing import TypedDict, List, Dict, Optional, Annotated
from datetime import datetime
from uuid import UUID
from langgraph.graph import add_messages

class GradingState(TypedDict):
    """批改流程的共享状态"""
    
    # 基础信息
    submission_id: UUID
    assignment_id: UUID
    student_id: UUID
    
    # 处理状态
    status: str  # pending, preprocessing, grading, reviewing, completed, failed
    current_step: str
    progress: float  # 0-100
    
    # 消息历史
    messages: Annotated[List[Dict], add_messages]
    
    # 预处理结果
    preprocessed_files: Optional[List[Dict]]
    extracted_text: Optional[str]
    file_metadata: Optional[Dict]
    
    # 批改结果
    score: Optional[float]
    max_score: float
    errors: Optional[List[Dict]]
    annotations: Optional[List[Dict]]
    confidence: Optional[float]
    
    # 审核结果
    review_passed: Optional[bool]
    review_comments: Optional[str]
    adjusted_score: Optional[float]
    
    # 反馈结果
    feedback_text: Optional[str]
    suggestions: Optional[List[str]]
    knowledge_points: Optional[List[str]]
    
    # 配置
    config: Dict
    
    # 元数据
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str]
```

**Step 2: 实现PreprocessAgent**

```python
# backend/app/agents/preprocess_agent.py
import logging
from typing import Dict, List
from pathlib import Path

from app.agents.state import GradingState
from app.services.file_service import FileService
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)


class PreprocessAgent:
    """预处理Agent - 负责文件解析、OCR识别、数据验证"""
    
    def __init__(self):
        self.file_service = FileService()
        self.ocr_service = OCRService()
        self.name = "PreprocessAgent"
    
    async def process(self, state: GradingState) -> GradingState:
        """执行预处理流程"""
        logger.info(f"[{self.name}] Starting preprocessing for submission {state['submission_id']}")
        
        try:
            # 更新状态
            state["status"] = "preprocessing"
            state["current_step"] = "preprocess"
            state["messages"].append({
                "agent": self.name,
                "action": "started",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 1. 获取文件
            files = await self.file_service.get_submission_files(state["submission_id"])
            logger.info(f"[{self.name}] Found {len(files)} files")
            
            # 2. 处理每个文件
            preprocessed_files = []
            all_text = []
            
            for file in files:
                file_result = await self._process_file(file)
                preprocessed_files.append(file_result)
                
                if file_result.get("text"):
                    all_text.append(file_result["text"])
            
            # 3. 合并文本
            extracted_text = "\n\n".join(all_text)
            
            # 4. 数据验证
            validation_result = self._validate_data(extracted_text, preprocessed_files)
            
            if not validation_result["is_valid"]:
                state["status"] = "failed"
                state["error_message"] = validation_result["error"]
                logger.error(f"[{self.name}] Validation failed: {validation_result['error']}")
                return state
            
            # 5. 更新状态
            state["preprocessed_files"] = preprocessed_files
            state["extracted_text"] = extracted_text
            state["file_metadata"] = {
                "file_count": len(files),
                "total_text_length": len(extracted_text),
                "file_types": [f["type"] for f in preprocessed_files]
            }
            state["status"] = "preprocessed"
            state["progress"] = 25.0
            
            state["messages"].append({
                "agent": self.name,
                "action": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "files_processed": len(preprocessed_files),
                    "text_length": len(extracted_text)
                }
            })
            
            logger.info(f"[{self.name}] Preprocessing completed successfully")
            return state
            
        except Exception as e:
            logger.error(f"[{self.name}] Error during preprocessing: {e}", exc_info=True)
            state["status"] = "failed"
            state["error_message"] = str(e)
            return state
    
    async def _process_file(self, file: Dict) -> Dict:
        """处理单个文件"""
        file_type = file["type"]
        
        if file_type.startswith("image/"):
            return await self._process_image(file)
        elif file_type == "application/pdf":
            return await self._process_pdf(file)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    async def _process_image(self, file: Dict) -> Dict:
        """处理图片文件"""
        # OCR识别
        ocr_result = await self.ocr_service.recognize(file["path"])
        
        return {
            "file_id": file["id"],
            "type": "image",
            "path": file["path"],
            "text": ocr_result["text"],
            "confidence": ocr_result["confidence"],
            "metadata": {
                "width": ocr_result.get("width"),
                "height": ocr_result.get("height")
            }
        }
    
    async def _process_pdf(self, file: Dict) -> Dict:
        """处理PDF文件"""
        # 提取文本
        text = await self.file_service.extract_pdf_text(file["path"])
        
        return {
            "file_id": file["id"],
            "type": "pdf",
            "path": file["path"],
            "text": text,
            "metadata": {
                "page_count": await self.file_service.get_pdf_page_count(file["path"])
            }
        }
    
    def _validate_data(self, text: str, files: List[Dict]) -> Dict:
        """验证数据"""
        if not text or len(text.strip()) < 10:
            return {
                "is_valid": False,
                "error": "提取的文本内容过少,请检查文件质量"
            }
        
        if not files:
            return {
                "is_valid": False,
                "error": "没有找到可处理的文件"
            }
        
        return {"is_valid": True}
```

**Step 3: 实现GradingAgent**

```python
# backend/app/agents/grading_agent.py
import logging
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.agents.state import GradingState
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GradingAgent:
    """批改Agent - 负责核心批改逻辑"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4-turbo-preview",
            temperature=0.3
        )
        self.name = "GradingAgent"
    
    async def process(self, state: GradingState) -> GradingState:
        """执行批改流程"""
        logger.info(f"[{self.name}] Starting grading for submission {state['submission_id']}")
        
        try:
            state["status"] = "grading"
            state["current_step"] = "grade"
            state["messages"].append({
                "agent": self.name,
                "action": "started",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 1. 获取批改标准
            assignment = await self._get_assignment(state["assignment_id"])
            grading_standard = assignment["grading_standard"]
            
            # 2. 构建批改提示词
            prompt = self._build_grading_prompt(
                student_answer=state["extracted_text"],
                grading_standard=grading_standard,
                config=state["config"]
            )
            
            # 3. 调用LLM进行批改
            logger.info(f"[{self.name}] Calling LLM for grading")
            response = await self.llm.ainvoke(prompt)
            
            # 4. 解析批改结果
            grading_result = self._parse_grading_result(response.content)
            
            # 5. 更新状态
            state["score"] = grading_result["score"]
            state["max_score"] = assignment["max_score"]
            state["errors"] = grading_result["errors"]
            state["confidence"] = grading_result["confidence"]
            state["status"] = "graded"
            state["progress"] = 60.0
            
            state["messages"].append({
                "agent": self.name,
                "action": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "result": {
                    "score": grading_result["score"],
                    "error_count": len(grading_result["errors"]),
                    "confidence": grading_result["confidence"]
                }
            })
            
            logger.info(f"[{self.name}] Grading completed: score={grading_result['score']}")
            return state
            
        except Exception as e:
            logger.error(f"[{self.name}] Error during grading: {e}", exc_info=True)
            state["status"] = "failed"
            state["error_message"] = str(e)
            return state
    
    def _build_grading_prompt(
        self,
        student_answer: str,
        grading_standard: Dict,
        config: Dict
    ) -> str:
        """构建批改提示词"""
        strictness = config.get("strictness", "standard")
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的教师,正在批改学生作业。
请严格按照评分标准进行批改,找出学生答案中的错误,并给出详细的反馈。

评分严格程度: {strictness}
- loose: 宽松,注重鼓励
- standard: 标准,客观公正
- strict: 严格,要求精确

请以JSON格式输出批改结果。"""),
            ("user", """
【批改标准】
{criteria}

【标准答案】
{answer}

【学生答案】
{student_answer}

请输出JSON格式的批改结果,包含以下字段:
{{
    "score": 分数(0-100),
    "confidence": 置信度(0-1),
    "errors": [
        {{
            "type": "错误类型",
            "location": "错误位置",
            "description": "错误说明",
            "correct_answer": "正确答案",
            "severity": "high|medium|low",
            "deduction": 扣分
        }}
    ],
    "overall_comment": "总体评价",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"]
}}
""")
        ])
        
        return prompt_template.format_messages(
            strictness=strictness,
            criteria=grading_standard["criteria"],
            answer=grading_standard["answer"],
            student_answer=student_answer
        )
    
    def _parse_grading_result(self, response: str) -> Dict:
        """解析批改结果"""
        import json
        
        try:
            # 提取JSON部分
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            json_str = response[start_idx:end_idx]
            
            result = json.loads(json_str)
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse grading result: {e}")
            # 返回默认结果
            return {
                "score": 0,
                "confidence": 0.5,
                "errors": [],
                "overall_comment": "批改结果解析失败",
                "strengths": [],
                "weaknesses": []
            }
    
    async def _get_assignment(self, assignment_id: UUID) -> Dict:
        """获取作业信息"""
        from app.services.assignment_service import AssignmentService
        from app.core.database import get_db_session
        
        async with get_db_session() as db:
            service = AssignmentService(db)
            assignment = await service.get_assignment(assignment_id)
            return assignment
```

**Step 4: 实现Orchestrator**

```python
# backend/app/agents/orchestrator.py
import logging
from typing import Dict
from langgraph.graph import StateGraph, END

from app.agents.state import GradingState
from app.agents.preprocess_agent import PreprocessAgent
from app.agents.grading_agent import GradingAgent
from app.agents.review_agent import ReviewAgent
from app.agents.feedback_agent import FeedbackAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """编排器Agent - 负责整体流程控制"""
    
    def __init__(self):
        self.preprocess_agent = PreprocessAgent()
        self.grading_agent = GradingAgent()
        self.review_agent = ReviewAgent()
        self.feedback_agent = FeedbackAgent()
        
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """构建LangGraph工作流"""
        workflow = StateGraph(GradingState)
        
        # 添加节点
        workflow.add_node("preprocess", self.preprocess_agent.process)
        workflow.add_node("grade", self.grading_agent.process)
        workflow.add_node("review", self.review_agent.process)
        workflow.add_node("feedback", self.feedback_agent.process)
        
        # 定义流程
        workflow.set_entry_point("preprocess")
        
        # 预处理 -> 批改
        workflow.add_conditional_edges(
            "preprocess",
            self._check_preprocess_status,
            {
                "continue": "grade",
                "failed": END
            }
        )
        
        # 批改 -> 审核或反馈
        workflow.add_conditional_edges(
            "grade",
            self._should_review,
            {
                "review": "review",
                "feedback": "feedback",
                "failed": END
            }
        )
        
        # 审核 -> 反馈
        workflow.add_conditional_edges(
            "review",
            self._check_review_status,
            {
                "continue": "feedback",
                "failed": END
            }
        )
        
        # 反馈 -> 结束
        workflow.add_edge("feedback", END)
        
        return workflow.compile()
    
    def _check_preprocess_status(self, state: GradingState) -> str:
        """检查预处理状态"""
        if state["status"] == "failed":
            return "failed"
        return "continue"
    
    def _should_review(self, state: GradingState) -> str:
        """决定是否需要审核"""
        if state["status"] == "failed":
            return "failed"
        
        # 如果配置启用审核且置信度较低,则进行审核
        if state["config"].get("enable_review") and state.get("confidence", 1.0) < 0.8:
            return "review"
        
        return "feedback"
    
    def _check_review_status(self, state: GradingState) -> str:
        """检查审核状态"""
        if state["status"] == "failed":
            return "failed"
        return "continue"
    
    async def execute(self, input_data: Dict) -> Dict:
        """执行批改流程"""
        logger.info(f"[Orchestrator] Starting grading workflow for submission {input_data['submission_id']}")
        
        # 初始化状态
        initial_state = GradingState(
            submission_id=input_data["submission_id"],
            assignment_id=input_data["assignment_id"],
            student_id=input_data["student_id"],
            status="pending",
            current_step="",
            progress=0.0,
            messages=[],
            preprocessed_files=None,
            extracted_text=None,
            file_metadata=None,
            score=None,
            max_score=100,
            errors=None,
            annotations=None,
            confidence=None,
            review_passed=None,
            review_comments=None,
            adjusted_score=None,
            feedback_text=None,
            suggestions=None,
            knowledge_points=None,
            config=input_data.get("config", {}),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            error_message=None
        )
        
        # 执行工作流
        result = await self.workflow.ainvoke(initial_state)
        
        logger.info(f"[Orchestrator] Workflow completed with status: {result['status']}")
        return result
```

---

## 2. API集成

```python
# backend/app/api/grading.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.agents.orchestrator import OrchestratorAgent
from app.schemas.grading import GradingRequest, GradingResponse

router = APIRouter(prefix="/api/v1/grading", tags=["grading"])


@router.post("/submit", response_model=GradingResponse)
async def submit_grading(
    request: GradingRequest,
    db: AsyncSession = Depends(get_db)
):
    """提交批改请求"""
    try:
        # 创建Orchestrator
        orchestrator = OrchestratorAgent()
        
        # 执行批改
        result = await orchestrator.execute({
            "submission_id": request.submission_id,
            "assignment_id": request.assignment_id,
            "student_id": request.student_id,
            "config": {
                "strictness": request.strictness,
                "enable_review": request.enable_review,
                "enable_analytics": request.enable_analytics
            }
        })
        
        return GradingResponse(
            success=result["status"] == "completed",
            submission_id=result["submission_id"],
            score=result.get("score"),
            feedback=result.get("feedback_text"),
            errors=result.get("errors", []),
            processing_time=result.get("processing_time")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

**继续阅读**: 查看其他设计文档了解更多实现细节

