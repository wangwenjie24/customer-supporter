import pymupdf4llm
import operator
import requests
import tempfile
import os
import json
import requests
from langgraph.types import Send
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph import END, StateGraph, START
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

# 定义代理的状态
class InputState(TypedDict):
    recruitment_info: str
    resume_urls: str
    scoring_rules: str

# 定义代理的状态
class SubInputState(TypedDict):
    recruitment_info: str
    resume_url: str
    scoring_rules: str

class SubOutState(TypedDict):
    resume_json_list: Annotated[list, operator.add]
    evaluate_json_list: Annotated[list, operator.add]

class MergeInputState(TypedDict):
    resume_json_list: Annotated[list, operator.add]
    evaluate_json_list: Annotated[list, operator.add]

class SubOverallState(TypedDict):
    recruitment_info: str
    resume_url: str
    scoring_rules: str
    resume_info: str
    resume_json: str
    evaluate_json: str

class OverallState(TypedDict):
    recruitment_info: str
    scoring_rules: str
    resume_url: str
    resume_url_list: list
    resume_info: str
    resume_json: str
    evaluate_json: str

class OutputState(TypedDict):
    data: list

def is_empty(s):
    return s is None or isinstance(s, str) and len(s.strip()) == 0

def get_content_by_url(url: str):

    print(f'URL:{url}')
    # 发送HTTP请求获取文件数据
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    temp_file_path = ''

    # 创建一个临时文件并写入数据
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(response.content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file_path = temp_file.name
    
    print(f'temp_file_path:{temp_file_path}')
    
    # 使用 pymupdf4llm 将 PDF 转换为 Markdown 格式的文本
    content = pymupdf4llm.to_markdown(temp_file_path)

    # 最后记得清理
    try:
        os.unlink(temp_file_path)
    except Exception as e:
        print("删除临时文件失败:", e)
        
    return content

def request_llm(system_content: str, user_content: str):
    """
    请求大模型获取回答
    """

    response = ChatOpenAI( 
        disable_streaming=True,
        model=os.getenv("OPENROUTER_MODEL_NAME"),  
        openai_api_key=os.getenv("OPENROUTER_API_KEY"), 
        openai_api_base=os.getenv("OPENROUTER_API_BASE")
    ).invoke([
        SystemMessage(content=system_content),
        HumanMessage(content=user_content)
    ])

    return response.content

def get_resume_system_content():
    """
    个人简历提取结构化信息的system内容
    """

    system_content = """你是佛山照明公司人力资源部门的简历助手，擅长将简历信息提取为结构化JSON数据，包含以下字段：
    1.姓名：变量名为“name”，表示个人的全名。
    2.性别：变量名为“gender”，用于标识个人的性别（如男、女或未填写）。
    3.年龄：变量名为“age”，代表个人的年龄，通常以年为单位。
    4.工作年限：变量名为“years_of_experience”，指个人累积的工作经验年数。
    5.电话：变量名为“phone_number”，记录个人用于联系的电话号码。
    6.邮箱：变量名为“email”，提供个人用于沟通的电子邮件地址。
    7.学校名称：变量名为“school_name”，指的是个人就读过的学校的名称。
    8.入学及毕业年月份：变量名为“enrollment_and_graduation_dates”，包括个人入学和毕业的具体年月信息。
    9.专业：变量名为“major”，表示个人在学术期间所学的专业领域。
    10.学历：变量名为“degree”，说明个人获得的最高或相关教育程度（如学士、硕士等）。
    11.工作经历：变量名为“work_experience”，包含个人过往的工作职位、公司名称、工作时间和职责描述等信息。
    12.证书情况：变量名为“certifications”，列出个人拥有的专业认证或许可证。
    13.获奖情况：变量名为“awards”，记录个人在其学业或职业生涯中获得的重要奖项和荣誉。
    请根据以上字段将用户输入的简历信息生成JSON格式的信息；只需要返回JSON字符串即可，不需要进行解释和格式化。
    返回格式示例如下：
    {
      "name": "张三",
      "gender": "男",
      "age": 28,
      "years_of_experience": 5,
      "phone_number": "123-4567-8901",
      "email": "zhangsan@example.com",
      "school_name": "北京大学",
      "enrollment_and_graduation_dates":"2010.09-2014.07",
      "major": "计算机科学与技术",
      "degree": "本科",
      "work_experience": "ABC科技有限公司,软件工程师,2014-07至2017-06,开发和维护公司主要产品", 
      "certifications": "注册会计师",
      "awards": "2013年度优秀学生奖"
    }
    """ 
    
    return system_content

def get_resume_score_system_content(scoring_rules: str):
    """
    简历评分分析的system内容
    """

    if is_empty(scoring_rules):
        scoring_rules = """
            1.简历中学历信息与招聘要求的学历相比较，简历中学历越高得分越高。
            2.简历中工作经验与招聘要求的工作经验比较，简历中工作经验越高得分越高。
            3.简历中应聘岗位与招聘岗位符合或相近，越符合分数越高。
            4.简历中期望薪资在岗位薪资范围内，期望薪资越低得分越高。
            5.简历中公司的更换频度，更换公司越频繁分数越低。
            6.简历中有获得证书说明，证书数量越多分数越高。
            7.简历中工作描述与招聘中的任职要求相符合，符合度越高分数越高。
            8.简历中教育信息的学校是否为重点大学，如果是985或211则得分越高。
            9.简历中工作经历的公司是否为知名公司，越知名得分越高。
            10.简历整体内容完善程度，包括但不限于姓名、求职意向、工作年限、年龄、电话、邮箱、教育背景、工作经历等，内容越完善分数越高。
            以上10条规则，每条规则最高可得10分，及格6分，最低得1分；所有规则总计满分100分。
        """
    else:
        scoring_rules_json = json.loads(scoring_rules)
        rules_txt = []

        for item in scoring_rules_json:
            score = item['value']
            if item['name'] == '教育背景':
                rules_txt.append(f'教育背景：变量名为“educational_background”，识别并对比应聘者的学历、专业以及毕业院校等信息，同时也能理解招聘要求中对教育背景的具体需求，最高得分{score}分。')
            elif item['name'] == '薪资期望':
                rules_txt.append(f'薪资期望：变量名为“expected_salary”，分析简历中的期望薪资范围和招聘信息中的提供的薪资待遇，评估两者之间的匹配度，最高得分{score}分。')
            elif item['name'] == '工作经验':
                rules_txt.append(f'工作经验：变量名为“work_experience”，这项包括了过去的相同行业工作经历、相同职位以及在职时间等。提取这些相关工作或专业信息，并将其与招聘信息中的经验要求进行比较，最高得分{score}分。')
            elif item['name'] == '技能能力':
                rules_txt.append(f'技能能力：变量名为“skills_abilities”，涉及具体的技能（如编程语言、软件操作能力等）。识别出简历中列出的技能，并判断它们是否符合招聘岗位的要求，最高得分{score}分。')
            elif item['name'] == '证书和资格':
                rules_txt.append(f'证书和资格：变量名为“certifications_qualifications”，任何相关的行业认证或资格证明。识别这些证书，并评估其对于申请职位的相关性和重要性，最高得分{score}分。')
            else:
                print(f"未找到相关评价指标：{item['name']}")
                continue
        scoring_rules = '\n'.join(rules_txt)

    system_content = """你是佛山照明公司人力资源部门的简历助手，擅长筛选简历信息，筛选规则如下：""" + scoring_rules + """
    请根据标签 <招聘信息></招聘信息> 和 <简历信息></简历信息> 对简历进行分析和评分；并返回JSON格式的结果，包含根据规则得到的每一项评分数；总评分变量名为“resume_rating“；评价结果变量名为“evaluate_results“，需要包含每一项的得分原因简述并使用“\n“换行，然后再进行总结。只需要返回JSON数据即可，不需要进行解释。
    返回格式示例如下：
    {
        "educational_background": "15",
        "expected_salary": "20",
        "work_experience": "15",
        "skills_abilities": "20",
        "certifications_qualifications": "15",
        "resume_rating": "85",
        "evaluate_results": "该应聘者具备出色的沟通能力和团队合作精神，工作态度积极主动，富有责任心。拥有相关项目经验，并展现出较强的学习能力和解决问题的技巧"
    }
    """
    
    return system_content

def process_input_data(state: InputState) -> OverallState:
    """
    处理输入数据
    """
    writer = get_stream_writer()
    writer({"action": {"type": "process_input_data", "state": "start"}})
    resume_urls = state.get('resume_urls')
    writer({"action": {"type": "process_input_data", "state": "end"}})
    writer({"action": {"type": "resume_score", "state": "start"}})
    return {"recruitment_info":state.get('recruitment_info'), "scoring_rules": state.get('scoring_rules'), "resume_url_list": resume_urls.split(",")}

def get_resume_json(state: SubInputState) -> SubOverallState:
    """
    根据个人简历文件获取JSON结构化信息
    """

    # 简历文件转成的文本信息
    resume_info = get_content_by_url(state["resume_url"])
    # 简历文本信息转成JSON格式
    resume_json = request_llm(get_resume_system_content(), resume_info)

    state = {"recruitment_info": state["recruitment_info"], "scoring_rules": state.get('scoring_rules'), "resume_url": state["resume_url"], "resume_info": resume_info, "resume_json": resume_json}

    return state

def get_resume_score(state: SubOverallState) -> SubOutState:
    """
    对个人简历进行评分分析
    参数：
    recruitment_info -- 招聘信息
    resume_info -- 简历信息
    """
    user_content = f' <招聘信息>{state["recruitment_info"]}</招聘信息><简历信息>{state["resume_info"]}</简历信息>'

    state["evaluate_json"] = request_llm(get_resume_score_system_content(state.get('scoring_rules')), user_content).replace("```json\n","").replace("\n```","")

    return {"resume_json_list": [state["resume_json"]], "evaluate_json_list": [state["evaluate_json"]]}

def merge_processing_results(state: MergeInputState) -> OutputState:
    """
    合并处理结果
    """
    writer = get_stream_writer()
    writer({"action": {"type": "resume_score", "state": "end"}})
    writer({"action": {"type": "merge_processing_results", "state": "start"}})
    print(f"merge_processing_results Input: {state}")

    # 解析并合并
    result = {
        "data": [
            dict(json.loads(resume), **json.loads(evaluate))
            for resume, evaluate in zip(state['resume_json_list'], state['evaluate_json_list'])
        ]
    }

    # 输出结果
    print(f"result:{result}")
    writer({"action": {"type": "merge_processing_results", "state": "end"}})
    return result

def continue_to_process(state: OverallState):
    return [Send("subgraph", {"recruitment_info":state.get('recruitment_info'), "scoring_rules": state.get('scoring_rules'), "resume_url": resume_url}) for resume_url in state['resume_url_list']]

# 构建子图
sub_workflow = StateGraph(SubOverallState, input=SubInputState, output=SubOutState)

sub_workflow.add_node("get_resume_json", get_resume_json)
sub_workflow.add_node("get_resume_score", get_resume_score)

sub_workflow.add_edge(START, "get_resume_json")
sub_workflow.add_edge("get_resume_json", "get_resume_score")
sub_workflow.add_edge("get_resume_score", END)

subgraph = sub_workflow.compile()

# 定义主图形
workflow = StateGraph(input=InputState, output=OutputState)

workflow.add_node("process_input_data", process_input_data)
workflow.add_node("subgraph", subgraph)
workflow.add_node("merge_processing_results", merge_processing_results)

workflow.add_edge(START, "process_input_data")
workflow.add_conditional_edges("process_input_data", continue_to_process, ["subgraph"])
workflow.add_edge("subgraph", "merge_processing_results")
workflow.add_edge("merge_processing_results", END)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
resume_workflow = workflow.compile(name="resume_workflow")