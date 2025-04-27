import os
import dotenv

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

# Initialize the processable kinds
# llm = ChatOpenAI(
#     model_name="Qwen/Qwen2.5-72B-Instruct",
#     openai_api_key=os.getenv("MODEL_SCOPE_API_KEY"),
#     openai_api_base=os.getenv("MODEL_SCOPE_API_BASE"),
#     temperature=0.0
# )

# llm=ChatOllama(model="qwen2.5:14b", temperature=0.0)

llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0
)