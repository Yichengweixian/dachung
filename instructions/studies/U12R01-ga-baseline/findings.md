---
unit: U12R01
status: complete
verdict: inconclusive
---

U12R01-v01，三种子各1480次，共4440次有效评估，全部Optimal并通过保存CSV独立审计。
相对网格成本误差分别0.0800103%、0.0793060%、0.0777284%，全部低于0.5%；种子稳健性通过。
评估次数均超过101，fast_accurate_seeds=0，按冻结规则inconclusive，不能声称加速。
证据：results/ga/U12R01-v01/{run_manifest.json,summary.csv,seed*_convergence.csv}；收敛图已打开检查。
网格离散、GA连续，GA略低的成本不等于网格错误或连续全局最优。
