import os
import dotenv
import requests

from dataclasses import dataclass, field
from typing_extensions import TypedDict

from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from agent.configuration import Configuration
from agent.prompts import financial_data_query_instructions

# 加载环境变量
dotenv.load_dotenv()


# 定义输入状态类
@dataclass
class InputState:
    query: str = field(default="")  # 用户查询内容

# 定义工作流状态类
@dataclass
class State(TypedDict):
    query: str                      # 用户查询内容
    query_result: str = ""          # 查询结果
    final_output: str = ""          # 最终输出
    need_more_information: bool = False  # 是否需要更多信息

# 定义输出状态类
@dataclass
class OutputState:
    final_output: str               # 最终输出结果

def query_data(state):
    """查询公司财务数据信息
    
    Args:
        state: 包含查询内容的状态对象
        
    Returns:
        包含查询结果的字典
    """
    writer = get_stream_writer()
    writer({"action": "查询财务数据"})

    # 获取查询内容
    query = state["query"]
    
    # 调用财务数据API
    klResponse = requests.post(
        f'{os.getenv("CHATBI_BASE_URL")}',
        json={
            "chatId": "888",
            "question": query,
            "knowledgeId": "1916018867520544768",
            "modelId": "1909433699322408960"
        }
    )
    
    # 检查请求状态码是否为200
    if klResponse.status_code == 200:
        data = klResponse.json()['data']
        code = klResponse.json()['code']
        msg = klResponse.json()['msg']
        
        # 处理错误情况
        if code == -1:
            return {"query_result": msg}
            
        # 处理空结果情况
        if not data or len(data) == 0:
            writer({"action": "检索财务数据"})
            return {"query_result": "抱歉，没有查询到相关信息。"}
        else:
            writer({"action": "检索财务数据"})
            return {"query_result": data}    
    else:
        writer({"action": "检索财务数据"})
        return {"final_output": "抱歉，查询财务数据时发生错误，请稍后再试。"}


def call_llm(state, config: RunnableConfig):
    """调用大语言模型处理查询结果
    
    Args:
        state: 包含查询结果的状态对象
        config: 运行时配置
        
    Returns:
        包含最终输出的字典
    """
    # 获取配置信息
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    # 获取查询结果
    query_result = state["query_result"]
    
    # 格式化指令
    financial__data_query_instructions_formatted = financial_data_query_instructions.format(user_title=user_title)

    # 调用LLM处理查询结果
    response = ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        tags=["call_financial_data"]
    ).invoke([
        SystemMessage(content=financial__data_query_instructions_formatted),
        HumanMessage(content=str(query_result)),
    ])
    
    return {"final_output": response.content}


# 构建工作流图
workflow = StateGraph(
    State, input=InputState, output=OutputState, config_schema=Configuration
)

# 添加节点
workflow.add_node("query_data", query_data)
workflow.add_node("agent", call_llm)

# 定义节点间的连接
workflow.add_edge("__start__", "query_data")
workflow.add_edge("query_data", "agent")
workflow.add_edge("agent", "__end__")

# 定义入口点和结束点
workflow.set_entry_point("query_data")
workflow.set_finish_point("agent")

# 编译工作流
finacial_data_query_workflow = workflow.compile(name="finacial_data_query_workflow")