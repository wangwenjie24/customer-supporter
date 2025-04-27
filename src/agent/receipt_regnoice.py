import os
import dotenv
import json
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.types import Command
from langgraph.config import get_stream_writer

from dataclasses import field
from typing import Any, Optional
from typing_extensions import TypedDict

from agent.configuration import Configuration
from agent.prompts import extractor_instructions, categorizer_instructions, receipt_instructions
from agent.utils import image_to_base64

dotenv.load_dotenv()

min_pixels=128*28*28
max_pixels=4096*28*28

# Initialize the processable kinds
llm = ChatOpenAI(
    model_name="Qwen/Qwen2.5-VL-72B-Instruct",
    openai_api_key=os.getenv("MODEL_SCOPE_API_KEY"),
    openai_api_base=os.getenv("MODEL_SCOPE_API_BASE"),
    temperature=0.0
)

# receipt_config = {
# 	"air_transport_receipt": {
# 		"feature": "It contains information such as serial number, passenger name, valid ID number, carrier, flight number, seat level, date, and time",
# 		"rules": [
# 			"For ´fare´, ´civil_aviation_development_fund´ and ´total´: remove 'CN' or 'CNY' prefix and any spaces, keep original numbers",
# 			"For ´fuel_surcharge´: should start with 'YQ', remove 'YQ' prefix and any spaces, keep original numbers'",
# 			"For ´other_taxes´: it is a number, keep original numbers",
#             "For all amounts: keep only digits and decimal point"
# 		],
# 		"examples": [
#             "'类型':'航空运输电子客票单', 'SERIAL NUMBER印刷字号':'55507095700','旅客姓名':'李博文','有效身份证件号码':'152127199408093011','签注':'Q/9HE10RV5/不得签转/改退收费','承运人':'国航','航班号':'CA8156','自FROM':'锡林浩特','至TO':'呼和浩特-白塔','座位等级':'W','日期':'2024-07-03','时间':'09:25','客票级别/客票类别':'W','客票生效日期':'','有效期截止日期':'25JUN','免费行李':'20K','票价':'610.00 CNY','民航发展基金':'EXEMPT YQ','燃油附加费':'30.00','其他税费':'','合计':'640.00 CNY','电子客票号码':'9995480673574','验证码':'9570','提示信息':'','保险费':'XXX','销售单位代号':'CAN 532 08351991','填开单位':'广州嘉宝商旅技术服务有限公司','填开日期':'2024-07-04'",
#             "'类型':'航空运输电子客票行程单','SERIAL NUMBER印刷字号':'55507097236','旅客姓名':'田忠天','有效身份证件号码':'150422199304013913','签注':'不得自愿签转','自FROM':'锡林浩特','至TO':'呼和浩特-白塔','承运人':'天航','航班号':'GS6614','座位等级':'','日期':'2024-07-03','时间':'17:00','客票级别/客票类别':'','客票生效日期':'','有效期截止日期':'','免费行李':'20K','票价':'470.00','民航发展基金':'50.00','燃油附加费':'30.00','其他税费':'','合计':'550.00','电子客票号码':'8265449276436','验证码':'9723','提示信息':'','保险费':'XXX','销售单位代号':'CAN53208351991','填开单位':'广州嘉宝商旅技术服务有限公司','填开日期':'2024-07-04'"
#         ]
# 	},
# 	"vat_invoice": {
# 		"feature": "It contains information such as the invoice number, date, buyer and seller details, item descriptions, prices, taxes, and totals.",
# 		"rules": [
# 			"For amounts: remove any currency symbols (￥, Y, CN, CNY), spaces and other non-numeric characters before processing, keep only digits and decimal point in the final output, especially for the ´total_amount_including_tax_lowercase´ field"
# 		],
# 		"examples": [
# 			"'类型':'北京增值税普通发票','发票号码':'42129756','开票日期':'2024年03月09日','购买方名称':'内蒙古科电电气有限责任公司','购买方纳税人识别号':'91150100720175351X','购买方地址、电话':'内蒙古自治区呼和浩特市和林格尔县盛乐经济园区北四街南侧电科院科技园区0471-6226440','购买方开户行及账号':'工商银行呼和浩特石羊桥东路支行0602005009024829865','items':[{'货物或应税劳务、服务名称':'住宿服务*住宿费','规格型号':'间','单位':'天','数量':'3','单价':'474.257425742','金额':'1422.77','税率':'1%','税额':'14.23'}],'合计金额':'1422.77','合计税额':'14.23','价税合计（大写）':'壹仟肆佰叁拾柒圆整','价税合计（小写）':'1437.00','销售方名称':'北京富国宾馆有限公司','销售方纳税人识别号':'911101017177635152','销售方地址、电话':'北京市东城区北新桥头条56号01084066811','销售方开户行及账号':'北京银行长城支行营业部01090365000120108081488','备注':'备注信息','收款人':'韩丹','复核人':'张伟','开票人':'韩晓芸'",
# 			"'类型':'内蒙古增值税电子专用发票','发票号码':'12208216','开票日期':'2023年07月15日','购买方名称':'内蒙古科电电气有限责任公司','购买方纳税人识别号':'91150100720175351X','购买方地址、电话':'呼和浩特市盛乐经济园区北四街南侧电科院科技园区0471-6226140','购买方开户行及账号':'工商银行呼和浩特石羊桥东路支行0602005009024829865','items':[{'货物或应税劳务、服务名称':'住宿服务*住宿','规格型号':'标间','单位':'天','数量':'9','单价':'215.811584158416','金额':'1942.57','税率':'1%','税额':'19.43'}],'合计金额':'1942.57','合计税额':'19.43','价税合计（大写）':'壹仟玖佰陆拾贰圆整','价税合计（小写）':'Y1962.00','销售方名称':'乌拉特中旗吴泽酒店宾馆','销售方纳税人识别号':'92150824MA7YQ1EUX0','销售方地址、电话':'巴彦淖尔市乌拉特中旗海流图镇13904720084','销售方开户行及账号':'中国农业银行乌拉特中旗支行05424101040022794','备注':'','收款人':'牛晓岚','复核人':'余震','开票人':'海英'"
# 		]
# 	}
# }

