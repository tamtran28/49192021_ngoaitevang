import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="FX kiểm toán 1201", layout="wide")
st.title("💱 Xử lý FX 1201 — Streamlit")
st.caption("Chỉ hỗ trợ .xlsx (engine openpyxl). Tải 4 file bên dưới rồi bấm **Chạy**.")

# --- Kiểm tra openpyxl sớm để báo lỗi dễ hiểu ---
try:
    import openpyxl  # noqa: F401
except Exception:
    st.error("Môi trường chưa có **openpyxl**. Chạy: `pip install openpyxl`.")
    st.stop()

# ====================== Helpers ======================
def read_xlsx(file, label):
    if not file:
        st.error(f"Thiếu file: {label}")
        st.stop()
    if not file.name.lower().endswith(".xlsx"):
        st.error(f"File {label} phải là .xlsx. Hãy lưu lại định dạng .xlsx.")
        st.stop()
    try:
        return pd.read_excel(file, engine="openpyxl")
    except Exception as e:
        st.error(f"Không đọc được file {label}: {e}")
        st.stop()

def contains_any(text, keywords):
    if pd.isna(text):
        return False
    text = str(text).upper()
    return any(k in text for k in keywords)

# ====================== UI: Upload ======================
c1, c2 = st.columns(2)
with c1:
    f_fx   = st.file_uploader("MUC49_1201.xlsx  (FX gốc)", type=["xlsx"])
    f_a    = st.file_uploader("Muc21_1201.xlsx (bảng A)", type=["xlsx"])
with c2:
    f_b    = st.file_uploader("Muc22_1201.xlsx (bảng B)", type=["xlsx"])
    f_m19  = st.file_uploader("Muc19_1201.xlsx (bảng 19)", type=["xlsx"])

run = st.button("▶️ Chạy", type="primary")

