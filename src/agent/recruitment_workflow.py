import os
from typing import Literal
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langchain_core.messages import HumanMessage, SystemMessage

def is_empty(s):
    return s is None or isinstance(s, str) and len(s.strip()) == 0

# 定义代理的状态
class InputState(TypedDict):
    user_require: str
    recruitment_info: str

class OutputState(TypedDict):
    json_data: str
    markdown_data: str

class OverallState(TypedDict):
    user_require: str
    recruitment_info: str
    system_content: str
    json_data: str
    markdown_data: str

def request_llm(system_content: str, user_content: str) -> str:
    """
    请求大模型获取回答
    """
    response = ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL_NAME"),  
        openai_api_key=os.getenv("OPENROUTER_API_KEY"), 
        openai_api_base=os.getenv("OPENROUTER_API_BASE")
    ).invoke([
        SystemMessage(content=system_content),
        HumanMessage(content=user_content)
    ])

    print(type(response))

    return response.content

def generate_recruitment_system_content():
    """
    生成招聘信息的system内容
    """

    system_content = """你是佛山照明公司人力资源部门的招聘助手，擅长编写JSON格式的结构化招聘信息，编写的招聘信息需要包含以下内容：
    1.职位名称：变量名为“job_title”，指企业或用人单位为某一岗位所设定的具体职务名称，如“项目工程师（智能照明）”、“测试工程师”等。
    2.薪资待遇：变量名为“salary”，指用人单位为员工提供的劳动报酬及相关经济福利，包括基本工资、绩效奖金、补贴、年终奖等。通常以月薪或年薪形式表示，如“8,000-12,000元/月”。
    3.工作经验：变量名为“work_experience”，指应聘者在申请该职位前所需具备的相关工作年限或经历要求，例如“三年或以上质量管理工作经验”。
    4.工作地点：变量名为“work_location”，指员工被录用后实际工作的地理位置，如“佛山”。
    5.学历要求：变量名为“educational_requirements”，指用人单位对应聘者最低学历水平的要求，如“本科及以上学历”、“硕士优先”等。
    6.公司福利：变量名为“company_benefits”，指除薪资以外，公司为员工提供的其他保障和激励措施，如五险一金、带薪年假、节日福利、员工旅游、定期体检、培训机会等。
    7.岗位职责：变量名为“job_responsibilities”，指该职位需要完成的主要工作任务和责任范围，如“负责家居智能照明产品研发”、“配合项目主管完成项目的监控和统筹”等。
    8.任职要求：变量名为“job_requirements”，又称“岗位要求”，是指胜任该职位所需具备的能力、技能、经验及其他素质要求，如“熟悉当前智能照明应用主流协议及标准”、“具有良好的沟通能力和团队合作精神”。
    请根据用户输入的信息生成JSON格式的招聘信息；只需要返回JSON数据即可，不需要进行解释；如果有分条叙述请保留序号，每条结尾使用<br>标签进行换行。返回格式示例如下：
    {
        "job_title": "测试工程师",
        "salary": "8,000-12,000元/月",
        "work_experience": "三年或以上质量管理工作经验",
        "work_location": "佛山",
        "educational_requirements": "本科及以上学历",
        "company_benefits": "五险一金、带薪年假、节日福利",
        "job_responsibilities": "负责家居智能照明产品研发",
        "job_requirements": "熟悉当前智能照明应用主流协议及标准"
    }
    """
    
    return system_content

def optimize_recruitment_system_content():
    """
    优化招聘信息的system内容
    """

    system_content = """你是佛山照明公司人力资源部门的招聘助手，擅长根据<优化要求></优化要求>标签中要求，优化<招聘信息></招聘信息>标签中的内容，并编写JSON格式的结构化招聘信息，编写的JSON格式招聘信息变量名及变量含义如下：
    1.职位名称：变量名为“job_title”，指企业或用人单位为某一岗位所设定的具体职务名称，如“项目工程师（智能照明）”、“测试工程师”等。
    2.薪资待遇：变量名为“salary”，指用人单位为员工提供的劳动报酬及相关经济福利，包括基本工资、绩效奖金、补贴、年终奖等。通常以月薪或年薪形式表示，如“8,000-12,000元/月”。
    3.工作经验：变量名为“work_experience”，指应聘者在申请该职位前所需具备的相关工作年限或经历要求，例如“三年或以上质量管理工作经验”。
    4.工作地点：变量名为“work_location”，指员工被录用后实际工作的地理位置，如“佛山”。
    5.学历要求：变量名为“educational_requirements”，指用人单位对应聘者最低学历水平的要求，如“本科及以上学历”、“硕士优先”等。
    6.公司福利：变量名为“company_benefits”，指除薪资以外，公司为员工提供的其他保障和激励措施，如五险一金、带薪年假、节日福利、员工旅游、定期体检、培训机会等。
    7.岗位职责：变量名为“job_responsibilities”，指该职位需要完成的主要工作任务和责任范围，如“负责家居智能照明产品研发”、“配合项目主管完成项目的监控和统筹”等。
    8.任职要求：变量名为“job_requirements”，又称“岗位要求”，是指胜任该职位所需具备的能力、技能、经验及其他素质要求，如“熟悉当前智能照明应用主流协议及标准”、“具有良好的沟通能力和团队合作精神”。
    请根据用户输入的<优化要求></优化要求>标签中要求，优化<招聘信息></招聘信息>标签中的内容，然后生成JSON格式的招聘信息；只需要返回优化后的JSON数据即可，不需要进行解释；如果有分条叙述请保留序号，每条结尾使用<br>标签进行换行。返回格式示例如下：
    {
        "job_title": "测试工程师",
        "salary": "8,000-12,000元/月",
        "work_experience": "三年或以上质量管理工作经验",
        "work_location": "佛山",
        "educational_requirements": "本科及以上学历",
        "company_benefits": "五险一金、带薪年假、节日福利",
        "job_responsibilities": "负责家居智能照明产品研发",
        "job_requirements": "熟悉当前智能照明应用主流协议及标准"
    }
    """
    
    return system_content

