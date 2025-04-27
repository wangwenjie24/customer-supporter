import os
import dotenv
import requests

from typing_extensions import Literal

from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig

from agent.configuration import Configuration
from agent.state import State
from agent.prompts import financial_instructions

dotenv.load_dotenv()

@tool
def query_policy(query: str) -> str:
    """Query information about company financial related policy."""
    writer = get_stream_writer()
    writer({"action": "检索财务制度"})
    
    klResponse = requests.get(f'http://47.251.17.61/saiyan-ai/ai/knowledge/1914967815086206976/search?query={query}')
    data = klResponse.json()['data']
    result = ''
    for index,item in enumerate(data):
        result += f'片段{index + 1}：{item["content"]}\n'
    if not result:
        result = '抱歉，没有查询到相关的财务制度或政策信息'
        
    writer({"action": "检索财务制度"})
    return result

def call_llm(state, config: RunnableConfig):
    # Get the configuration
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    # Format the recognizer instructions
    financial_instructions_formatted  = financial_instructions.format(user_title=user_title)

    response = ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        tags=["call_financial"]
    ).bind_tools([query_policy]).invoke([
        SystemMessage(content=financial_instructions_formatted),
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


builder = StateGraph(State)
builder.add_node("agent", call_llm)
builder.add_node("tools", ToolNode([query_policy]))
builder.add_edge("__start__", "agent")
builder.add_conditional_edges(
    "agent",
    route_model_output,
)
builder.add_edge("tools", "agent")

financial_agent = builder.compile(name="financial_agent")