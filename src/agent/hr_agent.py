import os
import dotenv
import requests

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from agent.configuration import Configuration
from agent.state import State
from agent.prompts import hr_instructions

from typing import Literal

dotenv.load_dotenv()

@tool
def query_policy(query: str) -> str:
    """Query information about company HR related policy.
    
    """
    writer = get_stream_writer()
    writer({"action": "检索人力资源制度"})
    klResponse = requests.get(f'http://47.251.17.61/saiyan-ai/ai/knowledge/1914967712749383680/search?query={query}')
    data = klResponse.json()['data']
    result = ''
    for index,item in enumerate(data):
        result += f'片段{index + 1}：{item["content"]}\n'
    if not result:
        result = '抱歉，没有查询到相关的HR制度或政策信息。'
    writer({"action": "检索人力资源制度"})
    return result

@tool
def query_position(name: str) -> str:
    """Query employee position information.

    Args:
        name (str): 员工姓名。
    """
    return f"{name}的岗位信息：总经理"
    # writer = get_stream_writer()
    # writer({"action": "查询岗位信息"})
    # klResponse = requests.get(f'http://47.251.17.61/saiyan-ai/rz/queryUserPost?name={name}')
    # data = klResponse.json()['data']
    # if not data or len(data) == 0:
    #     writer({"action": "查询岗位信息"})
    #     return f"抱歉，未找到{name}的岗位信息。"
    # else:
    #     writer({"action": "查询岗位信息"})
    #     return f"{name}的岗位信息：{data}"

@tool
def query_department_head(department: str) -> str:
    """Query department head information.
    
    Args:
        department (str): 部门名称。
    """
    writer = get_stream_writer()
    writer({"action": "查询部门负责人"})
    
    klResponse = requests.get(f'http://47.251.17.61/saiyan-ai/rz/queryDeptManager?name={department}')
    data = klResponse.json()['data']
    if not data or len(data) == 0:
        writer({"action": "查询部门负责人"})
        return f"抱歉，未找到{department}的负责人信息。"
    else:
        writer({"action": "查询部门负责人"})
        return f"{department}的负责人是：{data}"

@tool
def query_invalid_attendance() -> str:
    """Query employees with invalid attendance records.
    
    Args:
        department (str): 部门名称。
    """
    writer = get_stream_writer()
    writer({"action": "查询打卡记录无效人员"})
    
    klResponse = requests.get(f'http://47.251.17.61/saiyan-ai/rz/queryKq')
    data = klResponse.json()['data']
    if not data or len(data) == 0:
        writer({"action": "查询打卡记录无效人员"})
        return f"抱歉，未找到的打卡记录无效人员信息。"
    else:
        writer({"action": "查询打卡记录无效人员"})
        return f"打卡记录无效人员是：{data}"


def call_llm(state, config: RunnableConfig):
    # Get the configuration
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    # Format the recognizer instructions
    hr_instructions_formatted  = hr_instructions.format(user_title=user_title)

    response = ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        tags=["call_hr"]
    ).bind_tools([query_policy, query_position, query_department_head, query_invalid_attendance]).invoke([
        SystemMessage(content=hr_instructions_formatted),
        *state.messages
    ])
    return {"messages": [response]}


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )
    # If there is no tool call, then we finish
    if not last_message.tool_calls:
        return "__end__"
    # Otherwise we execute the requested actions
    return "tools"


builder = StateGraph(State, config_schema=Configuration)
builder.add_node("agent", call_llm)
builder.add_node("tools", ToolNode([query_policy, query_position, query_department_head, query_invalid_attendance]))
builder.add_edge("__start__", "agent")
builder.add_conditional_edges(
    "agent",
    route_model_output,
)
builder.add_edge("tools", "agent")

hr_agent = builder.compile(name="hr_agent")

