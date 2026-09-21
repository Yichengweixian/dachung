---
unit: U11R02
freeze_status: external_record
---

# U11R02 判据

输入8760连续UTC小时，单位元数据有效，无缺失非有限；365日全部Optimal，聚类两次标签一致。至少一个N年度消纳率和弃电率绝对误差<=1个百分点则主判据supported，否则inconclusive。种子7及N相邻档趋势另列，不因结果改N/种子/阈值。若稳健性失败总体inconclusive。

未执行verdict=null；环境/数据缺失blocked，不能当作科学反驳。探索性结果不登记claims。正式求解前生成freeze.json；冻结后修改方法必须新单元。

