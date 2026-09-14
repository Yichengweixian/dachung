# 新研究单元规格

适用全局策略：[execution-policy.md](../specs/execution-policy.md)。代码一律由 Codex 编写（用户手动粘贴），Claude 只读审查；一次只推进一个单元。

> 请为研究单元 UXX 建立规格。先读 specs/roadmap.md 的 Backlog 与相关单元的 findings，再从 studies/_TEMPLATE/ 复制五文件，填写：
>
> - question.md：一个可判定问题；mode 选择 exploratory 或 confirmatory；上游证据写清文件名
> - design.md：数据切片、变量单位、公式、参数配置文件、输出路径；所有数值必须来自 config 或明示出处
> - plan.md：组0 冻结清单 + 可直接粘贴执行的组1 提示词 + 组2 自查清单 + 组3 登记
> - decision-rule.md：A 有效性闸门、B 主判据（互斥、执行前定死阈值）、C 稳健性、D 论断映射、E 禁止事后修改
> - findings.md：保持模板初始状态
>
> 若旧单元已有结果，保留旧判据并说明新单元与旧单元差别。不要为肯定新方案删失败、切换 mode 或借用已看过的确认集。完成后停止。