# ====================== Core processing ======================
def process_fx(df_fx, df_a, df_b, df_muc19):
    # ------- Khối 1: df_filtered (tiêu chí 1,2,3,4) -------
    df_filtered = df_fx.copy()
    df_filtered = df_filtered[(df_filtered['CRNCY_PURCHSD'] != 'GD1') & (df_filtered['CRNCY_SOLD'] != 'GD1')].copy()

    filter_dot = df_filtered['DEALER'].astype(str).str.contains('.', regex=False, na=False)
    filter_not_robot = ~df_filtered['DEALER'].astype(str).str.contains('ROBOT', case=False, regex=False, na=False)
    df_filtered = df_filtered[filter_dot & filter_not_robot].copy()

    # P/S
    df_filtered['P/S'] = np.where(df_filtered['PURCHASED_AMOUNT'].fillna(0) != 0, 'P',
                                  np.where(df_filtered['SOLD_AMOUNT'].fillna(0) != 0, 'S', ''))

    df_filtered['AMOUNT'] = np.where(df_filtered['P/S'] == 'P', df_filtered['PURCHASED_AMOUNT'], df_filtered['SOLD_AMOUNT'])
    df_filtered['Rate'] = np.where(df_filtered['P/S'] == 'P', df_filtered['PURCHASED_RATE'], df_filtered['SOLD_RATE'])
    df_filtered['Treasury Rate'] = np.where(df_filtered['P/S'] == 'P', df_filtered['TREASURY_BUY_RATE'], df_filtered['TREASURY_SELL_RATE'])
    df_filtered['Loại Ngoại tệ'] = np.where(df_filtered['P/S'] == 'P', df_filtered['CRNCY_PURCHSD'], df_filtered['CRNCY_SOLD'])

    # Info
    df_filtered['SOL'] = df_filtered['SOL_ID']
    df_filtered['Đơn vị'] = df_filtered['SOL_DESC']
    df_filtered['CIF'] = df_filtered['CIF_ID']
    df_filtered['Tên KH'] = df_filtered['CUST_NAME']
    df_filtered['DEAL_DATE'] = pd.to_datetime(df_filtered['DEAL_DATE'], errors='coerce')
    df_filtered['DUE_DATE'] = pd.to_datetime(df_filtered['DUE_DATE'], errors='coerce')
    df_filtered['TRANSACTION_NO'] = df_filtered['TRANSACTION_NO'].astype(str).str.strip()
    df_filtered['Quy đổi VND'] = df_filtered['VALUE_VND']
    df_filtered['Quy đổi USD'] = df_filtered['VALUE_USD']
    df_filtered['Mục đích'] = df_filtered['PURPOSE_OF_TRANSACTION']
    df_filtered['Kết quả Lãi/lỗ'] = df_filtered['KETQUA']
    df_filtered['Số tiền Lãi lỗ'] = df_filtered['SOTIEN_LAI_LO']

    # Maker/Checker
    df_filtered['Maker'] = df_filtered['DEALER'].apply(lambda x: str(x).strip() if pd.notnull(x) and 'ROBOT' not in str(x).upper() else '')
    df_filtered['Maker Date'] = pd.to_datetime(df_filtered['MAKER_DATE'], errors='coerce')
    df_filtered['Checker'] = df_filtered['VERIFY_ID']
    df_filtered['Verify Date'] = pd.to_datetime(df_filtered['VERIFY_DATE'], errors='coerce')

    # 9 cột đặc biệt
    df_filtered['GD bán ngoại tệ CK'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['BAN NTE CK', 'CK']) else '', axis=1)
    df_filtered['GD bán ngoại tệ mặt'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['BAN NTE MAT', 'MAT']) else '', axis=1)
    df_filtered['GD bán NT không TB chi phí'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['BO SUNG', 'SINH HOAT PHI', 'BOSUNG']) else '', axis=1)
    df_filtered['Bán NT - Trợ cấp'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['TRO CAP', 'TROCAP']) else '', axis=1)
    df_filtered['Bán NT - Du học'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['DU HOC', 'DUHOC', 'SINH HOAT PHI']) else '', axis=1)
    df_filtered['Bán NT - Du lịch'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['DU LICH', 'DULICH']) else '', axis=1)
    df_filtered['Bán NT - Công tác'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['CONG TAC', 'CONGTAC']) else '', axis=1)
    df_filtered['Bán NT - Chữa bệnh'] = df_filtered.apply(
        lambda x: 'X' if x['P/S'] == 'S' and contains_any(x['Mục đích'], ['CHUA BENH', 'CHUABENH']) else '', axis=1)

    ban_nt_loai_tru_cols = ['Bán NT - Trợ cấp', 'Bán NT - Du học', 'Bán NT - Du lịch', 'Bán NT - Công tác', 'Bán NT - Chữa bệnh']
    df_filtered['Bán NT - Khác'] = df_filtered.apply(
        lambda x: 'X' if (str(x['P/S']).strip().upper() == 'S' and all(str(x[col]).strip() == '' for col in ban_nt_loai_tru_cols)) else '',
        axis=1
    )

    df_filtered['Nhập sai mục đích'] = df_filtered.apply(
        lambda x: 'X' if (x['P/S'] == 'P' and contains_any(x['Mục đích'], ['BAN'])) or
                         (x['P/S'] == 'S' and contains_any(x['Mục đích'], ['MUA'])) else '', axis=1)

    # (22) Giao dịch lỗ >100k
    df_filtered['GD lỗ >100.000đ'] = df_filtered.apply(
        lambda x: 'X' if x['Kết quả Lãi/lỗ'] == 'LO' and abs(x['Số tiền Lãi lỗ']) >= 100_000 else '',
        axis=1
    )

    # (23) GD duyệt trễ >30p
    tre = df_filtered['Verify Date'] - df_filtered['Maker Date']
    df_filtered['GD duyệt trễ >30p'] = tre.apply(lambda x: 'X' if pd.notnull(x) and x.total_seconds() > 1800 else '')

    # Rate Request (điều kiện a,b)
    df_a_proc = df_a.copy()
    df_a_proc['FRWRD_CNTRCT_NUM'] = df_a_proc['FRWRD_CNTRCT_NUM'].astype(str).str.strip()
    df_a_proc['TREA_REF_NUM'] = pd.to_numeric(df_a_proc['TREA_REF_NUM'], errors='coerce')
    set_a = set(df_a_proc[df_a_proc['TREA_REF_NUM'].notna()]['FRWRD_CNTRCT_NUM'])

    df_b_proc = df_b.copy()
    df_b_proc['TRAN_ID'] = df_b_proc['TRAN_ID'].astype(str).str.strip()
    df_b_proc['TRAN_DATE'] = pd.to_datetime(df_b_proc['TRAN_DATE'], errors='coerce').dt.strftime('%m/%d/%Y')
    df_b_proc['TREA_REF_NUM'] = pd.to_numeric(df_b_proc['TREA_REF_NUM'], errors='coerce')
    df_b_valid = df_b_proc[df_b_proc['TREA_REF_NUM'].notna()].copy()
    df_b_valid['match_key'] = list(zip(df_b_valid['TRAN_ID'], df_b_valid['TRAN_DATE']))
    set_b = set(df_b_valid['match_key'])

    df_filtered['TRANSACTION_NO'] = df_filtered['TRANSACTION_NO'].astype(str).str.strip()
    df_filtered['MAKER_DATE_ONLY'] = pd.to_datetime(df_filtered['Maker Date'], errors='coerce').dt.strftime('%m/%d/%Y')
    df_filtered['match_key'] = list(zip(df_filtered['TRANSACTION_NO'], df_filtered['MAKER_DATE_ONLY']))

    cond_a = df_filtered['TRANSACTION_NO'].isin(set_a)
    cond_b = df_filtered['match_key'].isin(set_b)
    df_filtered['GD Rate Request'] = np.where(cond_a | cond_b, 'X', '')

    df_filtered.drop(columns=['MAKER_DATE_ONLY', 'match_key'], inplace=True, errors='ignore')

    # Ghép loại tỷ giá từ A/B
    df_filtered['Maker_Date_fmt'] = pd.to_datetime(df_filtered['Maker Date'], errors='coerce').dt.strftime('%m/%d/%Y')
    df_filtered['AMOUNT'] = pd.to_numeric(df_filtered['AMOUNT'], errors='coerce')

    rate_dict_a = df_a_proc.set_index('FRWRD_CNTRCT_NUM')['RATE_CODE'].to_dict()
    df_filtered['RATE_CODE_A'] = df_filtered['TRANSACTION_NO'].map(rate_dict_a)

    df_b_map = df_b_proc[['TRAN_ID', 'TRAN_DATE', 'TRAN_AMT', 'RATE_CODE']].copy()
    df_b_map['TRAN_AMT'] = pd.to_numeric(df_b_map['TRAN_AMT'], errors='coerce')
    df_b_map['key'] = list(zip(df_b_map['TRAN_ID'], df_b_map['TRAN_DATE']))

    df_tmp = df_filtered[['TRANSACTION_NO', 'Maker_Date_fmt', 'AMOUNT']].copy()
    df_tmp['index_main'] = df_tmp.index
    df_tmp['key'] = list(zip(df_tmp['TRANSACTION_NO'], df_tmp['Maker_Date_fmt']))

    joined = df_tmp.merge(df_b_map[['key', 'TRAN_AMT', 'RATE_CODE']], on='key', how='left')
    joined['diff'] = (joined['AMOUNT'] - joined['TRAN_AMT']).abs()
    best = joined.sort_values('diff').groupby('index_main').first().reset_index()
    df_filtered['RATE_CODE_B'] = best.set_index('index_main')['RATE_CODE']

    df_filtered['Loại tỷ giá'] = df_filtered['RATE_CODE_A'].combine_first(df_filtered['RATE_CODE_B'])
    df_filtered.drop(columns=['RATE_CODE_A', 'RATE_CODE_B', 'Maker_Date_fmt'], inplace=True, errors='ignore')

    df_filtered['GD bán NT sai loại tỷ giá'] = np.where(
        (df_filtered['P/S'].astype(str).str.upper() == 'S') &
        (df_filtered['Mục đích'].astype(str).str.upper().str.contains('BAN NTE MAT|MAT', na=False)) &
        (df_filtered['Loại tỷ giá'].astype(str).str.upper() != 'T1000'),
        'X', ''
    )

    # Sắp cột
    final_columns = [
        'SOL','Đơn vị','CIF','Tên KH','P/S','AMOUNT','Rate','Treasury Rate','Loại Ngoại tệ',
        'DEAL_DATE','DUE_DATE','TRANSACTION_NO','Quy đổi VND','Quy đổi USD','Mục đích',
        'Kết quả Lãi/lỗ','Số tiền Lãi lỗ','Maker','Maker Date','Checker','Verify Date',
        'GD bán ngoại tệ CK','GD bán ngoại tệ mặt','GD bán NT không TB chi phí',
        'Bán NT - Trợ cấp','Bán NT - Du học','Bán NT - Du lịch','Bán NT - Công tác','Bán NT - Chữa bệnh',
        'Bán NT - Khác','Nhập sai mục đích','GD lỗ >100.000đ','GD duyệt trễ >30p',
        'GD Rate Request','Loại tỷ giá','GD bán NT sai loại tỷ giá'
    ]
    df_filtered = df_filtered.reindex(columns=final_columns)

    # ------- Khối 2: df_baocao (tiêu chí 5,6) -------
    df = df_muc19.copy()
    df['SOL'] = df['SOL_ID']; df['ĐON_VI'] = df['SOL_DESC']; df['CIF'] = df['CIF_ID']; df['Tên KH'] = df['CUST_NAME']
    df['DEAL_DATE'] = df['DEAL_DATE']; df['DUE_DATE'] = df['DUE_DATE']

    df['P/S'] = np.where(df['PURCHASED_AMOUNT'].fillna(0) != 0, 'P',
                         np.where(df['SOLD_AMOUNT'].fillna(0) != 0, 'S', ''))
    df['AMOUNT'] = np.where(df['P/S'] == 'P', df['PURCHASED_AMOUNT'], np.where(df['P/S'] == 'S', df['SOLD_AMOUNT'], np.nan))
    df['RATE'] = np.where(df['P/S'] == 'P', df['PURCHASED_RATE'], np.where(df['P/S'] == 'S', df['SOLD_RATE'], np.nan))
    df['TREASURY_RATE'] = np.where(df['P/S'] == 'P', df['TREASURY_BUY_RATE'], np.where(df['P/S'] == 'S', df['TREASURY_SELL_RATE'], np.nan))
    df['Quy đổi VND'] = df['VALUE_VND']
    df['TRANSACTION_NO'] = df['TRANSACTION_NO'].astype(str).str.strip()
    df['MAKER'] = df['DEALER'].where(df['DEALER'].str.contains(r'\.') & ~df['DEALER'].str.contains("ROBOT"), np.nan)
    df['MAKER_DATE'] = pd.to_datetime(df['MAKER_DATE'], errors='coerce').dt.strftime('%m/%d/%Y %H:%M:%S')
    df['CHECKER'] = df['VERIFY_ID']
    df['VERIFY_DATE'] = pd.to_datetime(df['VERIFY_DATE'], errors='coerce').dt.strftime('%m/%d/%Y %H:%M:%S')
    df['Mục đích'] = df['PURPOSE_OF_TRANSACTION']
    df['Transaction_type'] = df['TRANSACTION_TYPE']
    df['Kết quả Lãi/lỗ'] = df['KETQUA']
    df['Số tiền Lãi lỗ'] = df['SOTIEN_LAI_LO']
    df['Loại tiền KQ'] = df['KYQUY_NT']; df['Số tiền KQ'] = df['LOAITIEN_KYQUY']

    df['GD lỗ > 100.000đ'] = np.where((df['Kết quả Lãi/lỗ'] == 'LO') & (df['Số tiền Lãi lỗ'].abs() >= 100000), 'X', '')

    cols_baocao = [
        'SOL','ĐON_VI','CIF','Tên KH','DEAL_DATE','DUE_DATE','P/S','AMOUNT','RATE','TREASURY_BUY_RATE',
        'Quy đổi VND','TRANSACTION_NO','MAKER','MAKER_DATE','CHECKER','VERIFY_DATE','Mục đích','Transaction_type',
        'Kết quả Lãi/lỗ','Số tiền Lãi lỗ','Loại tiền KQ','Số tiền KQ','GD lỗ > 100.000đ'
    ]
    df_baocao = df[cols_baocao].copy()

    # TC6: duyệt trễ > 20p
    df_baocao['MAKER_DATE'] = pd.to_datetime(df_baocao['MAKER_DATE'], errors='coerce')
    df_baocao['VERIFY_DATE'] = pd.to_datetime(df_baocao['VERIFY_DATE'], errors='coerce')
    df_baocao['TIME_DELAY'] = df_baocao['VERIFY_DATE'] - df_baocao['MAKER_DATE']
    df_baocao['GD duyệt trễ > 20p'] = np.where(df_baocao['TIME_DELAY'] > pd.Timedelta(minutes=20), 'X', '')

    # GD Rate Request (18/06/2025 logic)
    df_baocao['TRANSACTION_NO_CLEAN'] = df_baocao['TRANSACTION_NO'].astype(str).str.strip()
    df_baocao['MAKER_DATE_FMT'] = pd.to_datetime(df_baocao['MAKER_DATE'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_a_valid2 = df_a[df_a['TREA_REF_NUM'].notna()]
    cond_a2 = df_baocao['TRANSACTION_NO_CLEAN'].isin(df_a_valid2['FRWRD_CNTRCT_NUM'].astype(str).str.strip())

    df_b2 = df_b.copy()
    df_b2['TRAN_ID'] = df_b2['TRAN_ID'].astype(str).str.strip()
    df_b2['TRAN_DATE_FMT'] = pd.to_datetime(df_b2['TRAN_DATE'], errors='coerce').dt.strftime('%m/%d/%Y')
    df_b_merge = df_baocao.merge(df_b2[['TRAN_ID','TRAN_DATE_FMT','TREA_REF_NUM']],
                                 left_on=['TRANSACTION_NO_CLEAN','MAKER_DATE_FMT'],
                                 right_on=['TRAN_ID','TRAN_DATE_FMT'], how='left')
    cond_b2 = df_b_merge['TREA_REF_NUM'].notna()
    df_baocao['GD Rate Request'] = np.where(cond_a2 | cond_b2, 'X', '')
    df_baocao.drop(columns=['TRANSACTION_NO_CLEAN','MAKER_DATE_FMT'], inplace=True, errors='ignore')

    # CASH / SPOT T0
    df_baocao['GD CASH'] = df_baocao['Transaction_type'].astype(str).str.upper().apply(lambda x: 'X' if x == 'CASH' else '')
    df_baocao['DEAL_DATE'] = pd.to_datetime(df_baocao['DEAL_DATE'])
    df_baocao['DUE_DATE'] = pd.to_datetime(df_baocao['DUE_DATE'])
    df_baocao['GD SPOT T0'] = df_baocao.apply(
        lambda row: 'X' if str(row['Transaction_type']).upper() == 'SPOT' and (row['DUE_DATE'] - row['DEAL_DATE']).days == 0 else '',
        axis=1
    )

    return df_filtered, df_baocao

# ====================== Run ======================
if run:
    df_fx   = read_xlsx(f_fx,  "MUC49_1201.xlsx")
    df_a    = read_xlsx(f_a,   "Muc21_1201.xlsx")
    df_b    = read_xlsx(f_b,   "Muc22_1201.xlsx")
    df_m19  = read_xlsx(f_m19, "Muc19_1201.xlsx")

    df_filtered, df_baocao = process_fx(df_fx, df_a, df_b, df_m19)

    st.subheader("📄 Tiêu chí 1,2,3,4")
    st.dataframe(df_filtered.head(100), use_container_width=True)

    st.subheader("📄 Tiêu chí 5,6")
    st.dataframe(df_baocao.head(100), use_container_width=True)

    # Tải Excel kết quả
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df_filtered.to_excel(writer, sheet_name="Tieu chi 1,2,3,4", index=False)
        df_baocao.to_excel(writer, sheet_name="Tieu chi 5,6", index=False)
    st.download_button(
        "⬇️ Tải KQ_xuly_NT_1201_.xlsx",
        data=out.getvalue(),
        file_name="KQ_xuly_NT_1201_.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
