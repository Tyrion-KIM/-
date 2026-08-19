# scripts/kpi_model.py
# -*- coding: utf-8 -*-
"""物流团队绩效 V1 指标模型：指标定义 + 得分公式（与 Excel 模板公式一一镜像）。"""
from dataclasses import dataclass

FT_COST_AB = "成本-计算"; FT_COST = "成本-直填"; FT_RATE = "达标率"
FT_UPPER = "上限"; FT_LOWER = "下限"; FT_PAY = "请款"
FT_STOCK = "库存综合"; FT_THREE = "三段综合"
FT_AVG_PAY = "引用-请款均"; FT_AVG_SPEC = "引用-专员均分"

PEOPLE = ["吴佳钒", "郑舒漫", "黄婷", "吴定佳", "张雨洁", "金炜铮"]
SPECIALISTS = PEOPLE[:4]          # 主管卡的"专员均分"不含实习生
TASK_WEIGHT = 30
QUANT_WEIGHT = 70

@dataclass(frozen=True)
class Indicator:
    id: str; person: str; line: str; name: str; ftype: str
    target: object      # 数值或 None；引用类为 None
    unit: str; weight: float
    raw: tuple          # 各原始字段含义说明，如 ("发货数量A","运费折欧B")
    source: str; scope: str   # 数据源 / 取值口径

