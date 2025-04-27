import os
import dotenv

from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.types import Command
from langchain_core.messages import SystemMessage, HumanMessage

from agent.configuration import Configuration
from agent.prompts import prompter_instructions

from typing_extensions import Literal
from dataclasses import dataclass, field

from dashscope import ImageSynthesis
from http import HTTPStatus

dotenv.load_dotenv()


@dataclass
class InputState:
    prompt: str = field(default="")
    action: Literal["generate_image", "optimize_prompt"] = field(default="generate_image")
    num: int = field(default=1)
    size: str = field(default="1024x1024")

@dataclass
class State:
    prompt: str = field(default="")
    prompt_extend: str = field(default="")
    urls: list[str] = field(default_factory=list)
    size: str = field(default="1024x1024")
    num: int = field(default=1)

@dataclass
class OutputState:
    prompt_extend: str
    urls: list[str]

# Initialize the processable kinds
llm = ChatOpenAI(
    model_name="Qwen/Qwen2.5-72B-Instruct",
    openai_api_key=os.getenv("MODEL_SCOPE_API_KEY"),
    openai_api_base=os.getenv("MODEL_SCOPE_API_BASE"),
    temperature=0.0
)

def router(state: InputState, config: RunnableConfig) -> Command[Literal["generate_image", "optimize_prompt"]]:
    if state.action == "generate_image":
        goto="generate_image"
    else:
        goto="optimize_prompt"
        
    return Command(
        goto=goto
    )

    
def generate_image(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Genreate image"""
    configuration = Configuration.from_runnable_config(config)
    # Get State
    prompt = state.prompt
    num = state.num
    # generate image
    rsp = ImageSynthesis.call(api_key=os.getenv("DASHSCOPE_API_KEY"),
                            model="wanx2.1-t2i-turbo",
                            prompt=prompt,
                            n=num,
                            size='1024*1024')

    urls = []
    if rsp.status_code == HTTPStatus.OK:
        for result in rsp.output.results:
            urls.append(result.url)
    else:
        print('sync_call Failed, status_code: %s, code: %s, message: %s' %
            (rsp.status_code, rsp.code, rsp.message))
    
    return {"urls": urls}


def optimize_prompt(state: State, config: RunnableConfig) -> str:
    """Extend the prompt"""
    # Get the configuration
    configuration = Configuration.from_runnable_config(config)
    # Get State
    prompt = state.prompt
    # Call LLM
    result = llm.invoke([
        SystemMessage(content=prompter_instructions),
        HumanMessage(content=prompt)
    ])
    return {"prompt_extend": result.content}


# Define a new graph
workflow = StateGraph(State, input=InputState, output=OutputState, config_schema=Configuration)

# Add the node to the graph
workflow.add_node("router", router)
workflow.add_node("generate_image", generate_image)
workflow.add_node("optimize_prompt", optimize_prompt)

# Set the entrypoint as `call_model`
workflow.add_edge("__start__", "router")
workflow.add_edge("generate_image", "__end__")
workflow.add_edge("optimize_prompt", "__end__")

# Compile the workflow into an executable graph
generate_image = workflow.compile(name = "generate_image")
