import os
import dotenv

from typing_extensions import Literal

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI

from agent.configuration import Configuration
from agent.state import State
from agent.prompts import corporate_legal_instructions
from agent.contract_review_workflow import contract_review_workflow

# 加载环境变量
dotenv.load_dotenv()


@tool
def review_contract(contract_file_path: str, analysis_angle: str) -> str:
    """Review the contract content and identify potential legal risk points.
    
    Args:
        contract_file_path: 合同文件路径
        analysis_angle: 分析角度
    """
    # 调用合同风险分析工作流
    result = contract_review_workflow.invoke({"contract_file_path": contract_file_path, "analysis_angle": analysis_angle})
    return result["risk_analysis_result"]


def call_llm(state, config: RunnableConfig):
    """
    调用LLM处理用户请求
    
    Args:
        state: 当前状态
        config: 运行时配置
        
    Returns:
        包含LLM响应的字典
    """
    # 获取配置信息
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    # 格式化指令
    corporate_legal_instructions_formatted = corporate_legal_instructions.format(user_title=user_title)

    # 调用LLM并绑定工具
    response = ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        tags=["call_corporate_legal"]
    ).bind_tools([review_contract]).invoke([
        SystemMessage(content=corporate_legal_instructions_formatted),
        *state.messages
    ])
    return {"messages": [response]}


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    """
    根据模型输出决定下一步路由
    
    Args:
        state: 当前状态
        
    Returns:
        下一步路由目标
    """
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )
    # 如果没有工具调用，则结束
    if not last_message.tool_calls:
        return "__end__"
    # 否则执行请求的工具
    return "tools"


# 构建主工作流
builder = StateGraph(State, config_schema=Configuration)
builder.add_node("agent", call_llm)
builder.add_node("tools", ToolNode([review_contract]))

# 定义工作流节点间的连接
builder.add_edge("__start__", "agent")
builder.add_conditional_edges(
    "agent",
    route_model_output,
)
builder.add_edge("tools", "agent")

# 编译企业法务代理
corporate_legal_agent = builder.compile(name="corporate_legal_agent")
