import os
import json
import requests
import tempfile
import dotenv
import pymupdf4llm

from dataclasses import dataclass
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.config import get_stream_writer
from langchain_openai import ChatOpenAI

# 加载环境变量
dotenv.load_dotenv()

extract_resume_instructions = """你是一名专业的人力资源信息提取助手，专注于从用户提供的简历中精准提取关键信息，用于岗位分析、人才画像构建及面试题目设计。

# Task
请从用户输入的文本中提取以下结构化信息，并以简练、清晰、专业的语言进行归纳整理：

- 背景 ：包括教育背景，工作经历概览，与岗位相关的核心优势/匹配点。
- 项目经验 ：包括项目名称，项目描述，项目职责，项目成果。
- 能力 ：包括沟通能力、团队协作、问题解决能力、责任心、学习能力等软性素质。
- 最高学历 ：最高学历。
- 姓名 ：候选人的姓名。
- 核心优势 ：候选人的核心优势。
- 与岗位的匹配点 ：候选人与岗位的匹配点。

# Format
请以JSON格式输出，包含以下字段：
{{
    "name": "候选人姓名",
    "background": {{
        "education": [{{
            "school": "学校",
            "major": "专业",
            "degree": "学历",
            "duration": "学习时间"
        }}],
        "work_experience": [{{
            "company": "公司",
            "position": "职位",
            "duration": "工作时间"
        }}],
    }},
    "project_experience": {{
        "name": "项目名称",
        "description": "项目描述",
        "responsibilities": "项目职责",
        "outcomes": "项目成果"
    }},
    "ability": [
        "能力1说明",
        "能力2说明",
        "能力3说明"
    ],
    "core_strengths": "核心优势",
    "matching_points": "与岗位的匹配点",
    "highest_education": "最高学历"
}}

# Note
- 请以JSON格式输出，不要包含任何其他内容，例如：```json
"""

extract_job_description_instructions = """你是一名专业的人力资源信息提取助手，专注于从用户提供的职位描述中精准提取关键信息，用于岗位分析、人才画像构建及面试题目设计。

# Task
请从用户输入的文本中提取以下结构化信息，并以简练、清晰、专业的语言进行归纳整理：

- 岗位名称 ：识别并提取招聘岗位的正式名称。
- 岗位描述 ：概括该岗位的整体定位、所属部门、工作目标或核心价值。
- 任职要求 ：整合并细化候选人需具备的各项条件，尽量细化到可评估的行为层面，便于后续出题参考，包括：
   - 任职职责 ：明确岗位的核心工作内容与日常职责，按优先级或逻辑顺序列出。
   - 硬性条件 ：学历、工作经验、专业背景、技术证书、技能工具掌握等可量化的门槛条件。
   - 核心素质 ：沟通能力、团队协作、问题解决能力、责任心、学习能力等软性素质。


# Format
请以JSON格式输出，包含以下字段：
{{
    "name": "岗位名称",
    "description": "岗位描述",
    "requirements": {{
        "responsibilities": "任职职责",
        "conditions": "硬性条件",
        "qualities": "核心素质"
    }}
}}

# Note
- 请以JSON格式输出，不要包含任何其他内容，例如：```json
"""

question_generate_instructions = """
你是一个资深招聘面试官助手，能够根据提供的岗位职责描述（JD）和候选人简历信息，为不同岗位定制一套专业、有针对性的面试问题。

# Task
请根据以下输入内容，生成三类面试问题：
1. **技术能力相关问题**：请基于岗位所需技术栈和候选人简历中的技术关键词，生成以下类型的问题：
  - 技术原理理解类问题
  - 实际应用经验类问题
  - 性能优化或疑难排查类问题
2. **项目经验相关问题**：请结合候选人过往参与的重点项目，生成以下类型的问题：
  - STAR法则引导类问题（情境-任务-行动-结果）
  - 角色与贡献类问题
  - 项目反思与改进类问题
3. **Q&A环节开放性问题**：评估候选人的软技能、职业动机、团队协作与沟通能力等综合素质，生成以下类型的问题：
  - 职业发展路径相关
  - 对公司/产品的兴趣延伸
  - 岗位价值认同度评估

每个问题需要附带一个“目的说明”，清晰表达考察点。问题应具有逻辑性、专业性和实操性，避免泛泛而谈。

<Job Description>
{description}
</Job Description>

<Job Requirements>
{requirements}
</Job Requirements>

<Candidate Project Experience>
{project_experience}
</Candidate Project Experience>

<Candidate Ability>
{ability}
</Candidate Ability>


# Format
请按照如下结构输出结果：

{{
  "technical_questions": [
    {{
      "question": "问题文本",
      "purpose": "考察点说明"
    }},
  ],
  "project_questions": [
    {{
      "question": "问题文本",
      "purpose": "考察点说明"
    }},
  ],
  "q_and_a_questions": [
    {{
      "question": "问题文本",
      "purpose": "考察点说明"
    }},
  ]
}}

# Note
- 请以JSON格式输出，不要包含任何其他内容，例如：```json
"""


