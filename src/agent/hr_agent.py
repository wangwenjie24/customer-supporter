import os
import dotenv
import requests

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode


from agent.configuration import Configuration
from agent.state import State
from agent.prompts import hr_instructions

from typing import Literal

# 加载环境变量
dotenv.load_dotenv()


@tool
def query_policy(query: str) -> str:
    """
    Query company human resources related policy information.
    
    Args:
        query: 查询关键词
        
    Returns:
        查询结果字符串
    """
    # 获取流式写入器用于实时反馈
    writer = get_stream_writer()
    writer({"action": "检索人力资源制度"})
    
    # 调用知识库API检索HR制度信息
    klResponse = requests.get(f'{os.getenv("HR_KNOWLEDGE_BASE_URL")}?query={query}')
    data = klResponse.json()['data']
    
    # 格式化检索结果
    result = ''
    source = ''
    for index, item in enumerate(data):
        source += item['metadata']['fileName'] + '\n'
        result += f'片段{index + 1}：{item["content"]}\n'
    
    # 处理无结果情况
    if not result:
        result = '抱歉，没有查询到相关的HR制度或政策信息。'
        
    writer({"action": "检索人力资源制度"})
    result = result + '\n 数据来源：' + source 
    return result


def call_llm(state, config: RunnableConfig):
    """
    调用大语言模型处理HR查询
    
    Args:
        state: 当前状态
        config: 可运行配置
        
    Returns:
        包含模型响应的字典
    """
    # 获取配置信息
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    # 格式化HR指令，插入用户职称
    hr_instructions_formatted = hr_instructions.format(user_title=user_title)

    # 构造消息列表
    trimmed_messages = trim_messages(
        state.messages,
        strategy="last",
        token_counter=len,
        max_tokens=5,
        start_on="human",
        end_on=("human", "tool"),
        include_system=True,
    )
    
    # 调用大语言模型并绑定工具
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
        tags=["call_hr"]
    ).bind_tools([query_policy]).invoke([
        SystemMessage(content=hr_instructions_formatted),
        *trimmed_messages
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
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )
    # 如果没有工具调用，则结束流程
    if not last_message.tool_calls:
        return "__end__"
    # 否则执行请求的工具操作
    return "tools"


# 构建状态图
builder = StateGraph(State, config_schema=Configuration)
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
hr_agent = builder.compile(name="hr_agent")