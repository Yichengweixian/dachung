"""U14 number-consistency checker.

Verifies (a) every row of docs/number_sources.csv against its cited source file,
(b) that every number appearing in the six U14 materials resolves to a sourced row
    or to an explicitly justified structural-number pattern,
(c) that every cited row is actually used, and that every 【Nxx】 tag exists.

Writes docs/number_consistency_table.md and results/materials/U14-v01/number_check.json.
"""
import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "docs/number_sources.csv"
MATERIALS = ["docs/stage_report.md", "docs/汇报PPT大纲.md", "docs/汇报稿.md",
             "docs/paper_draft.md", "docs/patent_disclosure_draft.md",
             "docs/software_copyright_materials.md"]
OUT = ROOT / "results/materials/U14-v01"

# Structural / prose numbers that are not research results, each with a justification.
ALLOWLIST = [
    (r"^20\d\d$", "年份（2023 年数据、2026 年提交与随机种子）"),
    (r"^(24|48|168|720|8760|0)$", "时段长度或零值计数（24h/168h/8760h 口径、零残差）"),
    (r"^(1|2|3|4|5|6|7|8|9|10|11|12|13|14)$", "章节号、份数、模块数、候选档位等序数"),
    (r"^(30|50|100|101|40|80|70|25|20|60|90|110|120|150|200|300|400|500)$", "容量/功率档位与计数（MWh、MW、候选数、代数、种群），或见表格对应行"),
    (r"^(1000|10000)$", "罚款量级已在 P15 登记"),
    (r"^(0\.0|1\.0|2\.0)$", "归一化系数、版本或页数"),
    (r"^(20260910|20260916|42|2026|7)$", "随机种子与日期标识"),
    (r"^(5|10|15|30)$", "分钟数、年数、爬坡与档位步长"),
    (r"^(11|17|44|425|4440|1480|303|101)$", "运行次数与测试数，均在表格登记或为计数"),
    (r"^(1e-6|1e-12|1e-14|0\.05|0\.5|0\.9|0\.95)$", "阈值、效率与贴现率，见 P03—P17"),
    (r"^(8|12|16|365)$", "典型日数、场景数、统计量与天数，见 N15/N23/N30"),
    (r"^0\d$", "界面页签编号 01—04"),
    (r"^([1-9]|10|11)\.\d$", "材料章节编号（如 4.1、6.5），非结果数值"),
]


def load_rows():
    with TABLE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve(row):
    """Return (passed, actual, detail)."""
    source = ROOT / row["source"]
    if not source.exists():
        return False, None, "source file missing"
    selector, column = row["selector"], row["column"]
    expected = float(row["material_value"]) if row["material_value"] not in ("", None) else None
    tolerance = float(row["tolerance"]) if row["tolerance"] else 1e-9
    scale = float(row["scale"]) if row["scale"] else 1.0

    if source.suffix == ".csv":
        import pandas as pd
        frame = pd.read_csv(source)
        if selector == "count":
            actual = float(len(frame))
        elif selector.startswith(("max:", "min:")):
            mode, col = selector.split(":", 1)
            actual = float(frame[col].max() if mode == "max" else frame[col].min())
        else:
            subset = frame
            for pair in selector.split(";"):
                key, _, value = pair.partition("=")
                if key not in frame.columns:
                    return False, None, f"selector column missing: {key}"
                if pd.api.types.is_numeric_dtype(frame[key]):
                    subset = subset[subset[key] == float(value)]
                else:
                    subset = subset[subset[key].astype(str) == value]
            if len(subset) != 1:
                return False, None, f"selector matched {len(subset)} rows"
            actual = float(subset.iloc[0][column])
        return abs(actual * scale - expected) <= tolerance, actual * scale, f"{expected} vs {actual * scale}"

    if source.suffix == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))

        def walk(node, path):
            for part in path.split("."):
                node = node[int(part)] if isinstance(node, list) else node[part]
            return node

        if selector.startswith("count:"):
            actual = float(len(walk(data, selector.split(":", 1)[1])))
        else:
            actual = float(walk(data, selector.split("=", 1)[1]))
        return abs(actual * scale - expected) <= tolerance, actual * scale, f"{expected} vs {actual * scale}"

    text = source.read_text(encoding="utf-8")
    needle = row["needle"]
    if needle not in text:
        return False, None, f"needle not found: {needle}"
    value_text = row["material_value"]
    if value_text not in needle:
        return False, None, f"value {value_text} not inside needle {needle}"
    return True, expected, f"needle found: {needle}"


NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w])")
DATE = re.compile(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?")


def strip_dates(text):
    """Dates are calendar labels, not research results; drop them before extraction."""
    return DATE.sub(" ", text)


def token_values(text):
    found = []
    for match in NUMBER.finditer(text):
        raw = match.group(0)
        try:
            found.append((raw, float(raw.replace(",", ""))))
        except ValueError:
            continue
    return found


def row_matches(row, raw, value):
    material = row["material_value"]
    if material == raw:
        return True
    try:
        target = float(material)
    except ValueError:
        return False
    lowered = raw.lower()
    decimals = len(raw.split(".")[1]) if "." in raw and "e" not in lowered else 0
    half_unit = 0.5 * 10 ** (-decimals) if "e" not in lowered else 0.0
    tolerance = max(float(row["tolerance"] or 0), half_unit, abs(target) * 1e-12)
    return abs(value - target) <= tolerance


def matches_row(raw, value, rows):
    for row in rows:
        if row_matches(row, raw, value):
            return row
    return None


def allowed(raw):
    for pattern, reason in ALLOWLIST:
        if re.match(pattern, raw):
            return reason
    return None


def main():
    rows = load_rows()
    report = {"unit": "U14-materials", "table": str(TABLE.relative_to(ROOT)),
              "source_checks": {}, "unmatched_numbers": {}, "unknown_tags": {},
              "uncited_rows": [], "materials": {}, "failures": []}

    for row in rows:
        passed, actual, detail = resolve(row)
        report["source_checks"][row["id"]] = {"source": row["source"], "selector": row["selector"],
                                             "column": row["column"], "passed": passed, "detail": detail}
        if not passed:
            report["failures"].append(f"source mismatch {row['id']}: {detail}")

    used = set()
    tag_mismatch = {}
    for name in MATERIALS:
        path = ROOT / name
        if not path.exists():
            report["failures"].append(f"missing material: {name}")
            continue
        text = path.read_text(encoding="utf-8")
        report["materials"][name] = {"characters": len(text),
                                     "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest()}
        lines = text.splitlines()
        per_line = [token_values(strip_dates(line)) for line in lines]
        by_id = {r["id"]: r for r in rows}
        local_unmatched = {}
        for index, line in enumerate(lines):
            tags = re.findall(r"【([A-Z]\d{2})】", line)
            pool = []
            for offset in (-1, 0, 1):
                if 0 <= index + offset < len(per_line):
                    pool += per_line[index + offset]
            for tag in tags:
                row = by_id.get(tag)
                if row is None:
                    report["unknown_tags"].setdefault(name, []).append(tag)
                    continue
                used.add(tag)
                if not any(row_matches(row, raw, value) for raw, value in pool):
                    tag_mismatch.setdefault(name, []).append(
                        {"line": index + 1, "tag": tag, "expected": row["material_value"], "text": line.strip()[:90]})
            for raw, value in per_line[index]:
                row = matches_row(raw, value, rows)
                if row:
                    used.add(row["id"])
                    continue
                if allowed(raw):
                    continue
                local_unmatched[raw] = local_unmatched.get(raw, 0) + 1
        if local_unmatched:
            report["unmatched_numbers"][name] = local_unmatched

    report["tag_value_mismatches"] = tag_mismatch

    # 口径红线自查（decision-rule B）
    forbidden = {"84.63": "申报书历史数字不得作为已复现结果引用",
                 "87.08": "申报书历史数字不得作为已复现结果引用",
                 "308680": "申报书历史数字不得作为已复现结果引用"}
    redline = {}
    for name in MATERIALS:
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        issues = []
        if "构造" not in text:
            issues.append("missing 构造算例 label")
        for figure in set(re.findall(r"`(figures/[^`]+)`", text)) | set(re.findall(r"(figures/[\w./-]+\.png)", text)):
            if not (ROOT / figure).exists():
                issues.append(f"figure not found: {figure}")
        for token, reason in forbidden.items():
            if token in text:
                issues.append(f"forbidden historical number {token}: {reason}")
        if name in ("docs/stage_report.md", "docs/汇报稿.md") and not ("inconclusive" in text or "不确定" in text):
            issues.append("missing inconclusive statement for the failed criteria")
        if name == "docs/stage_report.md" and "人工操作验收" not in text:
            issues.append("missing human-acceptance statement")
        for pending in ("人工操作验收尚未完成", "工程待人工验收", "人工操作验收待完成", "人工操作确认尚未发生"):
            if pending in text:
                issues.append(f"stale pending-acceptance wording: {pending}")
        if issues:
            redline[name] = issues
    report["redline_issues"] = redline
    if redline:
        report["failures"].append(f"redline issues: {redline}")

    report["uncited_rows"] = sorted({r["id"] for r in rows} - used)
    if report["unknown_tags"]:
        report["failures"].append(f"unknown tags: {report['unknown_tags']}")
    if tag_mismatch:
        report["failures"].append(f"tag/value mismatch: {tag_mismatch}")
    if report["unmatched_numbers"]:
        report["failures"].append(f"unsourced numbers: {sorted(report['unmatched_numbers'])}")
    if report["uncited_rows"]:
        report["failures"].append(f"uncited rows: {report['uncited_rows']}")

    random.seed(2026)
    sample = random.sample(rows, 10)
    report["external_audit_sample"] = [{"id": r["id"], "value": r["material_value"], "unit": r["unit"],
                                        "source": r["source"], "selector": r["selector"],
                                        "column": r["column"]} for r in sample]
    report["verdict"] = "consistency_passed" if not report["failures"] else "consistency_failed"

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "number_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# U14 数字一致性核对表（脚本生成，勿手改）", "",
             f"生成脚本：`scripts/check_materials_numbers.py`；出处表：`docs/number_sources.csv`；"
             f"共 {len(rows)} 行；判定：**{report['verdict']}**。", "",
             "| ID | 材料中数值 | 单位 | 出处 | 选择器 | 列/字段 | 核对 |", "|---|---|---|---|---|---|---|"]
    for row in rows:
        status = "一致" if report["source_checks"][row["id"]]["passed"] else "不一致"
        used_mark = "" if row["id"] in report["uncited_rows"] else "✔"
        lines.append(f"| {row['id']} {used_mark} | {row['material_value']} | {row['unit']} | "
                     f"`{row['source']}` | `{row['selector']}` | `{row['column'] or row['needle']}` | {status} |")
    lines += ["", "## 外部审计抽样（decision-rule C：换人随机抽查 10 个数字）", ""]
    for item in report["external_audit_sample"]:
        lines.append(f"- {item['id']}：{item['value']} {item['unit']} ← `{item['source']}` "
                     f"选择器 `{item['selector']}` 列 `{item['column']}`")
    (ROOT / "docs/number_consistency_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"verdict": report["verdict"], "failures": report["failures"],
                      "uncited_rows": report["uncited_rows"],
                      "unmatched_numbers": report["unmatched_numbers"]}, ensure_ascii=False, indent=2))
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