class Education(BaseModel):
    school: str = Field(description="The school of the candidate", default="")
    major: str = Field(description="The major of the candidate", default="")
    degree: str = Field(description="The degree of the candidate", default="")
    duration: str = Field(description="The duration of the candidate", default="")

class WorkExperience(BaseModel):
    company: str = Field(description="The company of the candidate", default="")
    position: str = Field(description="The position of the candidate", default="")
    duration: str = Field(description="The duration of the candidate", default="")

class Background(BaseModel):
    education: list[Education] = Field(description="The education of the candidate", default=[])
    work_experience: list[WorkExperience] = Field(description="The work experience of the candidate", default=[])

class ProjectExperience(BaseModel):
    name: str = Field(description="The name of the project", default="")
    description: str = Field(description="The description of the project", default="")
    responsibilities: str = Field(description="The responsibilities of the project", default="")
    outcomes: str = Field(description="The outcomes of the project", default="")

class ResumeInfo(BaseModel):
    name: str = Field(description="The name of the candidate", default="")
    background: Background = Field(description="The background of the candidate", default=Background())
    project_experience: list[ProjectExperience] = Field(description="The project experience of the candidate", default=[])
    ability: str = Field(description="The ability of the candidate", default="")
    core_strengths: str = Field(description="The core strengths of the candidate", default="")
    matching_points: str = Field(description="The matching points of the candidate", default="")
    highest_education: str = Field(description="The highest education of the candidate", default="")

class Requirements(BaseModel):
    responsibilities: list[str] = Field(description="The responsibilities of the job", default="")
    conditions: list[str] = Field(description="The conditions of the job", default="")
    qualities: list[str] = Field(description="The qualities of the job", default="")

class JobInfo(BaseModel):
    name: str = Field(description="The name of the job", default="")
    description: str = Field(description="The description of the job", default="")
    requirements: Requirements = Field(description="The requirements of the job", default=Requirements())

class Question(BaseModel):
    question: str = Field(description="The question", default="")
    purpose: str = Field(description="The purpose of the question", default="")

class Questions(BaseModel):
    technical_questions: list[Question] = Field(description="The technical questions", default=[])
    project_questions: list[Question] = Field(description="The project questions", default=[])
    q_and_a_questions: list[Question] = Field(description="The q_and_a_questions", default=[])

class InterviewStep(BaseModel):
    step: str = Field(description="The step of the interview", default="")
    content: str = Field(description="The content of the interview", default="")
    duration: str = Field(description="The duration of the interview", default="")

class InterviewProcess(BaseModel):
    steps: list[InterviewStep] = Field(description="The steps of the interview", default=[])


# 定义面试计划生成输入状态类
@dataclass
class InterviewPlanInputState:
    resume_file_path: str  # 简历文件路径
    job_description: str   # 职位描述

# 定义面试计划生成状态类
@dataclass
class InterviewPlanState:
    resume_file_path: str  # 简历文件路径
    job_description: str = ""   # 职位描述
    resume_content: str = ""   # 简历内容
    resume_info: ResumeInfo = None   # 简历信息
    job_info: JobInfo = None    # 岗位信息
    questions: list[str] = None    # 问题列表
    interview_doc: str = ""    # 面试文档
    interview_process: InterviewProcess = None    # 面试流程


