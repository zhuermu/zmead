#!/usr/bin/env python3
"""
ReAct Agent v2 端到端测试脚本
"""

import asyncio
import json
import sys
from datetime import datetime

import httpx


BASE_URL = "http://localhost:8001"
TIMEOUT = 60.0  # 60秒超时


async def test_health():
    """测试健康检查端点"""
    print("\n" + "="*60)
    print("测试 1: 健康检查")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ 状态码: {response.status_code}")
            
            data = response.json()
            print(f"✅ 系统状态: {data['status']}")
            print(f"✅ Redis: {data['checks']['redis']['status']}")
            print(f"✅ MCP: {data['checks']['mcp']['status']}")
            print(f"✅ Gemini: {data['checks']['gemini']['status']}")
            
            return True
        except Exception as e:
            print(f"❌ 错误: {e}")
            return False


async def test_simple_chat():
    """测试简单聊天"""
    print("\n" + "="*60)
    print("测试 2: 简单聊天 (无需 Tool 调用)")
    print("="*60)
    
    message = "你好！请用一句话介绍你自己。"
    print(f"📤 发送消息: {message}")
    
    payload = {
        "content": message,
        "user_id": "test-user-001",
        "session_id": f"test-session-{datetime.now().timestamp()}"
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            start_time = datetime.now()
            response = await client.post(
                f"{BASE_URL}/api/v1/chat/v3",
                json=payload
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ 状态码: {response.status_code}")
            print(f"⏱️  响应时间: {duration:.2f}秒")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功: {data.get('success', False)}")
                print(f"📥 响应: {data.get('response', '')[:200]}...")
                
                if data.get('tool_results'):
                    print(f"🔧 Tool 调用: {len(data['tool_results'])} 个")
                
                return True
            else:
                print(f"❌ 错误响应: {response.text}")
                return False
                
        except asyncio.TimeoutError:
            print(f"❌ 超时 (>{TIMEOUT}秒)")
            return False
        except Exception as e:
            print(f"❌ 错误: {e}")
            return False


async def test_tool_call():
    """测试需要 Tool 调用的请求"""
    print("\n" + "="*60)
    print("测试 3: Tool 调用测试")
    print("="*60)
    
    message = "我的积分余额是多少？"
    print(f"📤 发送消息: {message}")
    
    payload = {
        "content": message,
        "user_id": "test-user-001",
        "session_id": f"test-session-{datetime.now().timestamp()}"
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            start_time = datetime.now()
            response = await client.post(
                f"{BASE_URL}/api/v1/chat/v3",
                json=payload
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ 状态码: {response.status_code}")
            print(f"⏱️  响应时间: {duration:.2f}秒")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功: {data.get('success', False)}")
                print(f"📥 响应: {data.get('response', '')[:200]}...")
                
                if data.get('tool_results'):
                    print(f"🔧 Tool 调用: {len(data['tool_results'])} 个")
                    for i, tool in enumerate(data['tool_results'], 1):
                        print(f"   {i}. {tool.get('tool_name', 'unknown')}")
                
                return True
            else:
                print(f"❌ 错误响应: {response.text}")
                return False
                
        except asyncio.TimeoutError:
            print(f"❌ 超时 (>{TIMEOUT}秒)")
            return False
        except Exception as e:
            print(f"❌ 错误: {e}")
            return False


async def main():
    """运行所有测试"""
    print("\n" + "🚀 " + "="*56)
    print("🚀  ReAct Agent v2 端到端测试")
    print("🚀 " + "="*56)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"⏱️  超时设置: {TIMEOUT}秒")
    
    results = []
    
    # 测试 1: 健康检查
    results.append(("健康检查", await test_health()))
    
    # 测试 2: 简单聊天
    results.append(("简单聊天", await test_simple_chat()))
    
    # 测试 3: Tool 调用
    results.append(("Tool 调用", await test_tool_call()))
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    print(f"成功率: {passed/total*100:.1f}%")
    
    print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        sys.exit(1)
