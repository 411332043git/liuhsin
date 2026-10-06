# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "xlrd"]
# ///
"""把 114-1 在學生人數統計表 (.xls) 轉成整齊的 CSV。

用法：
  uv run work/etl_enrollment.py
"""
import re
from pathlib import Path

import pandas as pd
import xlrd

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "東華大學統計資料" / "在學人數統計表"
DST = ROOT / "work" / "enrollment_114-1.csv"

# 區塊小計列（欄 A）→ program_raw；「碩專班」要先判斷
BLOCKS = [
    ("碩專班", "碩士在職專班"),
    ("博士班", "博士班"),
    ("碩士班", "碩士班"),
    ("學士班", "學士班"),
]
C_BLOCK, C_COLLEGE, C_DEPT, C_GROUP, C_FEMALE, C_MALE = 0, 1, 2, 3, 5, 6
FIRST_DATA_ROW = 4  # 0=標題 1~2=表頭 3=總計


def strip_note(s: str) -> str:
    return re.sub(r"[（(].*?[）)]", "", s).strip()


def num(v) -> int:
    return int(v) if v != "" else 0


def main() -> None:
    src = next(SRC_DIR.glob("114-1*.xls"))
    sh = xlrd.open_workbook(src, formatting_info=True).sheet_by_index(0)

    # 合併儲存格：值只在左上角，補到整個範圍
    cell = {(r, c): sh.cell_value(r, c) for r in range(sh.nrows) for c in range(sh.ncols)}
    for rlo, rhi, clo, chi in sh.merged_cells:
        v = cell[(rlo, clo)]
        for r in range(rlo, rhi):
            for c in range(clo, chi):
                cell[(r, c)] = v
    get = lambda r, c: cell[(r, c)]

    program = None
    rows = []
    for r in range(FIRST_DATA_ROW, sh.nrows):
        label = str(get(r, C_BLOCK)).strip()
        if label.startswith("備註"):
            break
        if "合計" in label:  # 區塊小計列，只用來切換學制
            program = next(p for k, p in BLOCKS if k in label)
            continue
        college = strip_note(str(get(r, C_COLLEGE)))
        dept = str(get(r, C_DEPT)).strip()
        if not dept:
            # 報表瑕疵：「應用物理博士班一般組」的系所格空白、也不在合併範圍內
            # （物理學系的合併範圍晚一列才開始），所以歸給下一個有名稱的系所
            nxt = r + 1
            while not str(get(nxt, C_DEPT)).strip():
                nxt += 1
            dept = str(get(nxt, C_DEPT)).strip()
        assert program and college and dept, f"第 {r + 1} 列缺學制/學院/系所"
        for gender, col in (("女", C_FEMALE), ("男", C_MALE)):
            rows.append((college, dept, program, gender, num(get(r, col))))

    df = pd.DataFrame(rows, columns=["college", "dept_raw", "program_raw", "gender", "count"])
    df = df.groupby(["college", "dept_raw", "program_raw", "gender"], as_index=False, sort=False)["count"].sum()
    df.to_csv(DST, index=False, encoding="utf-8-sig")
    print(f"寫出 {len(df)} 列，總人數 {df['count'].sum()} -> {DST}")


if __name__ == "__main__":
    main()