# 定义面试计划生成输出状态类
@dataclass
class InterviewPlanOutputState:
    resume_info: ResumeInfo = None   # 简历信息
    job_info: JobInfo = None    # 岗位信息
    questions: list[str] = None    # 问题列表
    interview_process: InterviewProcess = None    # 面试流程
    interview_doc: str = ""    # 面试文档

def load_info(state: InterviewPlanState) -> str:
    """加载信息"""
    writer = get_stream_writer()
    writer({"action": {"type": "load_info", "state": "start"}})  
    try:
        resume_file_path = state.resume_file_path
        # 下载网络URL的文件到临时文件
        response = requests.get(resume_file_path)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
                
            # 使用pymupdf4llm加载PDF文件
            resume_content = pymupdf4llm.to_markdown(temp_file_path)
            
            # 删除临时文件
            os.unlink(temp_file_path)
        else:
            resume_content = "请提供正确的简历附件或简历路径！"
    except Exception as e:
        resume_content = f"处理简历文件时出错: {str(e)}"
    writer({"action": {"type": "load_info", "state": "end"}})
    return {"resume_content": resume_content}

def extract_resume(state: InterviewPlanState) -> str:
    """提取简历信息"""
    writer = get_stream_writer()
    writer({"action": {"type": "extract_resume", "state": "start"}})

    # 调用LLM分析合同风险
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
        tags=["call_extract_resume"]
    ).invoke([
        SystemMessage(content=extract_resume_instructions),
        HumanMessage(content=state.resume_content)
    ])
    resume_info = json.loads(response.content)
    writer({"action": {"type": "extract_resume", "state": "end"}})
    return {"resume_info": resume_info}

def extract_jd(state: InterviewPlanState) -> str:
    """
    提取职位描述
    """
    writer = get_stream_writer()
    writer({"action": {"type": "extract_jd", "state": "start"}})

    # 调用LLM分析合同风险
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
        tags=["call_extract_resume"]
    ).invoke([
        SystemMessage(content=extract_job_description_instructions),
        HumanMessage(content=state.job_description)
    ])
    job_info = json.loads(response.content)
    writer({"action": {"type": "extract_jd", "state": "end"}})
    return {"job_info": job_info}


def generate_questions(state: InterviewPlanState) -> str:
    """生成面试题目"""
    writer = get_stream_writer()
    writer({"action": {"type": "generate_questions", "state": "start"}})
    question_generate_instructions_formatted = question_generate_instructions.format(
        description=state.job_info["description"],
        requirements=state.job_info["requirements"],
        project_experience=state.resume_info["project_experience"],
        ability=state.resume_info["ability"]
    )
    # 调用LLM生成面试题目
    response = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0,
        tags=["call_generate_questions"]
    ).invoke([
        SystemMessage(content=question_generate_instructions_formatted),
        HumanMessage(content="Generate questions for the interview, ，every type generate **5 questions**.")
    ])
    questions = Questions(**json.loads(response.content))
    writer({"action": {"type": "generate_questions", "state": "end"}})
    return {"questions": questions}


