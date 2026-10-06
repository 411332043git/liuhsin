# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "xlrd"]
# ///
"""把 114-1 在學人數統計表 (.xls) 轉成整齊的 CSV。

用法：
  uv run work/etl_enrollment.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "東華大學統計資料" / "在學人數統計表" / "114-1在學生人數統計表1141020--網路公告-10035人.xls"
DST = ROOT / "work" / "enrollment_114-1.csv"

# 哪個「學制別 合計」區塊，對應哪個 program_raw
BLOCK_TO_PROGRAM = [
    (re.compile(r"碩專班"), "碩士在職專班"),  # 要先於「碩士班」判斷，避免誤判
    (re.compile(r"博士班"), "博士班"),
    (re.compile(r"碩士班"), "碩士班"),
    (re.compile(r"學士班"), "學士班"),
]


def block_to_program(block_label: str) -> str | None:
    for pattern, program in BLOCK_TO_PROGRAM:
        if pattern.search(block_label):
            return program
    return None


def strip_note(s: str) -> str:
    """去掉括號裡的註記，例如「環境暨海洋學院(111更名 )」-> 「環境暨海洋學院」"""
    return re.sub(r"[（(].*?[）)]", "", s).strip()


# 原始報表中，「應用物理博士班一般組(106起)」這一列的系所欄位是空白，
# 照合併規則往上承接會誤歸到「材料科學與工程學系」；但它實際屬於「物理學系」
# （「物理學系」這個系所名稱要再晚一列才出現）。這是原始報表本身的個案錯誤，
# 用分組欄位的文字內容特判修正。
GROUP_DEPT_OVERRIDE = {
    "應用物理博士班一般組(106起)": "物理學系",
}


def main() -> None:
    raw = pd.read_excel(SRC, sheet_name=0, header=None)

    current_block = None   # 目前所在的「學制別 合計」區塊文字
    current_college = None
    current_dept = None
    rows = []

    for _, r in raw.iloc[3:].iterrows():
        block, college, dept, group, total = r[0], r[1], r[2], r[3], r[4]

        is_header_row = pd.notna(block) and pd.isna(college) and pd.isna(dept)
        if pd.notna(block):
            current_block = block
        if is_header_row:
            # 總計 / 各學制合計列，不是資料列，跳過（但已用來更新 current_block）
            continue

        if pd.notna(college):
            current_college = strip_note(str(college))
        if pd.notna(dept):
            current_dept = str(dept).strip()

        if pd.isna(total):
            # 最下方的備註列
            continue

        program = block_to_program(str(current_block))
        if program is None or current_college is None or current_dept is None:
            continue

        dept_for_row = GROUP_DEPT_OVERRIDE.get(str(group).strip(), current_dept)

        female = 0 if pd.isna(r[5]) else int(r[5])
        male = 0 if pd.isna(r[6]) else int(r[6])
        rows.append((current_college, dept_for_row, program, "女", female))
        rows.append((current_college, dept_for_row, program, "男", male))

    df = pd.DataFrame(rows, columns=["college", "dept_raw", "program_raw", "gender", "count"])
    df = df.groupby(["college", "dept_raw", "program_raw", "gender"], as_index=False)["count"].sum()

    DST.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DST, index=False, encoding="utf-8-sig")
    print(f"寫出 {len(df)} 列 -> {DST}")


if __name__ == "__main__":
    main()
