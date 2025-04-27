import os
import requests
import tempfile
import dotenv

from dataclasses import dataclass
from typing_extensions import Literal

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langgraph.graph import StateGraph

from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI

from agent.configuration import Configuration
from agent.state import State
from agent.prompts import corporate_legal_instructions

dotenv.load_dotenv()

@dataclass
class RiskAnalysisState:
    contract_content: str
    analysis_angle: str

@dataclass
class RiskAnalysisInputState:
    contract_file_path: str
    analysis_angle: str

@dataclass
class RiskAnalysisOutputState:
    risk_analysis_result: str


def load_contract_content(state: RiskAnalysisInputState) -> str:
    contract_file_path = state.contract_file_path
    writer = get_stream_writer()
    writer({"action": "读取合同内容"})
    try:
        # 下载网络URL的文件到临时文件
        response = requests.get(contract_file_path)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name

            # 从响应头的Content-Type判断
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type.lower():
                file_extension = 'pdf'
            elif 'word' in content_type.lower() or 'docx' in content_type.lower():
                file_extension = 'docx'
            
            if file_extension == 'pdf':
                # 使用PyMuPDFLoader加载PDF文件
                loader = PyMuPDFLoader(temp_file_path)
                documents = loader.load()
                print(f"成功加载PDF合同，共{len(documents)}页")
            elif file_extension in ['doc', 'docx']:
                # 使用UnstructuredWordDocumentLoader加载Word文件
                loader = UnstructuredWordDocumentLoader(temp_file_path)
                documents = loader.load()
            else:
                raise ValueError(f"不支持的文件类型: {file_extension}")
                
            # 提取文本内容
            contract_content = "\n\n".join([doc.page_content for doc in documents])
            
            # 删除临时文件
            os.unlink(temp_file_path)
        else:
            contract_content = "请提供正确的合同附件或合同路径"
    except Exception as e:
        contract_content = f"处理合同文件时出错: {str(e)}"
    writer({"action": "读取合同内容"})
    return {"contract_content": contract_content}

def analyze_contract_risk(state: RiskAnalysisState) -> str:
    analysis_angle = state.analysis_angle
    contract_content = state.contract_content
    writer = get_stream_writer()
    writer({"action": "分析合同内容"})
    response = ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        tags=["call_analyze_contract_risk"]
    ).invoke([
        SystemMessage(content="""You are a corporate legal expert with access to check contract risk.
    Analyze the legal risks in the contract text from perspectives including payment and settlement terms, delivery and acceptance terms, breach of contract liability, intellectual property clauses, confidentiality provisions, applicable law and dispute resolution clauses, and other terms.
            """),
        HumanMessage(content=f"请站在{analysis_angle}分析以下合同文本中的法律风险并给出相应的建议, 合同内容:\n\n{contract_content}")
    ])
    writer({"action": "分析合同内容"})
    return {"risk_analysis_result": response.content}

workflow_builder = StateGraph(state_schema=RiskAnalysisState, input=RiskAnalysisInputState, output=RiskAnalysisOutputState)
workflow_builder.add_node("load_contract_content", load_contract_content)
workflow_builder.add_node("analyze_contract_risk", analyze_contract_risk)

workflow_builder.add_edge("__start__", "load_contract_content")
workflow_builder.add_edge("load_contract_content", "analyze_contract_risk")
workflow_builder.add_edge("analyze_contract_risk", "__end__")

workflow_agent = workflow_builder.compile(name="contract_risk_analysis_agent")


@tool
def review_contract(contract_file_path: str, analysis_angle: str) -> str:
    """Review the contract content and identify potential legal risk points.
    
    Args:
        contract_file_path: 合同文件路径
        analysis_angle: 分析角度
    """
    result = workflow_agent.invoke({"contract_file_path": contract_file_path, "analysis_angle": analysis_angle})
    return result["risk_analysis_result"]


def call_llm(state, config: RunnableConfig):
    # Get the configuration
    configuration = Configuration.from_runnable_config(config)
    user_title = configuration.user_title

    # Format the recognizer instructions
    corporate_legal_instructions_formatted  = corporate_legal_instructions.format(user_title=user_title)

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
builder.add_node("tools", ToolNode([review_contract]))
builder.add_edge("__start__", "agent")
builder.add_conditional_edges(
    "agent",
    route_model_output,
)
builder.add_edge("tools", "agent")

corporate_legal_agent = builder.compile(name="corporate_legal_agent")

