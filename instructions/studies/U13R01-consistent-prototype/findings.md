---
unit: U13R01
status: complete
verdict: supported
---

## 人工验收补充登记（本次会话）

用户（项目负责人）于本会话文字确认人工操作验收**通过**，逐项范围为：页面加载、24h MILP 结果数值、
加入方案对比、101 点网格最优、负容量报错、规则模式出图。
登记文件：results/prototype/human_acceptance_v01/human_acceptance.json（含操作者、时间、用户原话、核对项与依据）。
按冻结判据"缺少人工操作确认则注明该项待用户验收"，该项现已确认，故本单元 verdict 由 inconclusive 更新为 **supported**。
说明：该确认来自用户在会话中的文字答复，属人工确认而非机器可验证记录；当次运行的机器记录
results/prototype/U13R01-v01/run_manifest.json 中的 verdict=inconclusive 未改写，作为历史保留。

原型七模块自动化验收（U13R01-v01）全部执行：24h MILP 与 U06R01-v03/main_hourly.csv 逐值差 1.4210854715202004e-14；
规则模式与 E40_P20 逐时差 4.2105180453333446e-11、汇总差 1.9753088054130785e-11；
168h 界面与同run的CLI路径差 1.4210854715202004e-14；101候选网格与 U09R01-v01/summary.csv 差 5.820766091346741e-11；
CSV写盘读回差 1.4210854715202004e-14；PNG可解析；空CSV与负容量均被拒绝并给提示。
证据：results/prototype/U13R01-v01/{run_manifest.json,checks.json,ui_milp_24h.csv,ui_milp_168h.csv,ui_grid.csv,dispatch_export.png}。

真实浏览器验收（Chrome/152.0.7977.83，CDP自动化）：页面加载、24h MILP求解、加入方案对比、101点网格、负容量报错五步全部通过，
控制台错误0，截图见 results/prototype/browser_check_v02/。浏览器显示值与冻结结果一致：消纳率81.823%、弃电395.500 MWh、
缺供0.000 MWh、总成本496,637.539元（与U06R01-v03 main行在小数显示精度内相同）；网格最优70 MWh/25 MW、486,358.65元/24h与U09R01冻结最优相同。
浏览器证据为自动化代理，不冒充人工确认：browser_checks.json 明确记录 human_confirmation=false。

独立审计（另进程、不导入src）：run_manifest记录的产物SHA-256全部一致；记录的src/*.py与run_*.py自运行后未改动；
两条界面-基准逐值比较、网格比较、浏览器数值比较全部通过；规则基准在原进程重算得 4.2105180453333446e-11，与run记录相同。
报告：results/prototype/audit_v01/audit_report.json（verdict=audit_passed）。

失败与限制（保留，不删除）：
- browser_check_v01 两步失败（03 加入方案对比、05 负容量），定位为驱动脚本等待/选择器缺陷：点击前未等待元素渲染、数字输入用aria-label定位失败。
  仅修改驱动脚本、未改应用代码后 v02 全部通过；v01 证据保留在 results/prototype/browser_check_v01/。
- 按冻结判据"缺少人工操作确认则注明该项待用户验收，不冒充人工"：机器验收阶段总判定曾为 inconclusive；
  用户于本会话确认人工操作验收通过后，该项闭环，本单元最终 verdict 为 supported（见文首补充登记）。
- 网格寻优仅限24h输入；>168h 用独立日模式、无跨日储能耦合；168h一致性比较的是界面与该run自身的CLI调用。
- 驱动脚本自带的 charts 计数查询（img[src^="data:image/png"]）返回0，实际截图已显示图表；通过判据改用更宽的 stImage/canvas 选择器，属计数口径问题，不是界面缺陷。
- 未向环境新增浏览器自动化依赖（websocket-client 安装在沙箱内失败，未采用）；浏览器驱动仅用标准库实现。
- 全量测试在本次验收中重跑：44项，OK，逐项日志见 results/prototype/audit_v01/unit_tests_20260916.txt
  （该次重跑需在更宽的文件权限下执行，因测试用临时目录的 chmod 在当前沙箱被拒；沙箱拒绝本身不是测试失败）。
- 服务边界核对：.streamlit/config.toml 为 address=127.0.0.1、gatherUsageStats=false，与冻结执行边界一致；验收用服务保持在本机 8513 端口，
  便于用户完成人工确认后关闭。
