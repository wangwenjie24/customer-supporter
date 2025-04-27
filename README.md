# 客户支持智能助手（Customer Supporter）

## 项目概述

客户支持智能助手是一个基于LangGraph构建的多功能AI助手系统，专为企业内部服务设计。该系统集成了多种功能模块，包括人力资源咨询、财务数据查询、法律合同分析、票据识别和图像生成等功能，旨在提高企业内部服务效率和质量。

## 主要功能

系统基于路由机制将用户请求分发到不同的专业代理（Agent）处理：

1. **人力资源咨询（HR Agent）**
   - 解答员工关于人力资源政策、福利和工作流程的问题
   - 提供个性化的人力资源支持

2. **财务数据查询（Financial Data Agent）**
   - 查询和分析财务数据
   - 提供财务报表和数据分析结果

3. **法律合同分析（Corporate Legal Agent）**
   - 分析合同中的法律风险
   - 提供合同审查和建议
   - 支持PDF格式的合同文件

4. **票据识别（Receipt Agent）**
   - 自动识别各类票据（发票、机票等）
   - 提取并结构化票据信息
   - 支持多种票据类型

5. **图像生成（Image Agent）**
   - 根据文本描述生成相关图像
   - 支持提示词优化
   - 基于达摩院的通义万相模型

## 技术架构

项目基于以下技术构建：

- **LangGraph**: 用于构建多代理系统和工作流
- **LangChain**: 提供基础组件和集成能力
- **OpenAI API**: 提供高级语言处理能力
- **达摩院通义系列模型**: 提供视觉和语言处理能力
- **DashScope API**: 提供图像生成能力

## 安装指南

### 前置要求

- Python 3.9+
- 有效的OpenAI API密钥
- 有效的达摩院API密钥（用于图像生成）
- 有效的通义千问API密钥（用于票据识别）

### 安装步骤

1. 克隆仓库：

```bash
git clone [仓库URL]
cd customer-supporter
```

2. 安装依赖：

```bash
pip install .
```

或者使用开发模式：

```bash
pip install -e ".[dev]"
```

3. 配置环境变量：

创建`.env`文件并设置必要的API密钥：

```
OPENAI_API_KEY=your_openai_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key
MODEL_SCOPE_API_KEY=your_modelscope_api_key
MODEL_SCOPE_API_BASE=your_modelscope_api_base
CHATBI_BASE_URL=your_chatbi_base_url
```

## 使用方法

### 启动服务

使用以下命令启动LangGraph API服务：

```bash
langgraph serve
```

### API接口

系统提供以下API端点：

- `/agent`: 主要路由入口，根据请求类型分发到不同代理
- `/receipt_regnoice_workflow`: 票据识别服务
- `/generate_image_workflow`: 图像生成服务
- `/contract_review_workflow`: 合同审查服务

### 示例请求

法律合同分析：
```python
inputs = {
    "messages": [("user", "请站在甲方角度分析以下合同文本中的法律风险。合同路径：[合同URL]")], 
    "action": "corporate_legal_agent"
}
```

票据识别：
```python
inputs = {
    "messages": [("user", "识别票据")], 
    "action": "receipt_regnoice_agent", 
    "receipt_image": "[票据图片URL]"
}
```

图像生成：
```python
inputs = {
    "prompt": "一只狗在森林里奔跑", 
    "action": "optimize_prompt"
}
```

财务数据查询：
```python
inputs = {
    "query": "2023年公司的营业收入是多少？"
}
```

## 开发指南

### 项目结构

```
customer-supporter/
├── src/
│   └── agent/
│       ├── corporate_legal_agent.py        # 法律合同分析模块
│       ├── financial_agent.py              # 财务分析模块
│       ├── finacial_data_query_workflow.py # 财务数据查询流程
│       ├── generate_image.py               # 图像生成模块
│       ├── graph.py                        # 主图结构定义
│       ├── hr_agent.py                     # 人力资源模块
│       ├── receipt_regnoice_workflow.py    # 票据识别流程
│       ├── contract_review_workflow.py     # 合同审查流程
│       ├── prompts.py                      # 系统提示词
│       ├── utils.py                        # 工具函数
│       ├── config.py                       # 配置文件
│       ├── configuration.py                # 配置类定义
│       └── state.py                        # 状态定义
├── static/                                # 静态资源文件
├── tests/                                 # 测试目录
├── langgraph.json                         # LangGraph服务配置
├── pyproject.toml                         # 项目配置和依赖
└── docker-compose.yml                     # Docker配置
```

### 添加新功能

要添加新的代理或功能：

1. 在`src/agent/`目录下创建新的代理模块
2. 更新`graph.py`中的路由功能和节点配置
3. 如需要，在`langgraph.json`中注册新的图入口点

## 许可证

本项目采用MIT许可证。有关详细信息，请参阅LICENSE文件。

## 贡献指南

欢迎贡献代码、报告问题或提出改进建议。
