# U00 设计：版本基线与产物清单

## 目标产物

1. 本地 git 仓库：项目根 `git init`，`.gitignore` 已有（排除 .venv/、__pycache__/、.cache/ 等），不配置远程
2. `results/` 下新增 `baseline_manifest.json`（或 instructions/ 下）：文件清单 + SHA-256 + 环境版本
3. 全量测试运行记录（输出重定向到文件保存）

## 清单脚本（Windows 约定）

使用 Python 标准库，项目根相对路径遍历，排除 `.venv/`、`.cache/`、`__pycache__/`、`.claude/`：

```python
# 示例：计算项目产物清单哈希（执行时放入 src/ 或 scripts/）
import hashlib, json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
exclude = {".venv", ".cache", "__pycache__", ".claude", ".git"}
items = {}
for p in sorted(root.rglob("*")):
    if p.is_file() and not any(part in exclude for part in p.parts):
        rel = str(p.relative_to(root)).replace("\\", "/")
        items[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps(items, indent=2, ensure_ascii=False))
```

清单 JSON 另存为 `instructions/baseline_manifest.json`；再次运行哈希完全一致才算通过（git 元数据目录不参与）。

## 环境记录

- `.\.venv\Scripts\python.exe --version`
- `.\.venv\Scripts\python.exe -m pip list`（全量输出保存）
- `git --version`

## 提交约定

- 初始提交：当前全部项目文件（U00 执行前状态）
- 之后每个单元收尾时提交一次，提交信息格式：`UXX: 简要说明`
- 444.docx 是否入库由用户决定（默认入库，文件只读不改）

## 复用与注意

- 不使用 Unix 工具（shasum/find -exec 等），全部用 Python 实现，保证 Windows 可复现
- 文件读写统一 `encoding="utf-8"`
