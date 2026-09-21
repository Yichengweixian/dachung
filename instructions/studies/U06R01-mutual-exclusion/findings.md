---
unit: U06R01
status: complete
verdict: supported
---

U06R01-v03七场景全部Optimal，最大残差7.37365724035044e-12；逐时CSV读回通过。
记录见results/optimization/U06R01-v03/summary.csv及run_manifest.json。
v01 Windows CBC threads=1停滞，v02 saveSolution错误拼接Windows绝对路径；均保留failure和诊断。
v03串行threads=0、临时目录相对路径，读取原生double，不放宽1e-6阈值。
旧U06连续LP失败结论保留；互斥通过只属于本修订单元。
