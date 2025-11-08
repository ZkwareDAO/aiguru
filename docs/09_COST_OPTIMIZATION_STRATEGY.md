# Agent成本优化策略

## 📌 文档概述

本文档详细分析Agent架构的成本问题，并提供多种优化方案和实施建议。

---

## 1. 成本分析

### 1.1 当前设计的成本结构

**Agent分类**：

| Agent | 是否调用LLM | 成本 | 说明 |
|-------|------------|------|------|
| OrchestratorAgent | ❌ | $0 | 纯流程控制 |
| PreprocessAgent | ❌ | $0 | 文件处理、OCR |
| **GradingAgent** | ✅ | **$0.008-0.015** | 主要成本来源 |
| ReviewAgent | ❌ | $0 | 规则验证 |
| **FeedbackAgent** | ⚠️ | **$0.002-0.005** | 可选LLM调用 |

**单次批改成本**：
```
基础模式: $0.008 (仅GradingAgent)
标准模式: $0.010 (GradingAgent + 简单Feedback)
完整模式: $0.015 (GradingAgent + 详细Feedback)
```

**月度成本估算**：
```
假设: 每天1000次批改
- 基础模式: $0.008 × 1000 × 30 = $240/月
- 标准模式: $0.010 × 1000 × 30 = $300/月
- 完整模式: $0.015 × 1000 × 30 = $450/月
```

---

## 2. 优化方案

### 方案1: 智能Agent融合 (推荐)

**核心思路**: 根据任务复杂度动态选择Agent组合

#### 2.1 三种模式

```python
class AgentMode(Enum):
    """Agent运行模式"""
    FAST = "fast"           # 快速模式 - 单Agent
    STANDARD = "standard"   # 标准模式 - 2-3个Agent
    PREMIUM = "premium"     # 完整模式 - 全部Agent

class SmartOrchestrator:
    """智能编排器 - 根据场景选择Agent组合"""
    
    def __init__(self):
        # 融合Agent - 将多个功能合并到一次LLM调用
        self.unified_agent = UnifiedGradingAgent()
        
        # 独立Agent - 用于复杂场景
        self.preprocess_agent = PreprocessAgent()
        self.grading_agent = GradingAgent()
        self.review_agent = ReviewAgent()
        self.feedback_agent = FeedbackAgent()
    
    async def execute(self, input_data: Dict) -> Dict:
        """根据场景选择执行模式"""
        # 1. 评估任务复杂度
        complexity = await self._assess_complexity(input_data)
        
        # 2. 选择执行模式
        if complexity == "simple":
            return await self._fast_mode(input_data)
        elif complexity == "medium":
            return await self._standard_mode(input_data)
        else:
            return await self._premium_mode(input_data)
    
    async def _fast_mode(self, input_data: Dict) -> Dict:
        """快速模式 - 单次LLM调用完成所有任务"""
        # 预处理(不调用LLM)
        state = await self.preprocess_agent.process(input_data)
        
        # 统一批改(一次LLM调用完成批改+反馈)
        result = await self.unified_agent.process(state)
        
        return result
    
    async def _standard_mode(self, input_data: Dict) -> Dict:
        """标准模式 - 2次LLM调用"""
        # 预处理
        state = await self.preprocess_agent.process(input_data)
        
        # 批改(第1次LLM调用)
        state = await self.grading_agent.process(state)
        
        # 审核(规则检查,不调用LLM)
        state = await self.review_agent.process(state)
        
        # 反馈(第2次LLM调用,仅在需要时)
        if state["confidence"] < 0.8:
            state = await self.feedback_agent.process(state)
        
        return state
    
    async def _premium_mode(self, input_data: Dict) -> Dict:
        """完整模式 - 使用所有Agent"""
        # 完整的Pipeline
        state = await self.preprocess_agent.process(input_data)
        state = await self.grading_agent.process(state)
        state = await self.review_agent.process(state)
        state = await self.feedback_agent.process(state)
        return state
    
    async def _assess_complexity(self, input_data: Dict) -> str:
        """评估任务复杂度"""
        # 基于多个因素判断
        factors = {
            "file_count": len(input_data.get("files", [])),
            "file_size": sum(f.get("size", 0) for f in input_data.get("files", [])),
            "question_count": input_data.get("question_count", 1),
            "subject": input_data.get("subject", ""),
            "grade_level": input_data.get("grade_level", ""),
        }
        
        # 简单任务: 单文件、小尺寸、基础题目
        if (factors["file_count"] == 1 and 
            factors["file_size"] < 1_000_000 and 
            factors["question_count"] <= 3):
            return "simple"
        
        # 复杂任务: 多文件、大尺寸、复杂题目
        elif (factors["file_count"] > 3 or 
              factors["file_size"] > 5_000_000 or 
              factors["question_count"] > 10):
            return "complex"
        
        # 中等任务
        return "medium"
```

