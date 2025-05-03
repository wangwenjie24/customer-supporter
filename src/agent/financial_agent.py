import os
import dotenv
import requests

from typing_extensions import Literal

from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage
from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig

from agent.configuration import Configuration
from agent.state import State
from agent.prompts import financial_instructions

# 加载环境变量
dotenv.load_dotenv()


@tool
def query_policy(query: str) -> str:
    """Query company financial policies and related information."""
    # 获取流式写入器用于实时反馈
    writer = get_stream_writer()
    writer({"action": "检索财务制度"})
    
    # 调用知识库API检索财务制度信息
    klResponse = requests.get(f'{os.getenv("FINANCIAL_KNOWLEDGE_BASE_URL")}?query={query}')    
    data = klResponse.json()['data']
    
    # 格式化检索结果
    result = ''
    source = ''
    for index, item in enumerate(data):
        print(item)
        source += item['metadata']['fileName'] + '\n'
        result += f'片段{index + 1}：{item["content"]}\n'
    
    # 处理无结果情况
    if not result:
        result = '抱歉，没有查询到相关的财务制度或政策信息!'
        
    writer({"action": "检索财务制度"})
    result = result + '\n 数据来源：' + source 
    return result

def call_llm(state, config: RunnableConfig):
    """
    调用大语言模型处理财务查询
    
    Args:
        state: 当前状态
        config: 可运行配置
        
    Returns:
        包含模型响应的字典
    """
    # 获取配置信息
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    # 格式化财务指令，插入用户职称
    financial_instructions_formatted = financial_instructions.format(user_title=user_title)

    # 调用大语言模型并绑定工具
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
        tags=["call_financial"]
    ).bind_tools([query_policy]).invoke([
        SystemMessage(content=financial_instructions_formatted),
        *state.messages
    ])
    return {"messages": [response]}


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    """
    根据模型输出决定下一步操作
    
    Args:
        state: 当前状态
        
    Returns:
        下一步操作的标识符
    """
    last_message = state.messages[-1]
    # 如果没有工具调用，则结束流程
    if not last_message.tool_calls:
        return "__end__"
    # 否则执行请求的工具操作
    return "tools"


# 构建状态图
builder = StateGraph(State)
# 添加节点
builder.add_node("agent", call_llm)
builder.add_node("tools", ToolNode([query_policy]))
# 添加边，定义节点间的连接关系
builder.add_edge("__start__", "agent")
builder.add_conditional_edges(
    "agent",
    route_model_output,
)
builder.add_edge("tools", "agent")

# 编译图形为可执行代理
financial_agent = builder.compile(name="financial_agent")