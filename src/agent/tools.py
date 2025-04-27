from langgraph_sdk import get_client
import asyncio

async def main():
    # 初始化LangGraph客户端
    url_for_cli_deployment = "http://localhost:8123"
    client = get_client(url=url_for_cli_deployment)
    
    # 创建LangGraph线程
    thread = await client.threads.create()
    
    # 用于存储最终响应
    final_ai_response = ""
    
    try:
        # 使用stream_mode="values"获取整个状态
        async for chunk in client.runs.stream(
                thread["thread_id"],
                assistant_id="786ad614-e07c-4b7b-ad69-5aa9accdfa1f",
                input={"message": "你好"},
                stream_mode="values"
            ):
            if chunk.event == 'values' and 'messages' in chunk.data:
                messages = chunk.data['messages']
                # 查找AI消息，不包含工具调用的消息是最终回复
                for msg in reversed(messages):
                    if isinstance(msg, dict) and msg.get('type') == 'ai' and not msg.get('tool_calls'):
                        if 'content' in msg and msg['content']:
                            final_ai_response = msg['content']
                            break
    except Exception as e:
        print(f"发生错误: {e}")
    
    # 输出最终的AI回复
    print("\n最终AI回复:")
    print(final_ai_response)

# 使用stream_mode="messages-tuple"方法
async def extract_with_messages_tuple():
    url_for_cli_deployment = "http://localhost:8123"
    client = get_client(url=url_for_cli_deployment)
    
    thread = await client.threads.create()
    
    ai_message_contents = []
    
    try:
        async for chunk in client.runs.stream(
                thread["thread_id"],
                assistant_id="786ad614-e07c-4b7b-ad69-5aa9accdfa1f",
                input={"message": "福利待遇有什么？"},
                stream_mode="messages-tuple"
            ):
            # 仅处理messages事件
            if chunk.event == 'messages':
                message_data = chunk.data
                if message_data and isinstance(message_data, list) and len(message_data) > 0:
                    message = message_data[0]
                    # 检查是否为AI消息且不包含工具调用
                    if isinstance(message, dict) and message.get('type') == 'ai' and not message.get('tool_calls'):
                        if 'content' in message and message['content']:
                            ai_message_contents.append(message['content'])
    except Exception as e:
        print(f"消息元组模式错误: {e}")
    
    # 输出收集到的所有AI消息内容
    if ai_message_contents:
        print("\n使用messages-tuple模式收集的AI回复:")
        for i, content in enumerate(ai_message_contents):
            print(f"{i+1}. {content}")
        print("\n最终AI回复:")
        print(ai_message_contents[-1])

if __name__ == "__main__":
    # 两种方法都可以尝试
    asyncio.run(main())
    # asyncio.run(extract_with_messages_tuple()) 