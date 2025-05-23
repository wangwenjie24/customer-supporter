import requests
import pymysql
import os
import json
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph, START
from langchain_core.messages import HumanMessage, SystemMessage
import redis
from langchain_core.tools import StructuredTool

model_name=os.getenv("OPENROUTER_MODEL_NAME")
openai_api_key=os.getenv("OPENROUTER_API_KEY")
openai_api_base=os.getenv("OPENROUTER_API_BASE")

server_host= "http://47.251.17.61"
query_tools_url = {
    "attendance_record": f"{server_host}/saiyan-ai/ai/knowledge/1925017405541072896/search",
    "employee_roster": f"{server_host}/saiyan-ai/ai/knowledge/1925021373696589824/search",
    "company_department": f"{server_host}/saiyan-ai/ai/knowledge/1925021621638676480/search"
}

model_type = 'hr' #人资
TOOLS_REDIS_KEY = f'{model_type}_data_tool_list' 

# MySQl 配置信息
mysql_config = {
    'host': '47.251.17.61',  # 主机地址
    'user': 'root',          # 用户
    'port': 3306,            # 端口号
    'database': 'saiyan_ai', # 使用的数据库编号
    'password': ',ki89ol.'   # 密码（如果没有密码，设置为 None）
}

# 连接数据库查询所有的Tools
# 将数据行与字段名称结合成字典列表
def rows_to_dict_list(column_names, rows):
    return [dict(zip(column_names, row)) for row in rows]
    
def fetch_data_with_column_names(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        
        # 获取字段名称
        column_names = [desc[0] for desc in cursor.description]
        
        # 获取数据行
        rows = cursor.fetchall()
        
        # 返回字段名称和数据
        return column_names, rows
    except pymysql.connector.Error as e:
        print(f"查询数据失败: {e}")
        return None, None
    finally:
        cursor.close()

def get_data_from_db(sql_query: str) -> str:

    try:
        # 连接到 MySQL 数据库
        connection = pymysql.connect(**mysql_config)

        # 获取字段名称和数据
        column_names, rows = fetch_data_with_column_names(connection, sql_query)
        
        if column_names and rows:
            # 转换为字典列表
            data_as_dict = rows_to_dict_list(column_names, rows)

            return data_as_dict
            
    except pymysql.MySQLError as e:
        return f"数据库错误: {e}"
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

    return None

# Redis 配置信息
redis_config = {
    'host': '47.251.17.61',  # Redis 主机地址
    'port': 6379,            # Redis 端口号
    'db': 5,                 # 使用的数据库编号
    'password': ',ki89ol.'   # Redis 密码（如果没有密码，设置为 None）
}

# 创建 Redis 连接
def connect_to_redis(host='localhost', port=6379, db=0, password=None):
    try:
        # 创建 Redis 客户端
        redis_client = redis.StrictRedis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True  # 自动将字节类型解码为字符串
        )
        
        # 测试连接是否成功
        if redis_client.ping():
            print("成功连接到 Redis！")
            return redis_client
        else:
            print("无法连接到 Redis。")
            return None
    except Exception as e:
        print(f"连接 Redis 失败: {e}")
        return None

# 从 Redis List 中读取数据
def read_list_from_redis(redis_client, list_key):
    try:
        # 获取 List 的所有元素
        list_data = redis_client.lrange(list_key, 0, -1)  # 0 表示第一个元素，-1 表示最后一个元素
        if list_data:
            return list_data
        else:
            print(f"Redis List '{list_key}' 中没有数据。")
    except Exception as e:
        print(f"读取 Redis List 数据失败: {e}")
        
# 连接到 Redis
redis_client = connect_to_redis(**redis_config)

tools_dict = {}

if redis_client:

    # 读取 Redis List 数据
    tool_list = read_list_from_redis(redis_client, TOOLS_REDIS_KEY)

    for tool in tool_list:
        
        tool_json = json.loads(tool)
        
        targer_table = tool_json['targer_table']

        if 'company_relationship' == targer_table or 'company_department_relationship' == targer_table:
            targer_table = 'company_department'
        
        if not targer_table in tools_dict:
            tools_dict[targer_table] = []

        tools_dict[targer_table].append(tool_json)