receipt_config = {
	"air_transport_receipt": {
		"feature": "It contains information such as serial number, passenger name, valid ID number, carrier, flight number, seat level, date, and time",
		"rules": [
			"For ´fare´, ´civil_aviation_development_fund´ and ´total´: remove 'CN' or 'CNY' prefix and any spaces, keep original numbers",
			"For ´fuel_surcharge´: should start with 'YQ', remove 'YQ' prefix and any spaces, keep original numbers'",
			"For ´other_taxes´: it is a number, keep original numbers",
            "For all amounts: keep only digits and decimal point"
		],
		"output_format": {
			"title": "标题",
			"serial_number": "SERIAL NUMBER印刷字号",
			"passenger_name": "旅客姓名",
			"valid_id_no": "有效身份证件号码",
			"endorsements": "签注",
			"from": "自FROM",
			"to": "至TO",
			"carrier": "承运人",
			"flight_number": "航班号",
			"class": "座位等级",
			"date": "日期",
			"time": "时间",
			"fare_basis": "客票级别/客票类别",
			"not_valid_before": "客票生效日期",
			"not_valid_after": "有效期截止日期",
			"free_baggage_allowance": "免费行李",
			"fare": "票价",
			"civil_aviation_development_fund": "民航发展基金",
			"fuel_surcharge": "燃油附加费",
			"other_taxes": "其他税费",
			"total": "合计",
			"e-ticket_number": "电子客票号码",
			"check_code": "验证码",
			"information": "提示信息",
			"insurance_fee": "保险费",
			"sales_agent_code": "销售单位代号",
			"issued_by": "填开单位",
			"issue_date": "填开日期"
		},
		"examples": [
            "{'title': '航空运输电子客票单', 'serial_number':'55507095700','passenger_name':'李博文','valid_id_no':'152127199408093011','endorsements':'Q/9HE10RV5/不得签转/改退收费','carrier':'国航','flight_number':'CA8156','from':'锡林浩特','to':'呼和浩特-白塔','class':'W','date':'2024-07-03','time':'09:25','fare_basis':'W','not_valid_before':'','not_valid_after':'25JUN','free_baggage_allowance':'20K','fare':'610.00 CNY','civil_aviation_development_fund':'EXEMPT YQ','fuel_surcharge':'30.00','other_taxes':'','total':'640.00 CNY','e_ticket_number':'9995480673574','check_code':'9570','information':'','insurance_fee':'XXX','sales_agent_code':'CAN 532 08351991','issued_by':'广州嘉宝商旅技术服务有限公司','issue_date':'2024-07-04'}", "{'title':'航空运输电子客票行程单','serial_number':'55507097236','passenger_name':'田忠天','id_no':'150422199304013913','endorsements':'不得自愿签转','from':'锡林浩特','to':'呼和浩特-白塔','carrier':'天航','flight_number':'GS6614','class':'','date':'2024-07-03','time':'17:00','fare_basis':'','not_valid_before':'','not_valid_after':'','free_baggage_allowance':'20K','fare':'470.00','civil_aviation_development_fund':'50.00','fuel_surcharge':'30.00','other_taxes':'','total':'550.00','e_ticket_number':'8265449276436','check_code':'9723','information':'','insurance_fee':'XXX','sales_agent_code':'CAN53208351991','issued_by':'广州嘉宝商旅技术服务有限公司','issue_date':'2024-07-04'}"
        ],
        "finalize_out_example": """### 航空运输电子客票行程单

- **票号**: 55507097236
- **旅客姓名**: 田忠天
- **有效身份证件号码**: 150422199304013913
- **签注**: 不得自愿签转
- **出发地**: 锡林浩特
- **目的地**: 呼和浩特-白塔
- **承运人**: 天航
- **航班号**: GS6614
- **舱位**: 
- **日期**: 2024-07-03
- **时间**: 17:00
- **票价基础**: 
- **有效期前**: 
- **有效期后**: 
- **免费行李额**: 20K
- **票价**: 470.00元
- **民航发展基金**: 50.00元
- **燃油附加费**: 30.00元
- **其他税费**: 
- **总金额**: 550.00元
- **电子客票号**: 8265449276436
- **校验码**: 9723
- **保险费**: XXX
- **销售代理代码**: CAN53208351991
- **出票单位**: 广州嘉宝商旅技术服务有限公司
- **出票日期**: 2024-07-04"""
	},
	"vat_invoice": {
		"feature": "It contains information such as the invoice number, date, buyer and seller details, item descriptions, prices, taxes, and totals.",
		"rules": [
			"For amounts: remove any currency symbols (￥, Y, CN, CNY), spaces and other non-numeric characters before processing, keep only digits and decimal point in the final output, especially for the ´total_amount_including_tax_lowercase´ field"
		],
		"output_format": {
			"title": "发票标题",
			"invoice_number": "发票号码",
			"issue_date": "开票日期",
			"buyer_name": "购买方名称",
			"buyer_tax_id": "购买方纳税人识别号",
			"buyer_address_phone": "购买方地址、电话",
			"buyer_bank_account": "购买方开户行及账号",
			"items": [{
				"item_name": "货物或应税劳务、服务名称",
				"specification": "规格型号",
				"unit": "单位",
				"quantity": "数量",
				"unit_price": "单价",
				"amount": "金额",
				"tax_rate": "税率",
				"tax_amount": "税额"
			}],
			"total_amount": "合计金额",
			"total_tax_amount": "合计税额",
			"total_amount_including_tax_capital": "价税合计（大写）",
			"total_amount_including_tax_lowercase": "价税合计（小写）",
			"seller_name": "销售方名称",
			"seller_tax_id": "销售方纳税人识别号",
			"seller_address_phone": "销售方地址、电话",
			"seller_bank_account": "销售方开户行及账号",
			"remarks": "备注",
			"payee": "收款人",
			"reviewer": "复核",
			"issuer": "开票人"
		},
		"examples": [
			"{'title':'北京增值税普通发票','invoice_number':'42129756','issue_date':'2024年03月09日','buyer_name':'内蒙古科电电气有限责任公司','buyer_tax_id':'91150100720175351X','buyer_address_phone':'内蒙古自治区呼和浩特市和林格尔县盛乐经济园区北四街南侧电科院科技园区0471-6226440','buyer_bank_account':'工商银行呼和浩特石羊桥东路支行0602005009024829865','items':[{'item_name':'住宿服务*住宿费','specification':'间','unit':'天','quantity':'3','unit_price':'474.257425742','amount':'1422.77','tax_rate':'1%','tax_amount':'14.23'}],'total_amount':'1422.77','total_tax_amount':'14.23','total_amount_including_tax_capital':'壹仟肆佰叁拾柒圆整','total_amount_including_tax_lowercase':'1437.00','seller_name':'北京富国宾馆有限公司','seller_tax_id':'911101017177635152','seller_address_phone':'北京市东城区北新桥头条56号01084066811','seller_bank_account':'北京银行长城支行营业部01090365000120108081488','remarks':'备注信息','payee':'韩丹','reviewer':'张伟','issuer':'韩晓芸'}",
			"{'title':'内蒙古增值税电子专用发票','invoice_number':'12208216','issue_date':'2023年07月15日','buyer_name':'内蒙古科电电气有限责任公司','buyer_tax_id':'91150100720175351X','buyer_address_phone':'呼和浩特市盛乐经济园区北四街南侧电科院科技园区0471-6226140','buyer_bank_account':'工商银行呼和浩特石羊桥东路支行0602005009024829865','items':[{'item_name':'住宿服务*住宿','specification':'标间','unit':'天','quantity':'9','unit_price':'215.811584158416','amount':'1942.57','tax_rate':'1%','tax_amount':'19.43'}],'total_amount':'1942.57','total_tax_amount':'19.43','total_amount_including_tax_capital':'壹仟玖佰陆拾贰圆整','total_amount_including_tax_lowercase':'Y1962.00','seller_name':'乌拉特中旗吴泽酒店宾馆','seller_tax_id':'92150824MA7YQ1EUX0','seller_address_phone':'巴彦淖尔市乌拉特中旗海流图镇13904720084','seller_bank_account':'中国农业银行乌拉特中旗支行05424101040022794','remarks':'','payee':'牛晓岚','reviewer':'余震','issuer':'海英'}"
		],
        "finalize_out_example": """### 发票类型：电子发票(普通发票)
### 发票号码：25127000000071463648
### 开票日期：2025年03月11日

### 购买方信息：
- 购买方名称：内蒙古科电数据服务有限公司
- 纳税人识别号：911501006928709119

### 销售方信息：
- 销售方名称：滴滴出行科技有限公司
- 纳税人识别号：911201163409833307

### 商品信息：
- 商品名称：*运输服务*客运服务费
- 数量：1
- 单价：68.11元
- 金额：68.11元
- 税率：3%
- 税额：2.04元

- 商品名称：*运输服务*客运服务费
- 金额：-9.34元
- 税额：-0.28元

### 合计信息：
- 含税总金额（大写）：陆拾圆伍角叁分
- 含税总金额（小写）：60.53元
- 不含税总金额：58.77元
- 总税额：1.76元"""
	}
}


