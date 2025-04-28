import os
import dotenv

from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.types import Command
from langgraph.config import get_stream_writer
from langchain_core.messages import SystemMessage, HumanMessage

from agent.configuration import Configuration
from agent.prompts import prompter_instructions

from typing_extensions import Literal
from dataclasses import dataclass, field

from dashscope import ImageSynthesis
from http import HTTPStatus

# 加载环境变量
dotenv.load_dotenv()


@dataclass
class InputState:
    """输入状态类，定义图像生成的输入参数"""
    prompt: str = field(default="")
    action: Literal["generate_image", "optimize_prompt"] = field(default="generate_image")
    num: int = field(default=1)
    size: str = field(default="1024x1024")


@dataclass
class State:
    """状态类，定义图像生成过程中的状态"""
    prompt: str = field(default="")
    prompt_extend: str = field(default="")
    urls: list[str] = field(default_factory=list)
    size: str = field(default="1024x1024")
    num: int = field(default=1)


@dataclass
class OutputState:
    """输出状态类，定义图像生成的输出结果"""
    prompt_extend: str
    urls: list[str]


def router(state: InputState, config: RunnableConfig) -> Command[Literal["generate_image", "optimize_prompt"]]:
    """
    路由函数，根据输入状态决定下一步操作
    
    Args:
        state: 输入状态
        config: 可运行配置
        
    Returns:
        下一步操作的命令
    """
    if state.action == "generate_image":
        goto = "generate_image"
    else:
        goto = "optimize_prompt"
        
    return Command(
        goto=goto
    )

    
def generate_image(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    生成图像函数
    
    Args:
        state: 当前状态
        config: 可运行配置
        
    Returns:
        包含生成图像URL的字典
    """
    writer = get_stream_writer()
    writer({"action": "生成图像"})

    # 获取状态
    prompt = state.prompt
    num = state.num
    size = state.size.replace('x', '*')
    
    # 生成图像
    rsp = ImageSynthesis.call(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model="wanx2.1-t2i-turbo",
        prompt=prompt,
        n=num,
        size=size
    )

    urls = []
    if rsp.status_code == HTTPStatus.OK:
        for result in rsp.output.results:
            urls.append(result.url)
    else:
        print('生成图像失败, status_code: %s, code: %s, message: %s' %
            (rsp.status_code, rsp.code, rsp.message))

    writer({"action": "生成图像"})
    return {"urls": urls}


def optimize_prompt(state: State, config: RunnableConfig) -> Dict[str, str]:
    """
    优化提示词函数
    
    Args:
        state: 当前状态
        config: 可运行配置
        
    Returns:
        包含优化后提示词的字典
    """
    # 获取配置
    configuration = Configuration.from_runnable_config(config)
    # 获取状态
    prompt = state.prompt
    
    # 调用大语言模型
    result = ChatOpenAI(
        model_name="gpt-4",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0
    ).invoke([
        SystemMessage(content=prompter_instructions),
        HumanMessage(content=prompt)
    ])
    return {"prompt_extend": result.content}


# 定义新的图
workflow = StateGraph(State, input=InputState, output=OutputState, config_schema=Configuration)

# 添加节点到图
workflow.add_node("router", router)
workflow.add_node("generate_image", generate_image)
workflow.add_node("optimize_prompt", optimize_prompt)

# 设置入口点
workflow.add_edge("__start__", "router")
workflow.add_edge("generate_image", "__end__")
workflow.add_edge("optimize_prompt", "__end__")

# 编译工作流为可执行图
generate_image_workflow = workflow.compile(name="generate_image_workflow")