#### 2.2 统一批改Agent

```python
class UnifiedGradingAgent:
    """统一批改Agent - 一次LLM调用完成批改+反馈"""
    
    async def process(self, state: GradingState) -> GradingState:
        """单次LLM调用完成所有任务"""
        
        # 构建统一的提示词
        prompt = self._build_unified_prompt(state)
        
        # 一次LLM调用
        response = await self.llm.ainvoke(prompt)
        
        # 解析结果
        result = self._parse_unified_result(response)
        
        # 更新状态
        state.update({
            "score": result["score"],
            "errors": result["errors"],
            "confidence": result["confidence"],
            "feedback_text": result["feedback"],
            "suggestions": result["suggestions"],
            "knowledge_points": result["knowledge_points"]
        })
        
        return state
    
    def _build_unified_prompt(self, state: GradingState) -> str:
        """构建统一提示词 - 一次性完成所有任务"""
        return f"""
你是一位专业的教师,请完成以下批改任务:

【批改标准】
{state["grading_standard"]}

【学生答案】
{state["extracted_text"]}

请一次性完成以下所有任务,并以JSON格式输出:

1. **批改评分**: 找出错误,计算分数
2. **错误分析**: 详细说明每个错误
3. **总体反馈**: 优点、不足、改进建议
4. **知识点关联**: 相关知识点和学习建议

输出格式:
{{
    "score": 分数,
    "confidence": 置信度,
    "errors": [
        {{
            "type": "错误类型",
            "description": "错误说明",
            "correct_answer": "正确答案",
            "deduction": 扣分
        }}
    ],
    "overall_comment": "总体评价",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["建议1", "建议2"],
    "knowledge_points": [
        {{
            "name": "知识点名称",
            "mastery_level": 掌握程度(0-100),
            "suggestion": "学习建议"
        }}
    ]
}}
"""
```

**成本对比**：
```
原设计: GradingAgent($0.008) + FeedbackAgent($0.005) = $0.013
优化后: UnifiedAgent($0.010) = $0.010
节省: 23%
```

---

### 方案2: 批量处理优化

**核心思路**: 将多个学生的作业合并到一次LLM调用

```python
class BatchGradingAgent:
    """批量批改Agent - 一次处理多份作业"""
    
    async def batch_process(
        self, 
        submissions: List[GradingState],
        batch_size: int = 5
    ) -> List[GradingState]:
        """批量处理多份作业"""
        
        # 构建批量提示词
        prompt = self._build_batch_prompt(submissions)
        
        # 一次LLM调用处理多份作业
        response = await self.llm.ainvoke(prompt)
        
        # 解析批量结果
        results = self._parse_batch_results(response, len(submissions))
        
        return results
    
    def _build_batch_prompt(self, submissions: List[GradingState]) -> str:
        """构建批量提示词"""
        submissions_text = "\n\n".join([
            f"【学生{i+1}答案】\n{sub['extracted_text']}"
            for i, sub in enumerate(submissions)
        ])
        
        return f"""
请批改以下{len(submissions)}份学生作业:

【批改标准】
{submissions[0]["grading_standard"]}

{submissions_text}

请为每份作业分别输出批改结果,格式为JSON数组:
[
    {{"student_index": 1, "score": ..., "errors": [...], ...}},
    {{"student_index": 2, "score": ..., "errors": [...], ...}},
    ...
]
"""
```

**成本对比**：
```
原设计: 5份作业 × $0.010 = $0.050
批量处理: 1次调用 = $0.020
节省: 60%
```

**注意事项**：
- ⚠️ 批量大小不宜过大(建议3-5份)
- ⚠️ 需要确保LLM能正确区分不同学生的答案
- ⚠️ 适合简单、标准化的作业

---

### 方案3: 智能缓存策略

**核心思路**: 缓存相似问题的批改结果

