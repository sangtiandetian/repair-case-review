#!/usr/bin/env python3
"""维修案例复盘 · 案例卡生成器

把一次维修的原始记录（文本文件）整理成标准案例卡，并向案例库索引追加一行。

用法：
    python3 case_card.py --input notes.txt [--out ./cases] [--index ./cases/index.md] [--date 2026-10-30]

记录文件约定（全部可选，缺的字段在卡上标「未记录」，脚本绝不编造读数）：
    以「板型：」「现象：」「分类：」「阶段：」「结果：」「根因：」「修复：」「验收：」开头的行会被提取为对应字段；
    含有电压/阻值单位（V、mV、Ω、kΩ、MΩ）或「二极体值/对地阻值」字样的行会被收进检测路径表；
    其余行原样进入「现象（原话）」。

退出码：0 成功；2 参数或输入错误。
"""
import argparse
import re
import sys
from datetime import date as date_cls
from pathlib import Path

FIELD_LABELS = {
    "板型": "board", "设备": "board",
    "现象": "symptom",
    "分类": "category",
    "阶段": "stage",
    "结果": "result",
    "根因": "cause",
    "修复": "fix",
    "验收": "verify",
}
MEASURE_RE = re.compile(r"(\d+(?:\.\d+)?\s*(?:mV|V|kΩ|MΩ|Ω)|二极体值|对地阻值|阻值)")


def parse_notes(text):
    fields = {}
    raw_lines = []
    measures = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^([^：:]{1,4})[：:]\s*(.+)$", s)
        if m and m.group(1) in FIELD_LABELS:
            fields[FIELD_LABELS[m.group(1)]] = m.group(2).strip()
            continue
        if MEASURE_RE.search(s):
            measures.append(s)
        raw_lines.append(s)
    return fields, raw_lines, measures


def next_seq(cases_dir: Path, day: str) -> int:
    existing = list(cases_dir.glob(f"case-{day}-*.md")) if cases_dir.exists() else []
    return len(existing) + 1


def build_card(case_id, day, fields, raw_lines, measures):
    def f(key, default="未记录"):
        return fields.get(key, default)

    rows = []
    if measures:
        for i, line in enumerate(measures, 1):
            rows.append(f"| {i} | {line} | 未记录 | 未记录 | 未记录 | 见测点原文 | 未记录 |")
    else:
        rows.append("| 1 | 未记录 | 未记录 | 未记录 | 未记录 | 未记录 | 未记录 |")
    raw = "\n".join(raw_lines) if raw_lines else "未记录"
    return f"""# 案例 {case_id}：{f('board')} · {f('symptom')}

- 日期：{day}
- 板型/设备：{f('board')}
- 现象分类：{f('category')}
- 所属阶段：{f('stage')}
- 结果：{f('result')}

## 现象（原话）
{raw}

## 检测路径
| 步骤 | 测点（原文） | 档位 | 红笔 | 黑笔 | 读数 | 当时判断 |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## 关键转折点
未记录（复盘时补：哪一步读数让方向变了）

## 根因（复盘整理）
{f('cause')}

## 修复动作
{f('fix')}

## 验收数据
{f('verify')}

## 复盘三问（复盘整理）
1. 判断对在哪：未记录
2. 绕了什么弯路：未记录
3. 下次先测什么：未记录

## 理论补卡
未记录（复盘时按本案涉及的一个知识点补写）
"""


def ensure_index(index_path: Path):
    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            "# 案例库索引\n\n"
            "| 编号 | 日期 | 板型/设备 | 现象分类 | 根因 | 结果 | 卡片文件 |\n"
            "|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )


def main(argv=None):
    ap = argparse.ArgumentParser(description="维修案例复盘 · 案例卡生成器")
    ap.add_argument("--input", required=True, help="原始记录文本文件")
    ap.add_argument("--out", default="./cases", help="案例卡输出目录（默认 ./cases）")
    ap.add_argument("--index", default=None, help="索引文件路径（默认 <out>/index.md）")
    ap.add_argument("--date", default=None, help="案例日期 YYYY-MM-DD（默认今天）")
    args = ap.parse_args(argv)

    src = Path(args.input)
    if not src.exists():
        print(f"输入文件不存在：{src}", file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")
    day = args.date or date_cls.today().isoformat()
    day_compact = day.replace("-", "")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    seq = next_seq(out_dir, day_compact)
    case_id = f"{day_compact}-{seq:02d}"

    fields, raw_lines, measures = parse_notes(text)
    card = build_card(case_id, day, fields, raw_lines, measures)
    card_path = out_dir / f"case-{case_id}.md"
    card_path.write_text(card, encoding="utf-8")

    index_path = Path(args.index) if args.index else out_dir / "index.md"
    ensure_index(index_path)
    row = (
        f"| {case_id} | {day} | {fields.get('board', '未记录')} | "
        f"{fields.get('category', '未记录')} | {fields.get('cause', '未记录')} | "
        f"{fields.get('result', '未记录')} | {card_path.name} |\n"
    )
    with index_path.open("a", encoding="utf-8") as fh:
        fh.write(row)

    print(f"案例卡已生成：{card_path}")
    print(f"索引已更新：{index_path}")
    print(f"提取字段 {len(fields)} 个，检测路径 {len(measures)} 步")
    return 0


if __name__ == "__main__":
    sys.exit(main())