def create_function(func_name, func_body):
    exec(func_body)
    globals()[func_name] = eval(func_name)
    return globals()[func_name]

def create_tool(tool_info_data: dict) -> dict:
    """Create schema for a placeholder tool."""

    # 工具名称
    tool_name = tool_info_data["tool_name"]
    tool_body = tool_info_data["tool_body"]
    tool_description = tool_info_data["tool_desc"]
    tool_args_schema = json.loads(tool_info_data["args_schema"])
    
    # 创建函数对象
    tool_func = create_function(tool_name, tool_body)
    
    return StructuredTool.from_function(
        tool_func,
        name = tool_name,
        description = tool_description,
        args_schema = tool_args_schema
    )

# 定义代理的状态
class InputState(TypedDict):
    question: str
    module_name: str

class OverallState(TypedDict):
    question: str
    module_name: str
    tool_list: list
    data: str

class OutputState(TypedDict):
    messages: AIMessage

def get_related_tools(state: InputState) -> OverallState:
    """
    获取相关工具
    """

    module_name = state['module_name']
    question = state['question']

    response = requests.get(query_tools_url[module_name], {"query":question})
    resp_json = response.json()
    tool_list = []

    for item in resp_json['data']:
        for tool in tools_dict.get(module_name):
            if tool['tool_id'] == item['answer']:
                tool_list.append(tool)

    return {"module_name": module_name, "question": question, "tool_list": tool_list}

def get_data_node(state: OverallState) -> OverallState:
    """
    从数据库中查询数据
    """

    tool_registry = {}
    question = state['question']
    tool_list = state['tool_list']

    for item in tool_list:
        print(item)
        tool_registry[item['tool_id']] =  create_tool(item)

    tools = list(tool_registry.values())

    llm = ChatOpenAI(model=model_name, 
                     openai_api_key=openai_api_key, 
                     openai_api_base=openai_api_base, 
                     temperature=0
                     ).bind_tools(tools, tool_choice="any")
    
    system_content = """你是一个可以通过自然语言调用工具的助手，请根据用户的提问匹配相应的工具，并执行获取数据结果，如果用户输入参数和工具匹配失败，则提示用户补充参数"""

    message = llm.invoke([SystemMessage(content=system_content), HumanMessage(content=question)])

    if hasattr(message, "tool_calls") and message.tool_calls:
        tool_call = message.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        print(f"🛠️ 正在调用工具: {tool_name}, 参数: {tool_args}")

        # 执行工具
        for t in tools:
            if t.name == tool_name:
                tool_response = t.invoke(tool_args)
                state["data"] = tool_response
                break

    return state

def optimize_answers(state: OverallState) -> OutputState:
    """
    优化回答内容
    """
    llm = ChatOpenAI(model=model_name, openai_api_key=openai_api_key, openai_api_base=openai_api_base, temperature=0)

    question = state['question']
    data = state["data"]

    system_content = """你是一个数据整理助手，可以根据用户的提问和查询到的数据整理返回信息；其中<用户问题></用户问题>标签中间的是问题，<数据结果></数据结果>标签中间的是查询到的JSON格式结果，请将结果整理为自然语言返回给用户。"""
    user_context = f'<用户问题>{question}</用户问题><数据结果>{data}</数据结果>'

    return {"messages": llm.invoke([SystemMessage(content=system_content), HumanMessage(content=user_context)])}

# 定义主图形
workflow = StateGraph(OverallState, input=InputState, output=OutputState)

workflow.add_node("get_related_tools", get_related_tools)
workflow.add_node("get_data_node", get_data_node)
workflow.add_node("optimize_answers", optimize_answers)

workflow.add_edge(START, "get_related_tools")
workflow.add_edge("get_related_tools", "get_data_node")
workflow.add_edge("get_data_node", "optimize_answers")
workflow.add_edge("optimize_answers", END)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
wenshu = workflow.compile(name="wenshu")