import json

import pandas as pd


def parse_tg43_excel(xls_path, sheet_name=0):
    df = pd.read_excel(xls_path, sheet_name=sheet_name, header=None)

    # 转成字符串方便搜索
    df_str = df.astype(str)

    # -----------------------------
    # 1. 找 Dose Rate Constant Λ
    # -----------------------------
    dose_rate_constant = None
    for i in range(len(df)):
        row_text = " ".join(df_str.iloc[i].tolist()).lower()
        if "dose rate constant" in row_text:
            for val in df.iloc[i]:
                try:
                    dose_rate_constant = float(val)
                    break
                except:
                    continue

    if dose_rate_constant is None:
        print("⚠️ 未找到 Λ，设为 1.0（需要你手动改）")
        dose_rate_constant = 1.0

    # -----------------------------
    # 2. 找 g(r)
    # -----------------------------
    g_r = []
    g_start = None

    for i in range(len(df)):
        row_text = " ".join(df_str.iloc[i].tolist()).lower()

        if "radial dose function" in row_text or "g(r)" in row_text:
            g_start = i
            break

    if g_start is None:
        raise RuntimeError("❌ 未找到 g(r) 区域（Radial dose function）")

    # 往下找数据
    for i in range(g_start, len(df)):
        try:
            r = float(df.iloc[i, 0])
            g = float(df.iloc[i, 1])
            g_r.append([r, g])
        except:
            if len(g_r) > 5:
                break

    # -----------------------------
    # 3. 找 F(r,θ)
    # -----------------------------
    F_r_theta = {}
    theta_row = None

    for i in range(len(df)):
        row_text = " ".join(df_str.iloc[i].tolist()).lower()

        if "anisotropy" in row_text or "theta" in row_text:
            theta_row = i
            break

    if theta_row is None:
        raise RuntimeError("❌ 未找到 F(r,θ) 区域")

    # θ 值
    theta_vals = []
    for val in df.iloc[theta_row, 1:]:
        try:
            theta_vals.append(float(val))
        except:
            break

    # r + F
    for i in range(theta_row + 1, len(df)):
        try:
            r = float(df.iloc[i, 0])
        except:
            continue

        values = df.iloc[i, 1:1 + len(theta_vals)]

        row = []
        for k in range(len(theta_vals)):
            try:
                row.append([theta_vals[k], float(values.iloc[k])])
            except:
                pass

        if row:
            F_r_theta[r] = row

    # -----------------------------
    # 4. 输出
    # -----------------------------
    source_data = {
        "name": "I125_SelectSeed_130002",
        "dose_rate_constant": dose_rate_constant,
        "g_r": g_r,
        "F_r_theta": F_r_theta
    }

    return source_data


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# -----------------------------
# main
# -----------------------------
if __name__ == "__main__":
    xls_path = r"D:\code\TG43\125i-selectseed.xls"

    source = parse_tg43_excel(xls_path)

    print("✅ 解析成功")
    print("Λ =", source["dose_rate_constant"])
    print("g(r) 点数 =", len(source["g_r"]))
    print("F(r,θ) 层数 =", len(source["F_r_theta"]))

    save_json(source, "i125.json")
