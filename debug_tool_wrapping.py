#!/usr/bin/env python3
"""
调试工具包装功能
"""

import asyncio
import sys
import os

# 添加路径以便导入
sys.path.append(os.path.join(os.path.dirname(__file__), 'mcp-client'))

from core.client_manager import ClientManager
from core.streaming_executor import StreamingLangChainExecutor

async def test_tool_wrapping():
    """测试工具包装功能"""
    print("🧪 测试工具包装功能...")
    
    # 创建客户机管理器
    client_manager = ClientManager()
    
    # 创建流式执行器
    executor = StreamingLangChainExecutor(client_manager)
    
    # 获取流式Agent
    vm_id = "vm123"
    session_id = "sess456"
    
    print(f"📍 测试会话: {vm_id}/{session_id}")
    
    try:
        # 获取流式Agent  
        streaming_agent = await executor._get_streaming_agent_v2(vm_id, session_id)
        print(f"✅ 成功创建流式Agent")
        
        # 检查工具列表
        tools = streaming_agent.tools
        print(f"🔧 可用工具数量: {len(tools)}")
        
        # 查找write_text工具
        write_text_tool = None
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:50]}...")
            if tool.name == 'write_text':
                write_text_tool = tool
                print(f"     🎯 找到write_text工具")
                print(f"     📋 参数模式: {tool.args_schema}")
                if hasattr(tool.args_schema, 'model_fields'):
                    print(f"     🔍 字段: {list(tool.args_schema.model_fields.keys())}")
        
        if write_text_tool:
            print(f"✅ write_text工具包装验证成功")
        else:
            print(f"❌ 未找到write_text工具")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tool_wrapping())