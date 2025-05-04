import os
import dotenv

from dataclasses import dataclass, field

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from agent.prompts import generate_chart_instructions

# 加载环境变量
dotenv.load_dotenv()

@dataclass
class InputState:
    input: str

@dataclass
class State:
     input: str
     option: str = field(default_factory=str)

@dataclass
class OutputState:
    option: str

def call_llm(state: InputState):
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
    ).invoke([
        SystemMessage(content=generate_chart_instructions),
        HumanMessage(content=state.input)
    ])
    
    return {"option": response.content}


workflow = StateGraph(State, input=InputState, output=OutputState)

# Define the two nodes we will cycle between
workflow.add_node(call_llm)

workflow.add_edge(START, "call_llm")
workflow.add_edge("call_llm", END)

# 编译工作流
generate_chart_workflow = workflow.compile(name="generate_chart_workflow")