"""
统一API客户端

提供标准化的API调用接口，支持异步调用和并发控制。
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import base64

from ..models.api_models import APIResponse, ModelConfig, UsageStats, APICallContext, TaskType
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

@dataclass
class CallContext:
    """API调用上下文"""
    request_id: str
    model_config: ModelConfig
    prompt: str
    content: List[Dict[str, Any]]
    retry_count: int = 0
    start_time: Optional[datetime] = None
    timeout: int = 120
    max_retries: int = 3

class APIClient:
    """统一API客户端"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(3)  # 并发控制
        self._request_counter = 0
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=300)  # 5分钟总超时
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
            )
    
    async def close(self):
        """关闭HTTP会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _generate_request_id(self) -> str:
        """生成请求ID"""
        self._request_counter += 1
        timestamp = int(time.time() * 1000)
        return f"req_{timestamp}_{self._request_counter}"
    
    async def call_api(self, 
                      model_config: ModelConfig,
                      prompt: str,
                      content: List[Dict[str, Any]],
                      **kwargs) -> APIResponse:
        """
        执行API调用
        
        Args:
            model_config: 模型配置
            prompt: 提示词
            content: 内容列表
            **kwargs: 其他参数
            
        Returns:
            APIResponse: API响应
        """
        async with self.semaphore:  # 并发控制
            await self._ensure_session()
            
            context = CallContext(
                request_id=self._generate_request_id(),
                model_config=model_config,
                prompt=prompt,
                content=content,
                start_time=datetime.now(),
                timeout=kwargs.get('timeout', 120),
                max_retries=kwargs.get('max_retries', 3)
            )
            
            logger.info(f"开始API调用 {context.request_id} - 模型: {model_config.name}")
            
            try:
                return await self._execute_request(context)
            except Exception as e:
                logger.error(f"API调用失败 {context.request_id}: {str(e)}")
                raise
    
    async def _execute_request(self, context: CallContext) -> APIResponse:
        """执行具体的API请求"""
        # 构建请求数据
        request_data = self._build_request_data(context)
        
        # 构建请求头
        headers = self._build_headers(context.model_config)
        
        try:
            async with self.session.post(
                context.model_config.endpoint,
                json=request_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=context.timeout)
            ) as response:
                
                response_time = (datetime.now() - context.start_time).total_seconds()
                
                if response.status == 200:
                    response_data = await response.json()
                    return self._parse_response(context, response_data, response_time)
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except asyncio.TimeoutError:
            raise Exception(f"请求超时 ({context.timeout}秒)")
        except aiohttp.ClientError as e:
            raise Exception(f"网络错误: {str(e)}")
    
    def _build_request_data(self, context: CallContext) -> Dict[str, Any]:
        """构建请求数据"""
        messages = []
        
        # 添加系统消息
        if context.prompt:
            messages.append({
                "role": "system",
                "content": context.prompt
            })
        
        # 添加用户消息
        user_content = []
        
        # 处理文本内容
        text_parts = [item for item in context.content if item.get('type') == 'text']
        if text_parts:
            combined_text = '\n\n'.join([item['content'] for item in text_parts])
            user_content.append({
                "type": "text",
                "text": combined_text
            })
        
        # 处理图像内容
        image_parts = [item for item in context.content if item.get('type') == 'image']
        for image_item in image_parts:
            if 'base64' in image_item:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_item['base64']}"
                    }
                })
        
        messages.append({
            "role": "user",
            "content": user_content if len(user_content) > 1 else user_content[0] if user_content else ""
        })
        
        return {
            "model": context.model_config.id,
            "messages": messages,
            "max_tokens": context.model_config.max_tokens,
            "temperature": context.model_config.additional_params.get('temperature', 0.7),
            "stream": False
        }
    
    def _build_headers(self, model_config: ModelConfig) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {model_config.api_key}"
        }
        
        # 添加特定提供商的头部
        if hasattr(model_config.provider, 'value'):
            provider_name = model_config.provider.value
        else:
            provider_name = str(model_config.provider)
            
        if provider_name == "openrouter" or "openrouter" in model_config.endpoint:
            headers["HTTP-Referer"] = "https://github.com/your-repo"
            headers["X-Title"] = "AI Grading System"
        
        return headers
    
    def _parse_response(self, context: CallContext, response_data: Dict[str, Any], response_time: float) -> APIResponse:
        """解析API响应"""
        try:
            # 提取响应内容
            choices = response_data.get('choices', [])
            if not choices:
                raise Exception("响应中没有choices字段")
            
            content = choices[0].get('message', {}).get('content', '')
            if not content:
                raise Exception("响应内容为空")
            
            # 提取使用统计
            usage = response_data.get('usage', {})
            usage_stats = UsageStats(
                prompt_tokens=usage.get('prompt_tokens', 0),
                completion_tokens=usage.get('completion_tokens', 0),
                total_tokens=usage.get('total_tokens', 0),
                cost=self._calculate_cost(usage, context.model_config)
            )
            
            # 计算质量分数（基于响应时间和内容长度）
            quality_score = self._calculate_quality_score(content, response_time)
            
            return APIResponse(
                request_id=context.request_id,
                model_id=context.model_config.id,
                content=content,
                usage_stats=usage_stats,
                response_time=response_time,
                quality_score=quality_score,
                timestamp=datetime.now(),
                status_code=200
            )
            
        except Exception as e:
            logger.error(f"解析响应失败 {context.request_id}: {str(e)}")
            return APIResponse(
                request_id=context.request_id,
                model_id=context.model_config.id,
                content="",
                usage_stats=UsageStats(),
                response_time=response_time,
                quality_score=0.0,
                timestamp=datetime.now(),
                status_code=500,
                error_message=str(e)
            )
    
    def _calculate_cost(self, usage: Dict[str, Any], model_config: ModelConfig) -> float:
        """计算调用成本"""
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        
        # 使用模型配置中的价格信息
        # 如果没有分别的输入输出价格，使用统一价格
        cost_per_token = model_config.cost_per_token
        total_cost = (prompt_tokens + completion_tokens) * cost_per_token
        
        return total_cost
    
    def _calculate_quality_score(self, content: str, response_time: float) -> float:
        """计算质量分数"""
        # 基础分数
        score = 1.0
        
        # 根据响应时间调整（响应时间越短，分数越高）
        if response_time < 5:
            score += 0.2
        elif response_time > 30:
            score -= 0.3
        
        # 根据内容长度调整
        content_length = len(content)
        if content_length < 50:
            score -= 0.2  # 内容太短
        elif content_length > 1000:
            score += 0.1  # 内容丰富
        
        # 检查内容质量指标
        if '错误' in content or 'error' in content.lower():
            score -= 0.1
        
        if any(keyword in content for keyword in ['分析', '建议', '总结', '评价']):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def batch_call(self, 
                        requests: List[Dict[str, Any]], 
                        batch_size: int = 5) -> List[APIResponse]:
        """
        批量API调用
        
        Args:
            requests: 请求列表
            batch_size: 批次大小
            
        Returns:
            List[APIResponse]: 响应列表
        """
        results = []
        
        # 分批处理
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # 并发执行批次内的请求
            tasks = []
            for req in batch:
                task = self.call_api(**req)
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"批量调用中的错误: {str(result)}")
                    # 创建错误响应
                    error_response = APIResponse(
                        request_id=self._generate_request_id(),
                        model_id="unknown",
                        content="",
                        usage_stats=UsageStats(),
                        response_time=0.0,
                        quality_score=0.0,
                        timestamp=datetime.now(),
                        status_code=500,
                        error_message=str(result)
                    )
                    results.append(error_response)
                else:
                    results.append(result)
        
        return results