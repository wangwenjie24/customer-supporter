import os
import requests
import tempfile
import dotenv

from dataclasses import dataclass

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langgraph.graph import StateGraph

from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI

# 加载环境变量
dotenv.load_dotenv()

# 定义合同风险分析状态类
@dataclass
class RiskAnalysisState:
    contract_content: str    # 合同内容
    analysis_angle: str      # 分析角度

# 定义合同风险分析输入状态类
@dataclass
class RiskAnalysisInputState:
    contract_file_path: str  # 合同文件路径
    analysis_angle: str      # 分析角度

# 定义合同风险分析输出状态类
@dataclass
class RiskAnalysisOutputState:
    risk_analysis_result: str  # 风险分析结果



def load_contract_content(state: RiskAnalysisInputState) -> str:
    """
    加载合同内容
    
    Args:
        state: 包含合同文件路径的输入状态
        
    Returns:
        包含合同内容的字典
    """
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

            # 从响应头的Content-Type判断文件类型
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type.lower():
                file_extension = 'pdf'
            else:
                raise ValueError("只支持PDF格式的合同文件")
            
            # 使用PyMuPDFLoader加载PDF文件
            loader = PyMuPDFLoader(temp_file_path)
            documents = loader.load()
            print(f"成功加载PDF合同，共{len(documents)}页")
                
            # 提取文本内容
            contract_content = "\n\n".join([doc.page_content for doc in documents])
            
            # 删除临时文件
            os.unlink(temp_file_path)
        else:
            contract_content = "请提供正确的合同附件或合同路径！"
    except Exception as e:
        contract_content = f"处理合同文件时出错: {str(e)}"
    writer({"action": "读取合同内容"})
    return {"contract_content": contract_content}


def analyze_contract_risk(state: RiskAnalysisState) -> str:
    """
    分析合同风险
    
    Args:
        state: 包含合同内容和分析角度的状态
        
    Returns:
        包含风险分析结果的字典
    """
    analysis_angle = state.analysis_angle
    contract_content = state.contract_content
    writer = get_stream_writer()
    writer({"action": "分析合同内容"})
    
    # 调用LLM分析合同风险
    response = ChatOpenAI(
        model_name="gpt-4o-mini",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.0,
        tags=["call_analyze_contract_risk"]
    ).invoke([
        SystemMessage(content="""You are a corporate legal expert with access to check contract risk.
    Analyze the legal risks in the contract text from perspectives including payment and settlement terms, delivery and acceptance terms, breach of contract liability, intellectual property clauses, confidentiality provisions, applicable law and dispute resolution clauses, and other terms.
            """),
        HumanMessage(content=f"请站在{analysis_angle}分析以下合同文本中的法律风险并给出相应的建议，建议需要具体化，可以举例说明。合同内容:\n\n{contract_content}")
    ])
    writer({"action": "分析合同内容"})
    return {"risk_analysis_result": response.content}


# 构建合同风险分析工作流
workflow = StateGraph(state_schema=RiskAnalysisState, input=RiskAnalysisInputState, output=RiskAnalysisOutputState)
workflow.add_node("load_contract_content", load_contract_content)
workflow.add_node("analyze_contract_risk", analyze_contract_risk)

# 定义工作流节点间的连接
workflow.add_edge("__start__", "load_contract_content")
workflow.add_edge("load_contract_content", "analyze_contract_risk")
workflow.add_edge("analyze_contract_risk", "__end__")

# 编译工作流
contract_review_workflow = workflow.compile(name="contract_review_workflow")