import dotenv

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from agent.corporate_legal_agent import corporate_legal_agent
from agent.configuration import Configuration
from agent.hr_agent import hr_agent
from agent.financial_agent import financial_agent
from agent.receipt_regnoice_workflow import receipt_regnoice_workflow
from agent.meeting_summary_workflow import meeting_summary_workflow
from agent.financial_data_agent import financial_data_agent
from agent.hr_data_agent import hr_data_agent
from agent.generate_image import generate_image_workflow
from agent.state import State
from agent.prompts import financial_data_researcher_instructions, hr_data_researcher_instructions

# 加载环境变量
dotenv.load_dotenv()


def router(state: State) -> Command[Literal["hr_agent", "financial_agent", "corporate_legal_agent", "receipt_regnoice", "generate_image", "finalcial_data_research", "hr_data_research", "meeting_summary_agent"]]:
    """
    路由函数，根据state.action决定将请求路由到哪个代理
    
    Args:
        state: 当前状态对象
        
    Returns:
        Command对象，指定下一步执行的节点和更新的状态
    """
    
    if state.action == "hr_agent":
        return Command(
            update={"messages": state.messages[-1]},
            goto="hr_agent"
        )
    elif state.action == "financial_agent":
        return Command(
            update={"messages": state.messages[-1]},
            goto="financial_agent"
        )
    elif state.action == "corporate_legal_agent":
        return Command(
            update={"messages": state.messages[-1]},
            goto="corporate_legal_agent"
        )
    elif state.action == "receipt_regnoice_agent":
        return Command(
            update={"messages": f"识别并提取票据内容, 票据url：{state.receipt_image}", "receipt_image": state.receipt_image},
            goto="receipt_regnoice"
        )
    elif state.action == "generate_image_agent":
        return Command(
            update={"messages": f"生成图片,{state.messages[-1]}"},
            goto="generate_image"
        )
    elif state.action == "financial_data_agent":
      return Command(
            update={"messages": state.messages},
            goto="finalcial_data_research"
        )
    elif state.action == "hr_data_agent":
      return Command(
            update={"messages": state.messages},
            goto="hr_data_research"
        )
    elif state.action == "meeting_summary_agent":
      return Command(
            update={"messages": state.messages[-1]},
            goto="meeting_summary"
        )
    else:
        raise ValueError(f"Invalid action: {state.action}")


def receipt_regnoice(state: State):
    """
    票据识别代理，识别票据图片并返回结构化数据
    
    Args:
        state: 当前状态对象
        
    Returns:
        包含识别结果的字典
    """
    result = receipt_regnoice_workflow.invoke({"receipt_image": state.receipt_image, "should_convert": True})
    return {"messages": [AIMessage(content=result["text_output"])], "receipt_json": result["json_output"]}


def generate_image(state: State):
    """
    图片生成代理，根据提示生成图片
    
    Args:
        state: 当前状态对象
        
    Returns:
        包含生成图片URL的字典
    """
    result = generate_image_workflow.invoke({"prompt": state.messages[-1].content, "action": "generate_image"})
    return {"messages": [AIMessage(content=result["urls"][0])]}


def meeting_summary(state: State):
    """
    会议总结代理，根据会议记录生成总结
    
    Args:
        state: 当前状态对象
    """
    result = meeting_summary_workflow.invoke({"url": state.messages[-1].content})
    return {"messages": [AIMessage(content=result["final_summary"])]}


def finalcial_data_research(state: State, config: RunnableConfig):
    """
    财务数据查询代理，查询财务相关数据
    
    Args:
        state: 当前状态对象
        config: 运行配置
        
    Returns:
        包含查询结果的字典
    """
    # 获取流式写入器用于实时反馈
    writer = get_stream_writer()
    writer({"action": "检索财务数据"})
    # 获取配置信息
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title
        
    # 格式化指令
    financial_data_researcher_instructions_formatted = financial_data_researcher_instructions.format(user_title=user_title)
        
    # 构造消息列表
    messages = [
        SystemMessage(content=financial_data_researcher_instructions_formatted),
        *state.messages
    ]
    
    # 调用代理
    result = financial_data_agent.invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": config["configurable"]["thread_id"]}}
    )

    return {"messages": [result["messages"][-1]]}


