import dotenv

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage

from agent.corporate_legal_agent import corporate_legal_agent
from agent.configuration import Configuration
from agent.hr_agent import hr_agent
from agent.financial_agent import financial_agent
from agent.receipt_regnoice_workflow import receipt_regnoice_workflow
from agent.finacial_data_query_workflow import finacial_data_query_workflow
from agent.generate_image import generate_image_workflow
from agent.state import State

# 加载环境变量
dotenv.load_dotenv()


def router(state: State) -> Command[Literal["hr_agent", "financial_agent", "corporate_legal_agent", "receipt_regnoice_agent", "generate_image_agent", "financial_data_agent"]]:
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
            goto="receipt_regnoice_agent"
        )
    elif state.action == "generate_image_agent":
        return Command(
            update={"messages": f"生成图片,{state.messages[-1]}"},
            goto="generate_image_agent"
        )
    elif state.action == "financial_data_agent":
        return Command(
            update={"query": {state.messages[-1].content}},
            goto="financial_data_agent"
        )
    else:
        raise ValueError(f"Invalid action: {state.action}")


def receipt_regnoice_agent(state: State):
    """
    票据识别代理，识别票据图片并返回结构化数据
    
    Args:
        state: 当前状态对象
        
    Returns:
        包含识别结果的字典
    """
    result = receipt_regnoice_workflow.invoke({"receipt_image": state.receipt_image, "should_convert": True})
    return {"messages": [AIMessage(content=result["text_output"])], "receipt_json": result["json_output"]}


def generate_image_agent(state: State):
    """
    图片生成代理，根据提示生成图片
    
    Args:
        state: 当前状态对象
        
    Returns:
        包含生成图片URL的字典
    """
    result = generate_image_workflow.invoke({"prompt": state.messages[-1].content, "action": "optimize_prompt"})
    return {"messages": [AIMessage(content=result["urls"][0])]}


def financial_data_agent(state: State):
    """
    财务数据查询代理，查询财务相关数据
    
    Args:
        state: 当前状态对象
        
    Returns:
        包含查询结果的字典
    """
    result = finacial_data_query_workflow.invoke({"query": state.messages[-1].content})
    return {"messages": [AIMessage(content=result["final_output"])]}


# 构建状态图
builder = StateGraph(State, config_schema=Configuration)

# 添加节点
builder.add_node("router", router)
builder.add_node("hr_agent", hr_agent)
builder.add_node("financial_agent", financial_agent)
builder.add_node("corporate_legal_agent", corporate_legal_agent)
builder.add_node("financial_data_agent", financial_data_agent)
builder.add_node("generate_image_agent", generate_image_agent)
builder.add_node("receipt_regnoice_agent", receipt_regnoice_agent)

# 添加边，定义节点间的连接关系
builder.add_edge("__start__", "router")
builder.add_edge("hr_agent", "__end__")
builder.add_edge("financial_agent", "__end__")
builder.add_edge("corporate_legal_agent", "__end__")
builder.add_edge("financial_data_agent", "__end__")
builder.add_edge("receipt_regnoice_agent", "__end__")
builder.add_edge("generate_image_agent", "__end__")

# 编译并运行图
checkpointer = MemorySaver()
graph = builder.compile(name="Customer Supporter", checkpointer=checkpointer)

# 示例请求：
# "请站在甲方角度分析以下合同文本中的法律风险。合同路径：http://47.251.17.61/saiyan-ai/system/file/downloadById?id=1914982139343204352"

# if __name__ == "__main__":
#     inputs = {"messages": [("user", "你是谁？")], "action": "receipt_agent", "receipt_image": "https://cdn.nlark.com/yuque/0/2025/png/34020404/1744543760660-5ad0c14a-4689-48bd-9fa8-efb2bf0c3323.png?x-oss-process=image%2Fformat%2Cwebp%2Fresize%2Cw_1426%2Climit_0"}
#     # inputs = {"messages": [("user", "   请站在甲方角度分析以下合同文本中的法律风险。合同路径：http://47.251.17.61/saiyan-ai/system/file/downloadById?id=1914982139343204352")], "action": "corporate_legal_agent"}



#     current_agent = None
#     for stream_mode, streamed_output in graph.stream(inputs, stream_mode=["messages", "custom", "values"], config={"configurable": {"thread_id": "2", "user_id": "10001", "user_title": "万书记"}}):
#         # 如果是代理的消息，显示代理名称和内容

#         if stream_mode == "custom":
#             print(streamed_output)
#         # print(stream_mode, streamed_output)
#         if stream_mode == "messages" and isinstance(streamed_output, tuple) and len(streamed_output) > 1:
#             chunk, metadata = streamed_output
#             if metadata.get("langgraph_node", "") == "agent" or metadata.get("langgraph_node", "") == "finalinze_output":
#                 print(chunk.content, end="", flush=True)


        # if stream_mode == "messages" and isinstance(streamed_output, tuple) and len(streamed_output) > 1:
        #     chunk, metadata = streamed_output
        #     if isinstance(chunk, AIMessageChunk) and chunk.content and "call_supervisor" not in metadata.get("tags", []) and "call_analyze_contract_risk" not in metadata.get("tags", []):
        #         print(chunk.content, end="", flush=True)