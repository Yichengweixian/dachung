# U11R07 冻结前登记

诊断入口 `scripts/diagnose_u11r06_serialization.py`；输出 `results/annual/U11R07-v01/diagnosis.json`、`reconstructed.mps` 和 `replayed_models/`。使用 `scripts/diagnose_u11r04_serialization.py` 的已验证解析与 Decimal 计算结构，调整到 U11R06 模型/失败阶段；不修改旧脚本。

以 U11R06-v01 manifest 为准校验源与产物 SHA-256。只读分析不调用 CBC、PuLP 求解或任何网络。测试仅验证解析/诊断代码行为，不改变原研究证据。
