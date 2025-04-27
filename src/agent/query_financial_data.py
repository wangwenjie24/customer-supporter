import os
import dotenv
import requests

from typing_extensions import Literal
from dataclasses import dataclass, field
from typing_extensions import TypedDict

from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig

from agent.configuration import Configuration
from agent.prompts import financial_data_query_instructions

dotenv.load_dotenv()



@dataclass
class InputState:
    query: str = field(default="")

@dataclass
class State(TypedDict):
    query: str
    query_data: str = ""
    final_output: str = ""
    need_more_information: bool = False

@dataclass
class OutputState:
    final_output: str

def query_financial_data(state):
    """Query company financial data information.
    
    Args:
        query (str): 查询的财务数据关键词或指标名称。
    """
    # writer = get_stream_writer()
    # writer({"action": "查询财务数据"})

    query = state["query"]
    klResponse = requests.post(
        'http://192.168.3.99:9900/ai/agent/chatBI',
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
        if code == -1:
            return {"query_data": msg}
        if not data or len(data) == 0:
            return {"query_data": "抱歉，没有查询到相关信息。"}
        else:
            return {"query_data": data}    
    else:
        # writer({"action": "检索财务制度"})
        return {"final_output": "抱歉，查询财务数据时发生错误，请稍后再试。"}

# If need more information, please ask user for more information.
# If have enough information, please answer the question.

def call_llm(state, config: RunnableConfig):
    # Get the configuration
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    query_data = state["query_data"]
    # Format the recognizer instructions
    financial__data_query_instructions_formatted  = financial_data_query_instructions.format(user_title=user_title)

    response = ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        tags=["call_financial_data"]
    ).invoke([
        SystemMessage(content=financial__data_query_instructions_formatted),
        HumanMessage(content=str(query_data)),
    ])
    return {"final_output": response.content}


workflow = StateGraph(
    State, input=InputState, output=OutputState, config_schema=Configuration
)
workflow.add_node("query_financial_data", query_financial_data)
workflow.add_node("agent", call_llm)
workflow.add_edge("__start__", "query_financial_data")
workflow.add_edge("query_financial_data", "agent")
workflow.add_edge("agent", "__end__")

# 定义输出映射
workflow.set_entry_point("query_financial_data")
workflow.set_finish_point("agent")

query_financial_data = workflow.compile(name="financial_data_agent")


# if __name__ == "__main__":
#     result =  query_financial_data.invoke({"query": "查询性别是男的用户姓名和登录名"})
#     print(result)