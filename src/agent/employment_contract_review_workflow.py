import os
import requests
import tempfile
import dotenv
import pymupdf4llm

from dataclasses import dataclass, field

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph

from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI

from agent.utils import process_markdown


evaluate_instructions = """你是一名人资专家，熟悉《劳动合同法》及相关劳动法规，擅长从专业角度审查劳动合同条款，识别法律漏洞、权责失衡、表述模糊等问题，并提出合规建议，帮助企业规避用工风险。

你是一名人资专家，熟悉《中华人民共和国劳动合同法》《社会保险法》《劳动争议调解仲裁法》等相关法律法规，擅长从专业角度审查劳动合同条款，识别法律漏洞、权责失衡、表述模糊等问题，并提出合规建议，帮助企业规避用工风险。

Task:
请根据用户提供的劳动合同内容，按照以下维度逐项审查合同条款：
{review_dimensions}

对每个维度进行风险等级评估，并输出包含以下字段的 JSON 数组：
- risk_level：风险等级（取值为“无风险”、“低风险”、“中风险”、“高风险”）
- dimension：审核维度
- risk_point：发现的具体风险点
- recommendation：详细、具体的合规建议，应包括法律依据、修改方向和操作建议。

Risk Level Criteria:
请根据以下标准判断每个维度的风险等级：
"无风险"：条款表述清晰、内容完整、完全符合现行法律法规要求，不存在潜在法律争议或用工风险。
"低风险"：条款基本合规，但存在轻微表述不规范、格式瑕疵或建议优化项，不会引发实质性法律风险。
"中风险"：条款存在表述模糊、遗漏关键信息或部分不符合法律规定的情形，可能引起劳动争议或影响合同效力，需及时修正。
"高风险"：条款违反现行法律法规强制性规定，存在明显侵权行为或严重权责失衡，极有可能导致合同无效、赔偿甚至行政处罚。

Format:
请严格按照如下 JSON 格式返回数组，不要包含任何额外信息（如解释、说明、markdown格式等）：

[
  {{
    "risk_level": "中风险",
    "dimension": "合同期限与试用期约定",
    "risk_point": "试用期超过法定上限。",
    "recommendation": "根据《劳动合同法》第十九条，三年以上固定期限合同试用期不得超过六个月，请调整试用期长度。同时应在合同中明确试用期起止日期及考核标准，避免因认定"
  }},
  ...
]

Constraints:
- 使用中文输出。
- 不要添加任何额外字段或说明性文字。
- 若某项条款缺失或表述不清，默认标注为“中风险”或“高风险”。
- 所有建议应基于现行有效的法律法规，避免引用已废止条款。
- recommendation 字段必须提供详细建议，包括但不限于：
  - 明确指出适用的法律条款；
  - 建议如何修改或完善条款；
  - 提示可能的法律后果或操作注意事项。
"""

reporter_instructions = """你是一名人资专家，擅长分析和评估劳动合同内容。你具备扎实的劳动法知识、合规意识和企业管理经验，能够基于用户提供的各维度审核信息，生成一份结构清晰、逻辑严谨、语言专业的劳动合同评估报告。

Task:
请根据用户提供的劳动合同审核数据，生成一份通用格式的《劳动合同评估报告》。你需要完成以下任务：

1. 理解并整理用户提供的各项审核维度与结论；
2. 对每一项审核内容进行专业分析评价，指出潜在风险或改进点；
3. 总结整体合同情况，提出改进建议；
4. 输出符合规范格式的专业报告，不预设具体评估条目名称，而是根据实际输入数据动态生成对应章节。

Format:
请按照以下标准结构组织并输出报告内容：

## 劳动合同评估报告

### 一、评估背景
简述本次评估的目的、依据及范围。

## #二、审核维度概览
列出用户提供的所有审核维度及其初步判断结果。

### 三、详细评估内容
对每个审核维度逐一进行分析，每项内容应包含：
- 审核结果（用户提供）
- 评估意见（你的专业判断）

[注意：此部分应根据用户输入的审核项动态生成，不预设固定条目]

## 四、综合评估结论
对整份劳动合同的整体合规性、完整性、公平性及风险程度做出总结性评价。

## 五、改进建议
提出具体的修改建议或优化方向，以提升合同质量、降低法律风险。

Constraints:
- 用户将提供一个结构化数据（如 JSON 格式）作为输入，包含多个审核维度及其审核结果；
- 请根据这些数据生成对应的“详细评估内容”条目；
- 语言应保持正式、中立、专业；
- 若某项审核内容缺失，请注明“未提供”，并建议补充；
- 在评估意见中引用法律法规时，请注明来源。
- 不使用总结性语句，所有内容均以可执行、可参考的方式呈现。

"""

