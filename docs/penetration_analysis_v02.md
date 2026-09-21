# 风光出力系数场景分析 v02

构造算例（非真实电网数据）；输入data/input_24h.csv，系数0.8/1.0/1.2/1.4同时缩放风光出力，储能0/40/80MWh，功率为容量的一半。
模型采用U06R01互斥MILP，经济参数来自冻结配置。系数不是新能源装机占比，也不是实际渗透率百分数。
U08-master-v01执行12个场景并反序重跑；24次全部Optimal，读回CSV独立审计通过，重复差0。
当前算例观察到：同一储能档位下弃电率随出力系数增加而不减；同一出力系数下消纳率随储能增加而不减；后40MWh的增益不超过前40MWh。
系数1.0时，0→40MWh增益3.557694991014955个百分点，40→80MWh增益2.004260636804986个百分点。
出处：results/penetration/U08-master-v01/marginal.csv，factor=1.0行；其余完整指标见summary.csv。
判据supported只表示冻结趋势在该构造矩阵中成立，不能外推普适的最优装机或收益。
三个图均来自保存的CSV，已实际打开检查；图片在figures/penetration/U08-master-v01/。
复现：`python run_penetration.py --run-id U08-recheck-v02`。
