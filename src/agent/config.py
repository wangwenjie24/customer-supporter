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