INDICATORS = [
 # 吴佳钒 rows 4-9
 Indicator("K01","吴佳钒","DDP头程","成本","成本-计算",15,"欧/台",27,("发货数量A","运费折欧B"),"头程大表；长期易仓","当月签收订单"),
 Indicator("K02","吴佳钒","DDP头程","时效","达标率",None,"%",18,("达标单数","总单数"),"头程大表；长期易仓","当月签收订单，标准时效"),
 Indicator("K03","吴佳钒","始发计划","缺货率","上限",0.05,"%",5,("实际缺货率(小数)",),"库内MES+排产表","每周一交付计划"),
 Indicator("K04","吴佳钒","始发计划","缺货时间","上限",7,"天",5,("实际缺货天数",),"库内MES+排产表","缺货持续≤7天"),
 Indicator("K05","吴佳钒","在途库存","上架准确率","下限",0.95,"%",5,("实际上架准确率(小数)",),"各仓入库单上架情况",""),
 Indicator("K06","吴佳钒","财务","请款-DDP","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 郑舒漫 rows 10-13
 Indicator("K07","郑舒漫","FOB","单证准确率","下限",1.0,"%",15,("单证准确率(小数)",),"货代台账","我方单证零差错"),
 Indicator("K08","郑舒漫","FOB","订舱及时率","达标率",None,"%",10,("按时回传S/O单数","总单数"),"货代台账","OA审单→S/O≤1个工作日"),
 Indicator("K09","郑舒漫","FCA","执行时效","达标率",None,"%",25,("48h内达标单数","总单数"),"OA订单数据","OA申请→工厂发出≤48h"),
 Indicator("K10","郑舒漫","财务","请款-FOB","请款",None,"",20,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 黄婷 rows 14-20
 Indicator("K11","黄婷","B端中转","成本","成本-计算",15,"欧/台",21,("签收数量A","运费折欧B"),"当月核对账单","当月签收"),
 Indicator("K12","黄婷","B端中转","时效","达标率",None,"%",14,("达标单数","总单数"),"签收单+分段标准","DE1/DK2/AT2/SE1/SI2工作日；旺3-6淡7-2"),
 Indicator("K13","黄婷","目的国计划","缺货率","上限",0.05,"%",5,("实际缺货率(小数)",),"在库+待发+在途表","每周一交付计划"),
 Indicator("K14","黄婷","目的国计划","缺货时间","上限",7,"天",5,("实际缺货天数",),"在库+待发+在途表","缺货持续≤7天"),
 Indicator("K15","黄婷","B端库存","综合","库存综合",None,"",10,("长周期占比(小数)","平均库龄(天)","单台库内成本(欧)"),"各仓库存表+账单","≤3%/≤120天/≤5欧"),
 Indicator("K16","黄婷","财务","请款-B端仓库内","请款",None,"",7.5,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 Indicator("K17","黄婷","财务","请款-海外仓调拨","请款",None,"",7.5,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 吴定佳 rows 21-25
 Indicator("K18","吴定佳","一件代发","成本","成本-计算",15,"欧/台",24,("出库数量A","运费折欧B"),"正向仓账单+领星/易仓","当月出库"),
 Indicator("K19","吴定佳","一件代发","时效","达标率",None,"%",16,("达标单数","总单数"),"渠道承诺时效","出库单生成→签收；分段标准任务块定稿"),
 Indicator("K20","吴定佳","售后物流","退件率","上限",0.02,"%",10,("物流因素退件率(小数)",),"客服数据","≤2%"),
 Indicator("K21","吴定佳","C端库存","综合","库存综合",None,"",10,("长周期占比(小数)","平均库龄(天)","单台库内成本(欧)"),"各仓库存表+账单","≤3%/≤120天/≤5欧"),
 Indicator("K22","吴定佳","财务","请款-C端仓库内","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 张雨洁 rows 26-28
 Indicator("K23","张雨洁","特殊发运","时效","达标率",None,"%",40,("达标单数","总单数"),"头程大表；长期易仓","当月签收，按运输方式分段"),
 Indicator("K24","张雨洁","进口业务","时效","达标率",None,"%",20,("达标单数","总单数"),"待定","分段标准8月底前定，否则首月NA"),
 Indicator("K25","张雨洁","财务","账单协同-请款","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","协同雨洁表格"),
 # 金炜铮 rows 29-32
 Indicator("K26","金炜铮","团队","单台总成本","成本-直填",36,"欧/台",30,("当月实际单台总成本",),"财务核算","对齐降本分成方案结算线"),
 Indicator("K27","金炜铮","团队","三段结构","三段综合",None,"",20,("头程实际","尾程实际","仓储实际"),"财务核算","15/15/6，各段得分平均"),
 Indicator("K28","金炜铮","团队","团队请款及时率","引用-请款均",None,"",10,(),"全员请款线平均","打分表内自动引用"),
 Indicator("K29","金炜铮","团队","专员均分","引用-专员均分",None,"",10,(),"4位专员总分平均","打分表内自动引用"),
]

# ---------- 得分公式（与 Excel 模板镜像，勿单边修改） ----------
def score_cost(target, actual):
    """成本类：min(100, 100*目标/实际)。"""
    return min(100.0, 100.0 * target / actual)

def score_rate(passed, total):
    """达标率：达标数/总数*100。"""
    return min(100.0, passed / total * 100.0)

def score_upper(target, actual):
    """上限类：达标100，未达标 100*目标/实际。"""
    return 100.0 if actual <= target else 100.0 * target / actual

def score_lower(target, actual):
    """下限类：达标100，未达标 100*实际/目标。"""
    return 100.0 if actual >= target else 100.0 * actual / target

def score_payment(late_days, amount_ratio):
    """请款：时间50% + 金额50%。迟1个工作日-20（下限0）；金额 min(100, 占比/0.9*100)。"""
    time_s = max(0.0, 100.0 - 20.0 * late_days)
    amt_s = min(100.0, amount_ratio / 0.9 * 100.0)
    return 0.5 * time_s + 0.5 * amt_s

def score_stock(long_ratio, age_days, cost):
    """库存综合：三项上限类得分平均（3% / 120天 / 5欧）。"""
    return (score_upper(0.03, long_ratio) + score_upper(120, age_days)
            + score_upper(5, cost)) / 3.0

def score_three(head, tail, ware):
    """三段综合：头程15/尾程15/仓储6 各成本类得分平均。"""
    return (score_cost(15, head) + score_cost(15, tail) + score_cost(6, ware)) / 3.0

def row_scores(ind, i=None, j=None, k=None):
    """按公式类型重算指标分。原始值缺任一必要项 → None（降级）。"""
    t = ind.ftype
    if t == FT_COST_AB:
        return None if not i or not j else score_cost(ind.target, j / i)
    if t == FT_COST:
        return None if not i else score_cost(ind.target, i)
    if t == FT_RATE:
        return None if not j else score_rate(i or 0, j)
    if t == FT_UPPER:
        return None if i is None else score_upper(ind.target, i)
    if t == FT_LOWER:
        return None if i is None else score_lower(ind.target, i)
    if t == FT_PAY:
        return None if i is None or j is None else score_payment(i, j)
    if t == FT_STOCK:
        return None if i is None or j is None or k is None else score_stock(i, j, k)
    if t == FT_THREE:
        return None if not i or not j or not k else score_three(i, j, k)
    raise ValueError(f"引用类指标 {ind.id} 不在此计算，由汇总层处理")

def personal_total(pairs, task):
    """个人总分：可用项权重归一化。pairs=[(指标分|None,权重)]；task=任务块均分|None。"""
    avail = [(s, w) for s, w in pairs if s is not None]
    num = sum(s * w for s, w in avail)
    den = sum(w for _, w in avail)
    if task is not None:
        num += task * TASK_WEIGHT
        den += TASK_WEIGHT
    return num / den if den else None
