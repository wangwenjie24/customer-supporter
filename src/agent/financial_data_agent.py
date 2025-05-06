import os
import dotenv
import json
import pymysql
import redis
import uuid

from langgraph.store.memory import InMemoryStore
from langgraph_bigtool import create_agent
from langchain_core.tools import StructuredTool
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI


from agent.prompts import financial_data_researcher_instructions

# 加载环境变量
dotenv.load_dotenv()

# 从环境变量中读取 MySQL 配置
mysql_config = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT')),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
}

# =================== 数据库操作函数 ===================

def rows_to_dict_list(column_names, rows):
    """
    将数据行与字段名称结合成字典列表
    
    Args:
        column_names: 列名列表
        rows: 数据行列表
        
    Returns:
        字典列表，每个字典表示一行数据
    """
    return [dict(zip(column_names, row)) for row in rows]
    
def fetch_data_with_column_names(connection, query):
    """
    执行SQL查询并返回列名和数据行
    
    Args:
        connection: 数据库连接对象
        query: SQL查询语句
        
    Returns:
        元组(列名列表, 数据行列表)
    """
    cursor = connection.cursor()
    cursor.execute(query)
    
    # 获取字段名称
    column_names = [desc[0] for desc in cursor.description]
    
    # 获取数据行
    rows = cursor.fetchall()
    
    # 返回字段名称和数据
    return column_names, rows

def get_data_from_db(sql_query: str) -> str:
    """
    从数据库获取数据
    
    Args:
        sql_query: SQL查询语句
        
    Returns:
        查询结果的字典列表或错误信息
    """

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
        # 确保连接关闭
        if 'connection' in locals() and connection.open:
            connection.close()

    return None


def create_function(func_name, func_body):
    """
    动态创建函数
    
    Args:
        func_name: 函数名称
        func_body: 函数体代码
        
    Returns:
        创建的函数对象
        
    Raises:
        NameError: 如果函数未在代码中定义
    """
    # 创建一个新的局部命名空间来执行函数定义
    local_namespace = {}
    # 执行函数体代码，将其加载到局部命名空间
    exec(func_body, globals(), local_namespace)
    # 从局部命名空间中获取定义的函数
    if func_name in local_namespace:
        return local_namespace[func_name]
    else:
        raise NameError(f"函数 {func_name} 未在代码中定义")


# =================== Redis连接与工具注册 ===================

# 初始化Redis客户端
redis_client = redis.StrictRedis(
        host=os.getenv("REDIS_HOST"),
        port=os.getenv("REDIS_PORT"),
        db=os.getenv("REDIS_DB"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True  # 自动将字节类型解码为字符串
    )

# 从Redis获取工具列表
tool_list = redis_client.lrange("fin_data_tool_list", 0, -1)  # 0 表示第一个元素，-1 表示最后一个元素

# 注册工具
tool_registry = {}
for item in tool_list:
    tool_info_data = json.loads(item)
    # 解析工具信息
    tool_name = tool_info_data["tool_name"]
    tool_body = tool_info_data["tool_body"]
    tool_description = tool_info_data["tool_desc"]
    tool_args_schema = json.loads(tool_info_data["args_schema"])
    
    # 动态创建函数对象
    tool_func = create_function(tool_name, tool_body)
    
    # 注册为结构化工具
    tool_registry[str(uuid.uuid4())] = StructuredTool.from_function(
        tool_func,
        name=tool_name,
        description=tool_description,
        args_schema=tool_args_schema
    )


# =================== 向量存储初始化 ===================

# 初始化 OpenAI 嵌入模型
embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.getenv("DASHSCOPE_EMBEDDINGS_API_KEY")
)

# 创建内存存储
store = InMemoryStore(
    index={
        "embed": embeddings,
        "dims": 1024,  # text-embedding-v3 的向量维度是 1024
        "fields": ["description"],
    }
)

# 将工具信息存入向量存储
for tool_id, tool in tool_registry.items():
    store.put(
        ("tools",),
        tool_id,
        {
            "description": str(f"{tool.name}: {tool.description}"),  # 确保转换为字符串
        },
    )

# =================== 代理初始化 ===================
llm = ChatOpenAI(
    model_name=os.getenv("OPENROUTER_MODEL_NAME"),
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base=os.getenv("OPENROUTER_API_BASE"),
    temperature=0.0
)


# 创建代理构建器
builder = create_agent(llm, tool_registry, limit=4)

# 编译代理
financial_data_agent = builder.compile(store=store, name="financial_data_agent")


# if __name__ == "__main__":

#     user_title = "王院长"
        
#     # 格式化指令
#     financial_data_researcher_instructions_formatted = financial_data_researcher_instructions.format(user_title=user_title)
        
#     # 构造消息列表
#     messages = [
#         SystemMessage(content=financial_data_researcher_instructions_formatted),
#         HumanMessage(content="2024年2月佛山电器照明股份有限公司营业收入同比增长是多少？")
#     ]

#     inputs = {"messages": messages}
#     for stream_mode, streamed_output in financial_data_agent.stream(inputs, stream_mode=["messages", "custom", "values"], config={"configurable": {"thread_id": "2", "user_id": "10001", "user_title": "万书记"}}):
#         # 如果是代理的消息，显示代理名称和内容

#         # print(stream_mode, streamed_output)
#         # if stream_mode == "custom":
#         #     print(streamed_output)
#         # # print(stream_mode, streamed_output)
#         # if stream_mode == "messages" and isinstance(streamed_output, tuple) and len(streamed_output) > 1:
#         #     chunk, metadata = streamed_output
#         #     if metadata.get("langgraph_node", "") == "agent" or metadata.get("langgraph_node", "") == "finalinze_output" or metadata.get("langgraph_node", "") == "generate_image_agent":
#         #         print(chunk.content, end="", flush=True)
#         if stream_mode == "values":
#             # 获取最后一条消息
#             last_message = streamed_output["messages"][-1]
#             # 确保是AIMessage类型并获取content
#             if isinstance(last_message, AIMessage):
#                 print(last_message.content)