def generate_plan(state: InterviewPlanState) -> str:
    """生成面试计划"""
    writer = get_stream_writer()
    writer({"action": {"type": "generate_plan", "state": "start"}})

    job_info=state.job_info
    resume_info=state.resume_info
    questions=state.questions

    interview_process = InterviewProcess(
        steps=[
            InterviewStep(step="自我介绍", content="让候选人简要介绍自己的职业背景、核心能力和与应聘岗位相关的亮点。", duration="5分钟"),
            InterviewStep(step="技术能力评估", content="围绕岗位所需技术栈进行提问，深入评估候选人的专业深度与实际应用能力。", duration="15分钟"),
            InterviewStep(step="项目经验探讨", content="引导候选人分享其主导或参与的关键项目，了解其在项目中的角色、挑战与成果。", duration="20分钟"),
            InterviewStep(step="软技能评估", content="探讨候选人在团队协作、沟通协调、抗压能力等方面的表现。", duration="10分钟"),
            InterviewStep(step="Q&A环节", content="允许候选人就岗位职责、团队情况、发展路径等方面提问。", duration="5分钟")
        ]
    )

    interview_doc = f"## {resume_info['name']}的面试方案 - {job_info['name']}\n\n"
    interview_doc += f"### 1. 岗位信息摘要\n\n"
    interview_doc += f"{job_info['description']}\n\n"
    interview_doc += f"#### 岗位职责\n\n"
    for responsibility in job_info['requirements']['responsibilities']:
        interview_doc += f"- {responsibility}\n\n"
    interview_doc += f"#### 硬性条件\n\n"
    for condition in job_info['requirements']['conditions']:
        interview_doc += f"- {condition}\n\n"
    interview_doc += f"#### 核心素质\n\n"
    for quality in job_info['requirements']['qualities']:
        interview_doc += f"- {quality}\n\n"

    interview_doc += f"### 2. 候选人信息摘要\n\n"


    interview_doc += f"#### 教育背景\n\n"
    for education in resume_info['background']['education']:
        interview_doc += f"- {education['school']} {education['major']} {education['degree']} {education['duration']}\n\n"
    interview_doc += f"#### 工作经历\n\n"
    for work_experience in resume_info['background']['work_experience']:
        interview_doc += f"- {work_experience['company']} {work_experience['position']} {work_experience['duration']}\n\n"
    interview_doc += f"#### 项目经验\n\n"
    for project_experience in resume_info['project_experience']:
        interview_doc += f"- {project_experience['name']}\n\n"
        interview_doc += f"  - 项目描述：{project_experience['description']}\n\n"
        interview_doc += f"  - 工作内容：{project_experience['responsibilities']}\n\n"
        interview_doc += f"  - 项目成果：{project_experience['outcomes']}\n\n"

    interview_doc += f"#### 个人能力\n\n"
    for ability in resume_info['ability']:
        interview_doc += f"- {ability}\n\n"

    interview_doc += f"#### 核心优势\n\n"
    interview_doc += f"- {resume_info['core_strengths']}\n\n"
    interview_doc += f"#### 与岗位的匹配点\n\n"
    interview_doc += f"{resume_info['matching_points']}\n\n"

    interview_doc += f"### 3. 面试题目\n\n"
    interview_doc += f"#### 技术能力相关问题\n\n"
    for question in questions.technical_questions:
        interview_doc += f"- {question.question}\n\n"
        # interview_doc += f"  目的：{question.purpose}\n\n"
    interview_doc += f"#### 项目经验相关问题\n\n"
    for question in questions.project_questions:
        interview_doc += f"- {question.question}\n\n"
        # interview_doc += f"  目的：{question.purpose}\n\n"
    interview_doc += f"#### Q&A环节开放性问题\n\n"
    for question in questions.q_and_a_questions:
        interview_doc += f"- {question.question}\n\n"
        # interview_doc += f"  目的：{question.purpose}\n\n"
        
    interview_doc += f"### 4. 面试流程\n\n"
    for step in interview_process.steps:
        interview_doc += f"- **{step.step}** ({step.duration})：{step.content}\n\n"

    writer({"action": {"type": "generate_plan", "state": "end"}})
    return {"interview_doc": interview_doc, "interview_process": interview_process}

# 构建合同风险分析工作流
workflow = StateGraph(state_schema=InterviewPlanState, input=InterviewPlanInputState, output=InterviewPlanOutputState)
workflow.add_node("load_info", load_info)
workflow.add_node("extract_resume", extract_resume)
workflow.add_node("extract_jd", extract_jd)
workflow.add_node("generate_questions", generate_questions)
workflow.add_node("generate_plan", generate_plan)

# 定义工作流节点间的连接
workflow.add_edge("__start__", "load_info")
workflow.add_edge("load_info", "extract_resume")
workflow.add_edge("load_info", "extract_jd")
workflow.add_edge("extract_jd", "generate_questions")
workflow.add_edge("extract_resume", "generate_questions")
workflow.add_edge("generate_questions", "generate_plan")
workflow.add_edge("generate_plan", "__end__")

# 编译工作流
interview_plan_generate_workflow = workflow.compile(name="interview_plan_generate_workflow")