class InputState(TypedDict):
    receipt_image: str
    should_convert: bool = True

class State(TypedDict):
    receipt_image: str
    running_category: str
    should_convert: bool
    text_output: Optional[dict[str, Any]] = field(default=None)
    json_output: Optional[dict[str, Any]] = field(default=None)

class OutputState(TypedDict):
    text_output: dict[str, Any]
    json_output: dict[str, Any]

def categorize(state: State, config: RunnableConfig) -> Command[Literal["extract", "__end__"]]:
    """ Recognize the type based on image content."""
    writer = get_stream_writer()
    writer({"action": "识别票据类型"})
    # Initialize the processable kinds
    processable_categories = ""
    for category, config_data in receipt_config.items():
        processable_categories += category + ": " + config_data["feature"] + "\n"
    # Format the recognizer instructions
    categorizer_instructions_formatted  = categorizer_instructions.format(
        processable_categories=processable_categories
    )
    # Call LLM
    result = llm.invoke([
        SystemMessage(content=categorizer_instructions_formatted),
        HumanMessage(content=[{
            "type": "image_url",
            "min_pixels": min_pixels,
            "max_pixels": max_pixels,
            "image_url": {"url": image_to_base64(state["receipt_image"])}
        }])
    ])

    if result.content == "unknown":
        writer({"action": "识别票据类型"})
        return Command(
            update={"text_output": f"不支持的票据类型"},
            goto="__end__"
        )
    else:
        writer({"action": "识别票据类型"})
        return Command(
            update={"running_category": result.content, "receipt_image": state["receipt_image"]},
            goto="extract"
        )


