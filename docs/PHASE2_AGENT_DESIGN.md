# 🤖 Phase 2 Agent系统详细设计

**Multi-Agent协作架构设计文档**

---

## 📋 目录

1. [架构概览](#架构概览)
2. [Agent 1: PreprocessAgent](#agent-1-preprocessagent)
3. [Agent 2: UnifiedGradingAgent](#agent-2-unifiedgradingagent)
4. [Agent 3: LocationAnnotationAgent](#agent-3-locationannotationagent)
5. [GradingOrchestrator](#gradingorchestrator)
6. [数据流](#数据流)
7. [错误处理](#错误处理)
8. [性能优化](#性能优化)

---

## 架构概览

### Multi-Agent协作流程

```
用户提交作业
    ↓
┌─────────────────────────────────────────┐
│      GradingOrchestrator (LangGraph)    │
└─────────────────────────────────────────┘
    │
    ├─→ [Agent 1] PreprocessAgent
    │   输入: 作业图片
    │   输出: 题目列表 + 边界框
    │   技术: Tesseract OCR
    │   成本: $0.001/页
    │
    ├─→ [Agent 2] UnifiedGradingAgent
    │   输入: 题目截图
    │   输出: 分数 + 错误 + 反馈
    │   技术: Gemini 2.5 Flash Lite
    │   成本: $0.000043/题
    │
    └─→ [Agent 3] LocationAnnotationAgent ⭐ 新增
        输入: 题目图片 + 错误描述
        输出: 精确像素坐标 + 置信度
        技术: Gemini 2.5 Flash Lite
        成本: $0.000001/题
    ↓
保存到数据库 + WebSocket推送
```

### LangGraph状态机

```python
from langgraph.graph import StateGraph

# 状态定义
class GradingState(TypedDict):
    submission_id: str
    images: List[str]
    
    # Agent 1 输出
    question_segments: Optional[List[QuestionSegment]]
    
    # Agent 2 输出
    grading_results: Optional[List[QuestionGrading]]
    
    # Agent 3 输出
    annotated_results: Optional[List[AnnotatedGrading]]
    
    # 最终结果
    final_result: Optional[GradingResult]
    
    # 错误信息
    error: Optional[str]

# 工作流定义
workflow = StateGraph(GradingState)

# 添加节点
workflow.add_node("preprocess", preprocess_node)
workflow.add_node("grade", grade_node)
workflow.add_node("annotate", annotate_node)
workflow.add_node("finalize", finalize_node)

# 定义流程
workflow.add_edge("__start__", "preprocess")
workflow.add_edge("preprocess", "grade")
workflow.add_edge("grade", "annotate")
workflow.add_edge("annotate", "finalize")
workflow.add_edge("finalize", "__end__")

# 编译
graph = workflow.compile()
```

---

## Agent 1: PreprocessAgent

### 职责

**题目分段识别** - 将作业图片分割成独立的题目

### 输入

```python
class PreprocessInput(BaseModel):
    images: List[str]  # 图片URL列表
    image_metadata: List[ImageMetadata]  # 图片元数据
```

### 输出

```python
class QuestionSegment(BaseModel):
    question_number: str        # "第1题" 或 "1." 或 "(1)"
    question_index: int         # 0-based索引
    page_index: int             # 所在页面索引
    bbox: BoundingBox           # 题目边界框
    cropped_image: str          # 题目截图URL
    ocr_text: str               # OCR识别的文字
    confidence: float           # 识别置信度 (0-1)
```

### 实现方案

#### 1. OCR识别

```python
class PreprocessAgent:
    def __init__(self):
        self.ocr_engine = TesseractOCR(lang='chi_sim+eng')
    
    async def recognize_text(self, image_url: str) -> OCRResult:
        """OCR文字识别"""
        image = await self._load_image(image_url)
        
        # 预处理图片
        processed_image = self._preprocess_image(image)
        
        # OCR识别
        result = self.ocr_engine.image_to_data(
            processed_image,
            output_type=pytesseract.Output.DICT
        )
        
        return OCRResult(
            text=result['text'],
            boxes=result['boxes'],
            confidences=result['conf']
        )
    
    def _preprocess_image(self, image):
        """图片预处理"""
        # 1. 灰度化
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 2. 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 3. 去噪
        denoised = cv2.fastNlMeansDenoising(binary)
        
        return denoised
```

#### 2. 题号识别

```python
def _detect_question_markers(self, ocr_result: OCRResult) -> List[QuestionMarker]:
    """识别题号"""
    markers = []
    
    # 正则表达式匹配题号
    patterns = [
        r'^(\d+)[.、)]',           # 1. 或 1、 或 1)
        r'^[(（](\d+)[)）]',       # (1) 或 （1）
        r'^第(\d+)题',             # 第1题
        r'^[一二三四五六七八九十]+[.、)]',  # 一、 或 二、
    ]
    
    for i, text in enumerate(ocr_result.text):
        for pattern in patterns:
            match = re.match(pattern, text.strip())
            if match:
                markers.append(QuestionMarker(
                    text=text,
                    number=self._extract_number(match),
                    bbox=ocr_result.boxes[i],
                    confidence=ocr_result.confidences[i]
                ))
                break
    
    return markers
```

#### 3. 边界框计算

```python
def _calculate_bbox(
    self,
    marker: QuestionMarker,
    next_marker: Optional[QuestionMarker],
    ocr_result: OCRResult,
    image_height: int
) -> BoundingBox:
    """计算题目边界框"""
    
    # 起始位置: 题号的y坐标
    start_y = marker.bbox.y
    
    # 结束位置: 下一个题号的y坐标 或 图片底部
    if next_marker:
        end_y = next_marker.bbox.y
    else:
        end_y = image_height
    
    # 左右边界: 整个图片宽度
    start_x = 0
    end_x = ocr_result.image_width
    
    # 添加边距
    padding = 10
    
    return BoundingBox(
        x=max(0, start_x - padding),
        y=max(0, start_y - padding),
        width=min(end_x + padding, ocr_result.image_width) - start_x,
        height=end_y - start_y + padding
    )
```

#### 4. 题目截图

```python
async def _crop_question(
    self,
    image_url: str,
    bbox: BoundingBox
) -> str:
    """截取题目图片"""
    image = await self._load_image(image_url)
    
    # 裁剪
    cropped = image[
        bbox.y:bbox.y + bbox.height,
        bbox.x:bbox.x + bbox.width
    ]
    
    # 保存到云存储
    cropped_url = await self.storage.upload(cropped, f"questions/{uuid4()}.jpg")
    
    return cropped_url
```

### 完整流程

```python
async def segment_questions(
    self,
    images: List[str]
) -> List[QuestionSegment]:
    """题目分段识别"""
    segments = []
    question_index = 0
    
    for page_index, image_url in enumerate(images):
        # 1. OCR识别
        ocr_result = await self.recognize_text(image_url)
        
        # 2. 识别题号
        markers = self._detect_question_markers(ocr_result)
        
        # 3. 计算边界框和截图
        for i, marker in enumerate(markers):
            next_marker = markers[i + 1] if i + 1 < len(markers) else None
            
            bbox = self._calculate_bbox(
                marker,
                next_marker,
                ocr_result,
                ocr_result.image_height
            )
            
            cropped_image = await self._crop_question(image_url, bbox)
            
            ocr_text = self._extract_text_in_bbox(ocr_result, bbox)
            
            segments.append(QuestionSegment(
                question_number=marker.text,
                question_index=question_index,
                page_index=page_index,
                bbox=bbox,
                cropped_image=cropped_image,
                ocr_text=ocr_text,
                confidence=marker.confidence
            ))
            
            question_index += 1
    
    return segments
```

### 性能优化

1. **并行处理**: 多页图片并行OCR
2. **缓存OCR结果**: 避免重复识别
3. **图片预处理**: 提高OCR准确度
4. **批量上传**: 批量上传截图到云存储

### 错误处理

```python
async def segment_questions_with_fallback(
    self,
    images: List[str]
) -> List[QuestionSegment]:
    """带兜底的题目分段"""
    try:
        segments = await self.segment_questions(images)
        
        # 验证结果
        if len(segments) == 0:
            raise ValueError("未识别到任何题目")
        
        # 检查置信度
        low_confidence = [s for s in segments if s.confidence < 0.5]
        if len(low_confidence) > len(segments) * 0.3:
            logger.warning(f"低置信度题目过多: {len(low_confidence)}/{len(segments)}")
        
        return segments
        
    except Exception as e:
        logger.error(f"题目分段失败: {e}")
        
        # 兜底方案: 将整页作为一个题目
        return self._fallback_segment(images)
```

---

## Agent 2: UnifiedGradingAgent

### 职责

**批改识别** - 识别错误、计算分数、生成反馈

### 输入

```python
class GradingInput(BaseModel):
    question_segment: QuestionSegment
    standard_answer: Optional[str]
    rubric: Optional[Dict]
```

### 输出

```python
class QuestionGrading(BaseModel):
    question_index: int
    score: float
    max_score: float
    status: str  # "correct" | "warning" | "error"
    
    errors: List[ErrorItem]
    correct_parts: List[CorrectItem]
    warnings: List[WarningItem]
    
    feedback: str
```

### 实现

详见Phase 1文档，这里不再重复。

---

## Agent 3: LocationAnnotationAgent

### 职责

**精确位置标注** - 在图片中精确定位错误位置

### 输入

```python
class LocationInput(BaseModel):
    image_url: str
    image_width: int
    image_height: int
    question_bbox: BoundingBox
    error: ErrorItem
```

### 输出

```python
class LocationOutput(BaseModel):
    bbox: BoundingBox
    type: str  # "point" | "line" | "area"
    confidence: float  # 0-1
    reasoning: str
```

### Prompt设计

```python
LOCATION_PROMPT_TEMPLATE = """
你是一个专业的位置标注专家。你的任务是在学生作业图片中精确定位错误位置。

## 图片信息
- 图片尺寸: {width}px × {height}px
- 题目区域: x={bbox_x}, y={bbox_y}, width={bbox_width}, height={bbox_height}

## 错误信息
- 错误类型: {error_type}
- 错误描述: {error_description}
- 相关文字: {related_text}

## 任务要求
请仔细观察图片，找到错误所在的位置，并返回JSON格式:

{{
  "bbox": {{
    "x": 150,        // 左上角x坐标 (像素，相对于整张图片)
    "y": 200,        // 左上角y坐标 (像素，相对于整张图片)
    "width": 200,    // 宽度 (像素)
    "height": 50     // 高度 (像素)
  }},
  "type": "area",    // 标注类型: point(点), line(线), area(区域)
  "confidence": 0.95, // 置信度 (0-1)
  "reasoning": "错误位于第二行的计算结果部分，x+2y=8的求解过程中，x的系数计算错误"
}}

## 定位要求
1. 坐标必须是相对于整张图片的绝对像素坐标
2. bbox应该紧密包围错误内容，不要过大或过小
3. 如果无法准确定位，confidence设为0.5以下
4. reasoning必须详细说明定位依据，包括错误在第几行、第几步等

## 注意事项
- 只返回JSON，不要有其他文字
- 确保坐标在图片范围内
- 确保bbox在题目区域内或附近
"""
```

### 实现

```python
class LocationAnnotationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="google/gemini-2.5-flash-lite",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.1,  # 低温度，提高准确性
        )
    
    async def annotate(
        self,
        input: LocationInput
    ) -> LocationOutput:
        """精确位置标注"""
        
        # 1. 构建Prompt
        prompt = self._build_prompt(input)
        
        # 2. 调用LLM
        response = await self.llm.ainvoke([
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": input.image_url
                    }
                }
            ])
        ])
        
        # 3. 解析响应
        result = self._parse_response(response.content)
        
        # 4. 验证结果
        validated_result = self._validate_result(result, input)
        
        # 5. 兜底处理
        if validated_result.confidence < 0.5:
            validated_result = self._get_fallback_location(input)
        
        return validated_result
    
    def _build_prompt(self, input: LocationInput) -> str:
        """构建Prompt"""
        return LOCATION_PROMPT_TEMPLATE.format(
            width=input.image_width,
            height=input.image_height,
            bbox_x=input.question_bbox.x,
            bbox_y=input.question_bbox.y,
            bbox_width=input.question_bbox.width,
            bbox_height=input.question_bbox.height,
            error_type=input.error.type,
            error_description=input.error.description,
            related_text=input.error.related_text or "无"
        )
    
    def _parse_response(self, content: str) -> LocationOutput:
        """解析LLM响应"""
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                raise ValueError("未找到JSON")
            
            data = json.loads(json_match.group())
            
            return LocationOutput(
                bbox=BoundingBox(**data['bbox']),
                type=data['type'],
                confidence=data['confidence'],
                reasoning=data['reasoning']
            )
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            raise
    
    def _validate_result(
        self,
        result: LocationOutput,
        input: LocationInput
    ) -> LocationOutput:
        """验证结果"""
        
        # 1. 检查坐标是否在图片范围内
        if (result.bbox.x < 0 or
            result.bbox.y < 0 or
            result.bbox.x + result.bbox.width > input.image_width or
            result.bbox.y + result.bbox.height > input.image_height):
            logger.warning("坐标超出图片范围，降低置信度")
            result.confidence *= 0.5
        
        # 2. 检查是否在题目区域附近
        question_center_y = input.question_bbox.y + input.question_bbox.height / 2
        result_center_y = result.bbox.y + result.bbox.height / 2
        
        distance = abs(result_center_y - question_center_y)
        if distance > input.question_bbox.height:
            logger.warning("位置距离题目区域较远，降低置信度")
            result.confidence *= 0.7
        
        return result
    
    def _get_fallback_location(
        self,
        input: LocationInput
    ) -> LocationOutput:
        """兜底方案: 返回题目中心位置"""
        center_x = input.question_bbox.x + input.question_bbox.width / 2
        center_y = input.question_bbox.y + input.question_bbox.height / 2
        
        return LocationOutput(
            bbox=BoundingBox(
                x=int(center_x - 50),
                y=int(center_y - 25),
                width=100,
                height=50
            ),
            type="area",
            confidence=0.3,
            reasoning="无法准确定位，返回题目中心位置"
        )
```

### 性能优化

1. **批量处理**: 一次性标注多个错误
2. **缓存结果**: 相似错误复用位置
3. **并行调用**: 多个题目并行标注

---

## GradingOrchestrator

### 完整实现

```python
class GradingOrchestrator:
    def __init__(self):
        self.preprocess_agent = PreprocessAgent()
        self.grading_agent = UnifiedGradingAgent()
        self.location_agent = LocationAnnotationAgent()
        
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> CompiledGraph:
        """构建LangGraph工作流"""
        workflow = StateGraph(GradingState)
        
        # 添加节点
        workflow.add_node("preprocess", self._preprocess_node)
        workflow.add_node("grade", self._grade_node)
        workflow.add_node("annotate", self._annotate_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # 定义流程
        workflow.add_edge("__start__", "preprocess")
        workflow.add_edge("preprocess", "grade")
        workflow.add_edge("grade", "annotate")
        workflow.add_edge("annotate", "finalize")
        workflow.add_edge("finalize", "__end__")
        
        return workflow.compile()
    
    async def _preprocess_node(self, state: GradingState) -> GradingState:
        """预处理节点"""
        segments = await self.preprocess_agent.segment_questions(state["images"])
        return {**state, "question_segments": segments}
    
    async def _grade_node(self, state: GradingState) -> GradingState:
        """批改节点"""
        results = await asyncio.gather(*[
            self.grading_agent.grade(segment)
            for segment in state["question_segments"]
        ])
        return {**state, "grading_results": results}
    
    async def _annotate_node(self, state: GradingState) -> GradingState:
        """标注节点"""
        annotated = []
        for question in state["grading_results"]:
            errors_with_location = await asyncio.gather(*[
                self.location_agent.annotate(LocationInput(
                    image_url=state["images"][question.page_index],
                    question_bbox=question.bbox,
                    error=error
                ))
                for error in question.errors
            ])
            annotated.append({**question, "errors": errors_with_location})
        
        return {**state, "annotated_results": annotated}
    
    async def _finalize_node(self, state: GradingState) -> GradingState:
        """汇总节点"""
        final_result = {
            "submission_id": state["submission_id"],
            "total_score": sum(q.score for q in state["annotated_results"]),
            "max_score": sum(q.max_score for q in state["annotated_results"]),
            "questions": state["annotated_results"]
        }
        return {**state, "final_result": final_result}
    
    async def grade(
        self,
        submission_id: str,
        images: List[str],
        progress_callback: Optional[Callable] = None
    ) -> GradingResult:
        """执行批改"""
        initial_state = GradingState(
            submission_id=submission_id,
            images=images
        )
        
        result = await self.workflow.ainvoke(initial_state)
        
        return result["final_result"]
```

---

**文档版本**: v1.0  
**最后更新**: 2025-10-05  
**状态**: ✅ 完成

