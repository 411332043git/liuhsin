# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""把 data/ 裡的三份標準 CSV，整理成網頁可以直接用 <script> 載入的 docs/data.js。

用法：
  uv run work/build_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs" / "data.js"


def build_enrollment() -> dict:
    df = pd.read_csv(DATA / "enrollment.csv", encoding="utf-8-sig")
    g = (
        df.groupby(["semester", "college", "dept", "degree", "gender"], as_index=False)["count"]
        .sum()
    )
    return {
        "columns": ["semester", "college", "dept", "degree", "gender", "count"],
        "rows": g.values.tolist(),
    }


def build_leave() -> dict:
    df = pd.read_csv(DATA / "leave.csv", encoding="utf-8-sig")
    g = (
        df.groupby(["semester", "college", "dept", "degree", "gender", "reason"], as_index=False)[
            ["new_leave", "on_leave_end"]
        ].sum()
    )
    return {
        "columns": [
            "semester",
            "college",
            "dept",
            "degree",
            "gender",
            "reason",
            "new_leave",
            "on_leave_end",
        ],
        "rows": g.values.tolist(),
    }


def build_dept_aliases() -> dict:
    df = pd.read_csv(DATA / "dept_mapping.csv", encoding="utf-8-sig")
    aliases = {}
    for _, r in df.iterrows():
        raw = r["aliases"]
        names = [] if pd.isna(raw) else [s.strip() for s in str(raw).split(";") if s.strip()]
        aliases[r["dept"]] = names
    return aliases


def main() -> None:
    enrollment = build_enrollment()
    leave = build_leave()
    dept_aliases = build_dept_aliases()

    total_114_1 = sum(row[-1] for row in enrollment["rows"] if row[0] == "114-1")
    assert total_114_1 == 10035, f"114-1 在學人數合計應為 10035，實際為 {total_114_1}"
    print(f"核對：114-1 在學人數合計 = {total_114_1}（符合預期）")

    payload = {"enrollment": enrollment, "leave": leave, "deptAliases": dept_aliases}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.BI_DATA = ")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    size_kb = OUT.stat().st_size / 1024
    print(f"寫出 {OUT}（{size_kb:.1f} KB）")
    print(f"  enrollment: {len(enrollment['rows'])} 列")
    print(f"  leave: {len(leave['rows'])} 列")
    print(f"  deptAliases: {len(dept_aliases)} 個系所")


if __name__ == "__main__":
    main()