def extract(state: State, config: RunnableConfig) -> Command[Literal["finalinze_output"]]:
    """Extract data from the document."""
    writer = get_stream_writer()
    writer({"action": "提取票据信息"})
    # Get state
    receipt_image = state["receipt_image"]
    category = state["running_category"]
    # Format the extractor instructions
    extractor_instructions_formatted = extractor_instructions.format(
        category=category,
        rules="\n".join(["- " + rule for rule in receipt_config[category]["rules"]]),
        output_format=receipt_config[category]["output_format"],
        examples=receipt_config[category]["examples"]
    )
    # Call LLM
    result = llm.invoke([
        SystemMessage(content=extractor_instructions_formatted),
        HumanMessage(content=[{
            "type": "image_url",
            "min_pixels": min_pixels,
            "max_pixels": max_pixels,
            "image_url": {"url": image_to_base64(receipt_image)}
        }])
    ])
    
    extracted_data = json.loads(result.content)
    writer({"action": "提取票据信息"})
    return Command(
        update={"json_output": extracted_data},
        goto="finalinze_output"
    )
    
def finalinze_output(state: State, config: RunnableConfig):
    """Convert json to text"""

    if state.get("should_convert", True):
        # Get state
        json_output = state["json_output"]
        category = state["running_category"]
        # Convert json_output to string
        json_str = json.dumps(json_output, ensure_ascii=False)
        receipt_instructions_formatted = receipt_instructions.format(
            finalize_out_example=receipt_config[category]["finalize_out_example"]
        )
        response = ChatOpenAI(
            model_name="Qwen/Qwen2.5-72B-Instruct",
            openai_api_key=os.getenv("MODEL_SCOPE_API_KEY"),
            openai_api_base=os.getenv("MODEL_SCOPE_API_BASE"),
            temperature=0.0,
            tags=["call_regnoice_receipt"]
        ).invoke([
            SystemMessage(content=receipt_instructions_formatted),
            HumanMessage(content=json_str)
        ])
        return {"text_output": response.content}
    else:
        return {"text_output": ""}


# Create the graph
workflow = StateGraph(
    State, input=InputState, output=OutputState, config_schema=Configuration
)

workflow.add_node("categorize", categorize)
workflow.add_node("extract", extract)
workflow.add_node("finalinze_output", finalinze_output)
workflow.add_edge("__start__", "categorize")
workflow.add_edge("finalinze_output", "__end__")

receipt_regnoice = workflow.compile(name="receipt_regnoice")