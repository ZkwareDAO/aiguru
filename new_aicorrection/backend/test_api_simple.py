"""简单的API测试脚本"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from langchain_openai import ChatOpenAI


async def test_openrouter_connection():
    """测试OpenRouter API连接"""
    print("\n=== 测试OpenRouter API连接 ===\n")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("DEFAULT_MODEL", "google/gemini-flash-1.5-8b-latest")
    
    print(f"API Key: {api_key[:20]}..." if api_key else "未设置")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    
    if not api_key:
        print("\n错误: 未设置OPENROUTER_API_KEY")
        return False
    
    try:
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
            max_tokens=500,
        )
        
        print("\n发送测试请求...")
        response = await llm.ainvoke("请用一句话介绍你自己")
        
        print(f"\n成功! 响应: {response.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"\n失败: {str(e)}")
        return False


async def main():
    """主函数"""
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    success = await test_openrouter_connection()
    
    if success:
        print("\n=== API连接测试通过 ===")
        return 0
    else:
        print("\n=== API连接测试失败 ===")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