```python
class CachedGradingAgent:
    """带缓存的批改Agent"""
    
    def __init__(self):
        self.cache = GradingCache()
        self.similarity_threshold = 0.85
    
    async def process(self, state: GradingState) -> GradingState:
        """带缓存的批改"""
        
        # 1. 计算答案指纹
        answer_hash = self._compute_hash(state["extracted_text"])
        
        # 2. 查找相似的缓存结果
        cached_result = await self.cache.find_similar(
            answer_hash,
            threshold=self.similarity_threshold
        )
        
        if cached_result:
            logger.info("Cache hit! Reusing previous grading result")
            # 使用缓存结果,稍作调整
            return self._adapt_cached_result(cached_result, state)
        
        # 3. 缓存未命中,调用LLM
        result = await self._call_llm(state)
        
        # 4. 缓存结果
        await self.cache.store(answer_hash, result)
        
        return result
    
    def _compute_hash(self, text: str) -> str:
        """计算文本相似度哈希"""
        # 使用SimHash或MinHash
        from simhash import Simhash
        return str(Simhash(text).value)
    
    async def _adapt_cached_result(
        self, 
        cached: Dict, 
        current: GradingState
    ) -> GradingState:
        """调整缓存结果以适应当前任务"""
        # 保留核心批改结果,但更新时间戳等元数据
        current.update({
            "score": cached["score"],
            "errors": cached["errors"],
            "confidence": cached["confidence"] * 0.95,  # 略微降低置信度
            "feedback_text": cached["feedback_text"],
            "from_cache": True
        })
        return current
```

**成本节省**：
```
假设缓存命中率30%:
原成本: $300/月
优化后: $300 × (1 - 0.3) = $210/月
节省: 30%
```

---

### 方案4: 分层定价策略

**核心思路**: 让用户选择不同的批改质量等级

```python
class TieredGradingService:
    """分层批改服务"""
    
    PRICING_TIERS = {
        "basic": {
            "name": "基础批改",
            "price": 0.5,  # 元/次
            "features": ["自动评分", "错误标注"],
            "agent_mode": "fast",
            "llm_model": "gpt-3.5-turbo"
        },
        "standard": {
            "name": "标准批改",
            "price": 1.0,  # 元/次
            "features": ["自动评分", "错误标注", "详细反馈"],
            "agent_mode": "standard",
            "llm_model": "gpt-4-turbo"
        },
        "premium": {
            "name": "精品批改",
            "price": 2.0,  # 元/次
            "features": ["自动评分", "错误标注", "详细反馈", "学习建议", "人工审核"],
            "agent_mode": "premium",
            "llm_model": "gpt-4-turbo"
        }
    }
    
    async def grade_with_tier(
        self, 
        submission_id: UUID,
        tier: str = "standard"
    ) -> GradingResult:
        """根据等级进行批改"""
        config = self.PRICING_TIERS[tier]
        
        # 使用对应的Agent模式和模型
        orchestrator = SmartOrchestrator(
            mode=config["agent_mode"],
            llm_model=config["llm_model"]
        )
        
        result = await orchestrator.execute({
            "submission_id": submission_id,
            "tier": tier
        })
        
        return result
```

---

## 3. 推荐实施方案

### 阶段1: 立即实施 (成本节省 ~40%)

```python
# 1. 实现智能Agent融合
class OptimizedOrchestrator:
    """优化后的编排器"""
    
    async def execute(self, input_data: Dict) -> Dict:
        # 默认使用快速模式
        mode = input_data.get("mode", "fast")
        
        if mode == "fast":
            # 单次LLM调用完成批改+反馈
            return await self.unified_agent.process(input_data)
        
        elif mode == "standard":
            # 批改 + 规则审核 + 简单反馈
            state = await self.grading_agent.process(input_data)
            state = await self.review_agent.process(state)  # 不调用LLM
            return state
        
        else:  # premium
            # 完整流程
            return await self.full_pipeline(input_data)

# 2. 添加智能缓存
@cache_similar(similarity_threshold=0.85)
async def grade_submission(submission_id: UUID):
    return await grading_agent.process(submission_id)
```

**预期效果**：
- 成本从 $0.015 降至 $0.009
- 节省 40%
- 速度提升 30%

---

### 阶段2: 中期优化 (成本节省 ~60%)

