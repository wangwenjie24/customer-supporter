from http import HTTPStatus
import dashscope
import requests

import os
import dotenv

from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.config import get_stream_writer

from agent.configuration import Configuration
from agent.prompts import meeting_summarizer_instructions
from dataclasses import dataclass, field
from http import HTTPStatus


dotenv.load_dotenv()

@dataclass
class InputState:
    url: str = field(default="")

@dataclass
class State:
    url: str
    text: str = field(default="")
    final_summary: str = field(default="")

@dataclass
class OutputState:
    final_summary: str

    
def transcription(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """transcription audio to text"""

    writer = get_stream_writer()
    writer({"action": "转写音频"})

    # Get State
    task_response = dashscope.audio.asr.Transcription.async_call(
        model='sensevoice-v1',
        file_urls=[state.url],
        language_hints=['zh'],
    )

    transcribe_response = dashscope.audio.asr.Transcription.wait(task=task_response.output.task_id)
    if transcribe_response.status_code == HTTPStatus.OK:
        # 获取转写结果URL
        transcription_url = transcribe_response.output['results'][0]['transcription_url']
        
        try:
            response = requests.get(transcription_url)
            if response.status_code == 200:
                # 解析JSON内容
                transcription_data = response.json()
                
                # 检查转写数据结构
                if 'transcripts' in transcription_data and len(transcription_data['transcripts']) > 0:
                    # 从transcripts列表中获取第一个元素的text字段
                    text_content = transcription_data['transcripts'][0].get('text', '无转写文本')
                else:
                    print("无转写文本 - 数据结构中未找到transcripts字段或为空")
            else:
                print(f"获取转写结果失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"解析转写结果时出错: {e}")
            
    writer({"action": "转写音频"})
    return {"text": text_content}


def summary(state: State, config: RunnableConfig) -> str:
    """Extend the prompt"""
    writer = get_stream_writer()
    writer({"action": "生成会议纪要"})

    # Get State
    text = state.text
    # Call LLM
    result = ChatOpenAI(
        model_name=os.getenv("OPENROUTER_MODEL_NAME"),
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_API_BASE"),
        temperature=0.0
    ).invoke([
        SystemMessage(content=meeting_summarizer_instructions),
        HumanMessage(content=text)
    ])
    writer({"action": "生成会议纪要"})
    return {"final_summary": result.content}


# Define a new graph
workflow = StateGraph(State, input=InputState, output=OutputState, config_schema=Configuration)

# Add the node to the graph
workflow.add_node("transcription", transcription)
workflow.add_node("summary", summary)

# Set the entrypoint as `call_model`
workflow.add_edge("__start__", "transcription")
workflow.add_edge("transcription", "summary")
workflow.add_edge("summary", "__end__")

# Compile the workflow into an executable graph
meeting_summary_workflow = workflow.compile(name="meeting_summary_workflow")