def markdown_recruitment_system_content() -> str:
    """
    Markdown格式招聘信息的system内容
    """

    system_content = """你是佛山照明公司人力资源部门的招聘助手，擅长将JSON格式的招聘信息，编写成Markdown格式，JSON格式的变量名含义如下：
    1.变量名“job_title”：职位名称。
    2.变量名“salary”：薪资待遇。
    3.变量名“work_experience”：工作经验。
    4.变量名“work_location”：工作地点。
    5.变量名“educational_requirements”：学历要求。
    6.变量名“company_benefits”：公司福利。
    7.变量名“job_responsibilities”：岗位职责。
    8.变量名“job_requirements”：任职要求。
    请将用户输入的JSON格式的招聘信息；转换成Markdown格式，只需要返回Markdown数据即可，不需要进行解释。返回格式示例如下：

    ## 职位名称
    测试工程师

    ## 薪资待遇
    8,000-12,000元/月

    ## 工作经验
    三年或以上质量管理工作经验

    ## 工作地点
    佛山

    ## 学历要求
    本科及以上学历

    ## 公司福利
    五险一金、带薪年假、节日福利

    ## 岗位职责
    负责家居智能照明产品研发

    ## 任职要求
    熟悉当前智能照明应用主流协议及标准
    """
    
    return system_content

def select_system_content(state: InputState) -> OverallState:
    """
    选择系统提示词
    """
    system_content = generate_recruitment_system_content()

    # 如果已有招聘信息，则进行优化
    if not is_empty(state.get('recruitment_info')):
        system_content = optimize_recruitment_system_content()

    return  {"user_require": state.get("user_require"), "recruitment_info": state.get('recruitment_info'), "system_content": system_content, }

def generate_recruitment_information(state: OverallState) -> OverallState:
    """
    生成JSON格式招聘信息
    """
    
    recruitment_info = state.get('user_require')

    state['json_data'] = request_llm(generate_recruitment_system_content(), recruitment_info)

    return state

def optimize_recruitment_information(state: OverallState) -> OverallState:
    """
    优化招聘信息
    """

    user_context = f"<招聘信息>{state.get('recruitment_info')}</招聘信息><优化要求>{state.get('user_require')}</优化要求>"
 
    state["json_data"] = request_llm(state.get('system_content'), user_context)

    return state

def markdown_recruitment_information(state: OverallState) -> OutputState:
    """
    生成Markdown格式招聘信息
    """
    
    markdown_data = request_llm(markdown_recruitment_system_content(), state["json_data"])

    return {"json_data": state["json_data"], "markdown_data": markdown_data}

# 定义新图形
workflow = StateGraph(input=InputState, output=OutputState)

workflow.add_node("select_system_content", select_system_content)
workflow.add_node("generate_recruitment_information", generate_recruitment_information)
workflow.add_node("optimize_recruitment_information", optimize_recruitment_information)
workflow.add_node("markdown_recruitment_information", markdown_recruitment_information)

workflow.add_edge(START, "select_system_content")

# 定义决定工作流是下一节点
def select_edge(state: OverallState) -> Literal["generate_recruitment_information", "optimize_recruitment_information"]:
    """
    决定工作流是下一节点
    """
    
    # 如果有招聘信息则走优化招聘信息节点
    if not is_empty(state.get('recruitment_info')):
        return "optimize_recruitment_information"
    
    # 默认选择生成招聘信息节点
    return "generate_recruitment_information"

workflow.add_conditional_edges(
    "select_system_content",
    select_edge,
)

workflow.add_edge("generate_recruitment_information", "markdown_recruitment_information")
workflow.add_edge("optimize_recruitment_information", "markdown_recruitment_information")

workflow.add_edge("markdown_recruitment_information", END)

recruitment_workflow = workflow.compile(name="recruitment_workflow")















