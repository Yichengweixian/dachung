---
unit: U12R01
freeze_status: external_record
---

# U12R01 判据

至少2种子误差<0.5%且实际有效评估<101则supported；误差达标但评估>=101则inconclusive，不以首次达到阈值计数冒充总次数。三种子变差<网格成本0.5%另列。非Optimal失败保留并停止该运行。

未执行verdict=null；环境/数据缺失blocked，不能当作科学反驳。探索性结果不登记claims。正式求解前生成freeze.json；冻结后修改方法必须新单元。

