import pandas as pd

xls_path = r"D:\code\TG43\125i-selectseed.xls"

# 读取整个 Excel
xls = pd.ExcelFile(xls_path)

print("📄 所有 Sheet：")
for name in xls.sheet_names:
    print(" -", name)

print("\n=============================\n")

# 遍历每个 sheet 并打印
for name in xls.sheet_names:
    print(f"\n📄 Sheet: {name}")
    print("-" * 50)

    df = pd.read_excel(xls_path, sheet_name=name, header=None)

    # 防止太宽被截断
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    print(df)