def hr_data_research(state: State, config: RunnableConfig):
    """
    人资数据查询代理，查询人资相关数据
    
    Args:
        state: 当前状态对象
        config: 运行配置
        
    Returns:
        包含查询结果的字典
    """
    # 获取流式写入器用于实时反馈
    writer = get_stream_writer()
    writer({"action": "检索人资数据"})

    # 获取配置信息
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title
        
    # 格式化指令
    hr_data_researcher_instructions_formatted = hr_data_researcher_instructions.format(user_title=user_title)
        
    # 构造消息列表
    messages = [
        SystemMessage(content=hr_data_researcher_instructions_formatted),
        *state.messages
    ]
    
    # 调用代理
    result = hr_data_agent.invoke(
        {"messages": messages},
        config={"configurable": {"thread_id": config["configurable"]["thread_id"]}}
    )
    
    return {"messages": [result["messages"][-1]]}


# 构建状态图
builder = StateGraph(State, config_schema=Configuration)

# 添加节点
builder.add_node("router", router)
builder.add_node("hr_agent", hr_agent)
builder.add_node("financial_agent", financial_agent)
builder.add_node("corporate_legal_agent", corporate_legal_agent)
builder.add_node("finalcial_data_research", finalcial_data_research)
builder.add_node("generate_image", generate_image)
builder.add_node("receipt_regnoice", receipt_regnoice)
builder.add_node("hr_data_research", hr_data_research)

# 添加边，定义节点间的连接关系
builder.add_edge("__start__", "router")
builder.add_edge("hr_agent", "__end__")
builder.add_edge("financial_agent", "__end__")
builder.add_edge("corporate_legal_agent", "__end__")
builder.add_edge("finalcial_data_research", "__end__")
builder.add_edge("hr_data_research", "__end__")
builder.add_edge("receipt_regnoice", "__end__")
builder.add_edge("generate_image", "__end__")

# 编译并运行图
checkpointer = MemorySaver()
graph = builder.compile(name="Customer Supporter", checkpointer=checkpointer)

# 示例请求：
# "请站在甲方角度分析以下合同文本中的法律风险。合同路径：http://47.251.17.61/saiyan-ai/system/file/downloadById?id=1914982139343204352"

# if __name__ == "__main__":
#     # inputs = {"messages": [("user", "张剑锋所属单位及部门以及司龄是多少？")], "action": "hr_data_agent"}
#     inputs = {"messages": [("user", "查询2024年2月佛山电器照明股份有限公司营业收入同比增长多少？")], "action": "financial_data_agent"}
#     # inputs = {"messages": [("user", "   请站在甲方角度分析以下合同文本中的法律风险。合同路径：http://47.251.17.61/saiyan-ai/system/file/downloadById?id=1914982139343204352")], "action": "corporate_legal_agent"}
#     # inputs = {"messages": [("user", "")], "action": "receipt_regnoice_agent", "receipt_image":"https://cdn.nlark.com/yuque/0/2025/png/34020404/1741869817307-6e320d85-410f-4a16-aa6a-60e03dfa0efc.png?x-oss-process=image%2Fformat%2Cwebp%2Fresize%2Cw_1423%2Climit_0"}
#     current_agent = None
#     for stream_mode, streamed_output in graph.stream(inputs, stream_mode=["messages", "custom", "values"], config={"configurable": {"thread_id": "2", "user_id": "10001", "user_title": "万书记"}}):
#         # 如果是代理的消息，显示代理名称和内容

#         if stream_mode == "custom":
#             print(streamed_output)
#         # print(stream_mode, streamed_output)
#         if stream_mode == "messages" and isinstance(streamed_output, tuple) and len(streamed_output) > 1:
#             chunk, metadata = streamed_output
#             if metadata.get("langgraph_node", "") == "agent" or metadata.get("langgraph_node", "") == "finalinze_output" or metadata.get("langgraph_node", "") == "generate_image_agent":
#                 print(chunk.content, end="", flush=True)


#         # if stream_mode == "messages" and isinstance(streamed_output, tuple) and len(streamed_output) > 1:
#         #     chunk, metadata = streamed_output
#         #     if isinstance(chunk, AIMessageChunk) and chunk.content and "call_supervisor" not in metadata.get("tags", []) and "call_analyze_contract_risk" not in metadata.get("tags", []):
#         #         print(chunk.content, end="", flush=True)


# if __name__ == "__main__":
#     query = "查询2024年2月佛山电器照明股份有限公司营业收入同比增长多少？"

#     result = financial_data_agent.invoke({"messages": query})
#     print(result)