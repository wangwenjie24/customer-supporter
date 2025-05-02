import os
import dotenv
import json
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from langgraph.config import get_stream_writer

from dataclasses import field
from typing import Any, Optional
from typing_extensions import TypedDict

from agent.configuration import Configuration
from agent.prompts import extractor_instructions, categorizer_instructions, receipt_instructions
from agent.utils import image_to_base64
from agent.config import receipt_config

# 加载环境变量
dotenv.load_dotenv()

# 定义图像处理的像素范围
min_pixels = 128 * 28 * 28  # 最小像素数
max_pixels = 4096 * 28 * 28  # 最大像素数


class InputState(TypedDict):
    """输入状态定义"""
    receipt_image: str  # 票据图片路径或URL
    should_convert: bool = True  # 是否需要转换为文本输出


class State(TypedDict):
    """工作流状态定义"""
    receipt_image: str  # 票据图片路径或URL
    running_category: str  # 当前识别的票据类型
    should_convert: bool  # 是否需要转换为文本输出
    text_output: Optional[dict[str, Any]] = field(default=None)  # 文本输出结果
    json_output: Optional[dict[str, Any]] = field(default=None)  # JSON输出结果


class OutputState(TypedDict):
    """输出状态定义"""
    text_output: dict[str, Any]  # 文本格式的输出结果
    json_output: dict[str, Any]  # JSON格式的输出结果


def categorize(state: State, config: RunnableConfig) -> Command[Literal["extract", "__end__"]]:
    """识别票据类型
    
    根据图片内容识别票据类型，决定后续处理流程
    
    Args:
        state: 当前状态
        config: 运行配置
        
    Returns:
        Command对象，指定下一步执行的节点和更新的状态
    """
    writer = get_stream_writer()
    writer({"action": "识别票据类型"})
    
    # 初始化可处理的票据类型列表
    processable_categories = ""
    for category, config_data in receipt_config.items():
        processable_categories += category + ": " + config_data["feature"] + "\n"
    
    # 格式化分类器指令
    categorizer_instructions_formatted = categorizer_instructions.format(
        processable_categories=processable_categories
    )
    
    # 调用大模型进行票据类型识别
    result = ChatOpenAI(
        model_name="qwen2.5-vl-72b-instruct",
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base=os.getenv("DASHSCOPE_API_BASE"),
        temperature=0.0
    ).invoke([
        SystemMessage(content=categorizer_instructions_formatted),
        HumanMessage(content=[{
            "type": "image_url",
            "min_pixels": min_pixels,
            "max_pixels": max_pixels,
            "image_url": {"url": image_to_base64(state["receipt_image"])}
        }])
    ])

    # 处理识别结果
    if result.content == "unknown":
        writer({"action": "识别票据类型"})
        return Command(
            update={"text_output": f"不支持的票据类型"},
            goto="__end__"
        )
    else:
        writer({"action": "识别票据类型"})
        return Command(
            update={"running_category": result.content, "receipt_image": state["receipt_image"]},
            goto="extract"
        )


def extract(state: State, config: RunnableConfig) -> Command[Literal["finalinze_output"]]:
    """提取票据数据
    
    根据识别的票据类型，从图片中提取结构化数据
    
    Args:
        state: 当前状态
        config: 运行配置
        
    Returns:
        Command对象，指定下一步执行的节点和更新的状态
    """
    writer = get_stream_writer()
    writer({"action": "提取票据信息"})
    
    # 获取状态信息
    receipt_image = state["receipt_image"]
    category = state["running_category"]
    
    # 格式化提取器指令
    extractor_instructions_formatted = extractor_instructions.format(
        category=category,
        rules="\n".join(["- " + rule for rule in receipt_config[category]["rules"]]),
        output_format=receipt_config[category]["output_format"],
        examples=receipt_config[category]["examples"]
    )
    
    # 调用大模型提取票据信息
    result = ChatOpenAI(
        model_name="qwen2.5-vl-72b-instruct",
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base=os.getenv("DASHSCOPE_API_BASE"),
        temperature=0.0
    ).invoke([
        SystemMessage(content=extractor_instructions_formatted),
        HumanMessage(content=[{
            "type": "image_url",
            "min_pixels": min_pixels,
            "max_pixels": max_pixels,
            "image_url": {"url": image_to_base64(receipt_image)}
        }])
    ])
    
    # 解析提取的数据
    extracted_data = json.loads(result.content)
    writer({"action": "提取票据信息"})
    return Command(
        update={"json_output": extracted_data},
        goto="finalinze_output"
    )
    

def finalinze_output(state: State, config: RunnableConfig):
    """将JSON数据转换为可读文本
    
    根据配置决定是否将JSON数据转换为人类可读的文本格式
    
    Args:
        state: 当前状态
        config: 运行配置
        
    Returns:
        包含处理结果的字典
    """
    # 判断是否需要转换为文本输出
    if state.get("should_convert", True):
        # 获取状态信息
        json_output = state["json_output"]
        category = state["running_category"]
        
        # 将JSON转换为字符串
        json_str = json.dumps(json_output, ensure_ascii=False)
        
        # 格式化输出指令
        receipt_instructions_formatted = receipt_instructions.format(
            finalize_out_example=receipt_config[category]["finalize_out_example"]
        )
        
        # 调用大模型生成可读文本
        response = ChatOpenAI(
            model_name=os.getenv("OPENROUTER_MODEL_NAME"),
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base=os.getenv("OPENROUTER_API_BASE"),
            temperature=0.0,
            tags=["call_regnoice_receipt"]
        ).invoke([
            SystemMessage(content=receipt_instructions_formatted),
            HumanMessage(content=json_str)
        ])
        return {"text_output": response.content}
    else:
        return {"text_output": ""}


# 创建工作流图
workflow = StateGraph(
    State, input=InputState, output=OutputState, config_schema=Configuration
)

# 添加节点
workflow.add_node("categorize", categorize)
workflow.add_node("extract", extract)
workflow.add_node("finalinze_output", finalinze_output)

# 添加边，定义节点间的连接关系
workflow.add_edge("__start__", "categorize")
workflow.add_edge("finalinze_output", "__end__")

# 编译工作流
receipt_regnoice_workflow = workflow.compile(name="receipt_regnoice_workflow")