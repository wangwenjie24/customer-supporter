"""
修复合同法律风险分析工具的连接和消息格式问题

此脚本提供了对original corporate_legal.ipynb文件的修复，主要解决：
1. APIConnectionError连接错误 - 可能是OpenAI API密钥失效
2. HumanMessage验证错误 - 使用正确的多模态消息格式
"""

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from agent.llm import llm
import os
import base64
from pathlib import Path
import dotenv

# 重新加载环境变量，确保API密钥正常加载
dotenv.load_dotenv(override=True)

def main():
    # 定义合同文件路径
    contract_file_path = "/Users/wangwenjie/Desktop/基于数字孪生的立体仓库和工厂车间展示项目-技术协议书-北京科安-20241108-V1.8_20250422172436.pdf"

    # 检查文件是否存在
    if not os.path.exists(contract_file_path):
        print(f"文件不存在: {contract_file_path}")
        return
    
    print(f"文件存在: {contract_file_path}")

    # 读取PDF并将其编码为base64
    try:
        with open(contract_file_path, "rb") as pdf_file:
            pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
            print(f"已成功加载PDF文件，Base64编码长度: {len(pdf_base64)}")
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return

    # 方法1：使用ChatPromptTemplate和正确的多模态消息格式
    print("\n==== 方法1：使用ChatPromptTemplate ====")
    try:
        # 使用最新的LangChain格式来处理多模态内容
        template = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a corporate legal expert with access to check contract risk."),
            ("human", [
                {"type": "text", "text": "请分析以下合同附件中的法律风险"},
                {
                    "type": "image_url", 
                    "image_url": {
                        "url": f"data:application/pdf;base64,{pdf_base64}",
                        "detail": "auto"
                    }
                }
            ])
        ])
        
        # 格式化消息
        messages = template.format_messages()
        print("消息格式化成功")
        
        # 调用LLM
        try:
            response = llm.invoke(messages)
            print("LLM响应:")
            print(response.content)
        except Exception as e:
            print(f"调用LLM时出错: {e}")
            print("\n可能是API密钥无效或API连接问题，请检查您的.env文件中的OPENAI_API_KEY")
            print(f"当前使用的OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')[:10]}***")
    except Exception as e:
        print(f"创建消息格式时出错: {e}")

    # 方法2：测试简单的文本调用，验证API连接
    print("\n==== 方法2：测试基本API连接 ====")
    try:
        simple_response = llm.invoke("请确认你能看到这条消息，并简要描述你的功能")
        print("基本LLM测试响应:")
        print(simple_response.content)
    except Exception as e:
        print(f"测试LLM基本功能时出错: {e}")
        print("\n这可能是API密钥问题或连接问题，请检查以下内容:")
        print("1. .env文件中的OPENAI_API_KEY是否有效")
        print("2. 网络连接是否正常")
        print("3. API密钥是否有足够的配额")
        print("4. 是否需要使用代理")

    # 方法3：通过其他方法读取和处理PDF内容
    print("\n==== 方法3：使用文本提取方法 ====")
    try:
        from unstructured.partition.pdf import partition_pdf
        
        print("使用unstructured库提取PDF内容...")
        elements = partition_pdf(contract_file_path)
        pdf_text = "\n".join([str(el) for el in elements])
        
        # 截取部分内容防止过长
        text_preview = pdf_text[:500] + "..." if len(pdf_text) > 500 else pdf_text
        print(f"提取的内容预览: {text_preview}")
        
        # 使用普通文本内容调用
        try:
            text_prompt = f"请分析以下合同内容中的法律风险:\n\n{pdf_text[:4000]}..."
            text_response = llm.invoke(text_prompt)
            print("LLM响应:")
            print(text_response.content)
        except Exception as e:
            print(f"使用文本内容调用LLM时出错: {e}")
    except Exception as e:
        print(f"尝试提取PDF文本时出错: {e}")
        print("请安装必要的依赖: pip install unstructured[pdf]")

if __name__ == "__main__":
    print("启动合同法律风险分析工具...")
    main() 