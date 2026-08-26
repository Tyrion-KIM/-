# 物流团队绩效 V1

> 本目录已并入《物流团队管理体系-基准框架 v1.0》：基准框架 + 战役插件，四合一承接组织/目标/绩效/激励。
> 主文档：`物流团队管理体系-基准框架.md`；管控节奏打卡工具：`python -X utf8 scripts/build_rhythm_checklist.py`。
> 绩效卡结构 2026-08-26 调整为 5 稳定岗（雨洁卡撤销，K23/K24/K25 并入郑舒漫并重新配权）。

月度绩效记分卡（量化70% + 任务块30%）+ HTML 看板。设计文档见
docs/superpowers/specs/2026-08-19-logistics-team-kpi-design.md。

## 使用（每月）
1. 复制 [打分表模板] → 重命名 打分-YYYY-MM，B1 填月份
2. [任务块] 登记任务（月份/姓名/任务/验收物），月末打分 0/50/100
3. 打分表填原始数据（数据不可得选 NA，自动降级归一化）
4. 出看板：`python -X utf8 scripts/build_kpi_dashboard.py --month 2026-09`
5. 打开 output/kpi_dashboard_2026-09.html

## 重新生成模板
`python -X utf8 scripts/build_kpi_template.py`（覆盖 物流团队绩效V1.xlsx；历史打分 sheet 不受影响——重生成前先备份旧文件或在旧文件里直接复制新表）

## 测试
`python -X utf8 -m pytest tests/ -v`

## 关键规则
- 得分公式 / 降级规则 / 可控性原则 / 红绿灯阈值：见 [说明] sheet
- 权重固定至 2027-02 复盘；任务块成熟后降至 10-20% 再挂奖金
