from __future__ import annotations

from dataclasses import dataclass, field
from typing_extensions import Annotated
from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage


@dataclass
class State:
    """状态类，用于存储工作流中的状态信息"""
    # 当前执行的动作名称
    action: str
    
    # 消息列表，使用 add_messages 注解实现消息追加功能
    messages: Annotated[list[AnyMessage], add_messages]

    # 票据识别相关字段
    # 票据图片路径或URL
    receipt_image: str = field(default_factory=lambda: "")
    
    # 票据识别结果的JSON字符串
    receipt_json: str = field(default_factory=lambda: "")