# 加载环境变量
dotenv.load_dotenv()

# 定义合同风险分析状态类
@dataclass
class RiskAnalysisState:
    contract_file_path: str  # 合同文件路径
    contract_content: str = ""    # 合同内容
    review_dimensions: list[str] = field(default_factory=list)    # 审查纬度
    review_result: str = ""  # 审核结果

# 定义合同风险分析输入状态类
@dataclass
class RiskAnalysisInputState:
    contract_file_path: str  # 合同文件路径
    review_dimensions: list[str]    # 审查纬度

# 定义合同风险分析输出状态类
@dataclass
class RiskAnalysisOutputState:
    review_result: str  # 审核结果
    report_url: str  # 审核报告url


def load(state: RiskAnalysisState) -> str:
    """加载合同内容"""
    contract_file_path = state.contract_file_path
    writer = get_stream_writer()
    writer({"action": {"type": "load", "state": "start"}})
    try:
        # 下载网络URL的文件到临时文件
        response = requests.get(contract_file_path)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name

            # 使用pymupdf4llm加载PDF文件
            contract_content = pymupdf4llm.to_markdown(temp_file_path)
            
            # 删除临时文件
            os.unlink(temp_file_path)
        else:
            contract_content = "请提供正确的合同附件或合同路径！"
    except Exception as e:
        contract_content = f"处理合同文件时出错: {str(e)}"
    writer({"action": {"type": "load", "state": "end"}})
    return {"contract_content": contract_content}

def evaluate(state: RiskAnalysisState) -> str:
    """
    评估合同风险
    """
    writer = get_stream_writer()
    writer({"action": {"type": "evaluate", "state": "start"}})

    contract_content = state.contract_content
    review_dimensions = state.review_dimensions
    evaluate_instructions_formatted = evaluate_instructions.format(
        review_dimensions="\n".join(["- " + rule for rule in review_dimensions]),
    )

    # 调用LLM分析合同风险
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
        tags=["call_evaluate"]
    ).invoke([
        SystemMessage(content=evaluate_instructions_formatted),
        HumanMessage(content=contract_content)
    ])
    writer({"action": {"type": "evaluate", "state": "end"}})
    return {"review_result": response.content}



def generate_report(state: RiskAnalysisState) -> str:
    """
    生成审核报告
    """
    writer = get_stream_writer()
    writer({"action": {"type": "generate_report", "state": "start"}})

    review_result = state.review_result

    # 调用LLM分析合同风险
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
        tags=["call_generate_report"]
    ).invoke([
        SystemMessage(content=reporter_instructions),
        HumanMessage(content=review_result)
    ])

    url = process_markdown(response.content, 'docx', True, "劳动合同评估报告")
    writer({"action": {"type": "generate_report", "state": "end"}})
    return {"report_url": url}


# 构建合同风险分析工作流
workflow = StateGraph(state_schema=RiskAnalysisState, input=RiskAnalysisInputState, output=RiskAnalysisOutputState)
workflow.add_node(load)
workflow.add_node(evaluate)
workflow.add_node(generate_report)

# 定义工作流节点间的连接
workflow.add_edge("__start__", "load")
workflow.add_edge("load", "evaluate")
workflow.add_edge("evaluate", "generate_report")
workflow.add_edge("generate_report", "__end__")

# 编译工作流
employment_contract_review_workflow = workflow.compile(name="employment_contract_review_workflow")