```python
# 3. 实现批量处理
async def batch_grade_class(assignment_id: UUID):
    """批量批改整个班级的作业"""
    submissions = await get_submissions(assignment_id)
    
    # 按相似度分组
    groups = group_by_similarity(submissions, group_size=5)
    
    # 批量处理每组
    results = []
    for group in groups:
        batch_result = await batch_grading_agent.process(group)
        results.extend(batch_result)
    
    return results

# 4. 使用更便宜的模型
class ModelSelector:
    """智能模型选择"""
    
    def select_model(self, complexity: str) -> str:
        if complexity == "simple":
            return "gpt-3.5-turbo"  # $0.001/1K tokens
        elif complexity == "medium":
            return "gpt-4-turbo"    # $0.01/1K tokens
        else:
            return "gpt-4"          # $0.03/1K tokens
```

**预期效果**：
- 批量处理节省 50%
- 模型选择节省 30%
- 综合节省 60%

---

### 阶段3: 长期优化 (成本节省 ~80%)

```python
# 5. 训练专用模型
class CustomGradingModel:
    """微调的专用批改模型"""
    
    def __init__(self):
        # 使用开源模型微调
        self.model = load_finetuned_model("grading-model-v1")
    
    async def grade(self, submission):
        # 使用自己的模型,成本极低
        return await self.model.predict(submission)

# 6. 混合策略
async def hybrid_grading(submission):
    """混合使用自有模型和API"""
    
    # 先用自有模型快速批改
    quick_result = await custom_model.grade(submission)
    
    # 如果置信度低,再用GPT-4审核
    if quick_result.confidence < 0.8:
        final_result = await gpt4_agent.review(quick_result)
    else:
        final_result = quick_result
    
    return final_result
```

**预期效果**：
- 80%的简单任务用自有模型(成本 ~$0.001)
- 20%的复杂任务用GPT-4(成本 ~$0.015)
- 综合成本: $0.003
- 节省 80%

---

## 4. 成本对比总结

| 方案 | 单次成本 | 月度成本(1000次/天) | 节省比例 | 实施难度 |
|------|---------|-------------------|---------|---------|
| 原设计(完整模式) | $0.015 | $450 | 0% | - |
| 智能融合 | $0.009 | $270 | 40% | ⭐ 简单 |
| + 批量处理 | $0.006 | $180 | 60% | ⭐⭐ 中等 |
| + 智能缓存 | $0.004 | $120 | 73% | ⭐⭐ 中等 |
| + 自有模型 | $0.003 | $90 | 80% | ⭐⭐⭐ 困难 |

---

## 5. 最终建议

### 推荐方案: 智能Agent融合 + 分层定价

```python
class ProductionGradingSystem:
    """生产环境批改系统"""
    
    def __init__(self):
        self.unified_agent = UnifiedGradingAgent()  # 快速模式
        self.standard_pipeline = StandardPipeline()  # 标准模式
        self.premium_pipeline = PremiumPipeline()    # 完整模式
        self.cache = GradingCache()
    
    async def grade(
        self, 
        submission_id: UUID,
        tier: str = "standard"
    ) -> GradingResult:
        """智能批改"""
        
        # 1. 检查缓存
        cached = await self.cache.get(submission_id)
        if cached:
            return cached
        
        # 2. 评估复杂度
        complexity = await self._assess_complexity(submission_id)
        
        # 3. 选择执行策略
        if tier == "basic" or complexity == "simple":
            result = await self.unified_agent.process(submission_id)
        elif tier == "standard":
            result = await self.standard_pipeline.process(submission_id)
        else:  # premium
            result = await self.premium_pipeline.process(submission_id)
        
        # 4. 缓存结果
        await self.cache.set(submission_id, result)
        
        return result
```

### 定价建议

| 套餐 | 价格 | 成本 | 利润率 | 适用场景 |
|------|------|------|--------|---------|
| 基础版 | ¥0.5/次 | ¥0.06 | 88% | 简单选择题、填空题 |
| 标准版 | ¥1.0/次 | ¥0.09 | 91% | 一般主观题 |
| 精品版 | ¥2.0/次 | ¥0.15 | 92% | 复杂论述题、作文 |

---

## 6. 实施检查清单

- [ ] 实现UnifiedGradingAgent
- [ ] 实现智能复杂度评估
- [ ] 添加相似度缓存
- [ ] 实现分层定价
- [ ] 添加成本监控
- [ ] 进行A/B测试
- [ ] 优化提示词长度
- [ ] 实现批量处理(可选)

---

**总结**: 通过智能Agent融合,可以在保持批改质量的同时,将成本降低40-60%,并为用户提供灵活的选择。

