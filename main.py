import streamlit as st
import gspread
import pandas as pd
from datetime import date, datetime
import time
import json

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Mission 1 Cr | Final V14", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .header-box { 
        background: #003366 !important; padding: 20px; border-radius: 12px; 
        border-bottom: 5px solid #ff7043; text-align: center; margin-bottom: 30px; 
    }
    .header-box h1 { color: white !important; margin: 0; font-size: 26px; }
    button[kind="primaryFormSubmit"], .stButton > button {
        background-color: #ff7043 !important; color: white !important;
        border: none !important; width: 100% !important; height: 50px !important;
        font-weight: bold !important; font-size: 18px !important; border-radius: 8px !important;
    }
    .prog-container { padding: 20px; border: 2.5px solid #ff7043 !important; border-radius: 12px; margin-bottom: 30px; }
    .stats-card { background: #f8f9fa; padding: 15px; border: 1px solid #ddd; border-radius: 10px; text-align: center; margin-bottom: 15px; }
    .stats-lbl { color: #666; font-size: 11px; font-weight: bold; text-transform: uppercase; }
    .stats-val { color: #003366; font-size: 18px; font-weight: 900; margin-top: 5px; display: block; }
    .stats-sub { font-size: 11px; color: #2ea043 !important; font-weight: 800 !important; margin-top: 4px; display: block; }
    div[data-baseweb="input"] > div { border: 2px solid #333333 !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. AUTHENTICATION (AUTO-DETECT FIX)
# ==========================================
MASTER_ID = "10SunpSW_j5ALESiX1mJweifCbgz2b9z7Q4El7k-J3Pk"

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'sid': None, 'name': None})

# --- SMART LOGIN SYSTEM ---
if not st.session_state.auth:
    st.markdown('<div class="header-box"><h1>🔒 SECURE LOGIN</h1></div>', unsafe_allow_html=True)
    l_mob = st.text_input("Enter Registered Mobile Number")
    
    if st.button("UNLOCK TERMINAL"):
        try:
            # --- THE FIX IS HERE ---
            if "SERVICE_ACCOUNT_JSON" in st.secrets:
                secret_val = st.secrets["SERVICE_ACCOUNT_JSON"]
                # Agar ye pehle se Dict (TOML) hai, to seedha use karo
                if isinstance(secret_val, dict):
                    key_dict = secret_val
                # Agar ye String hai, to convert karo
                else:
                    key_dict = json.loads(secret_val)
                
                gc = gspread.service_account_from_dict(key_dict)
            else:
                gc = gspread.service_account(filename="service_key.json")
            
            # Database Connection
            db = gc.open_by_key(MASTER_ID).worksheet("CLIENT_DB")
            users = pd.DataFrame(db.get_all_records())
            u_row = users[users['Mobile'].astype(str).str.strip() == l_mob.strip()]
            
            if not u_row.empty:
                st.session_state.update({'auth': True, 'sid': str(u_row.iloc[0]['Sheet_ID']).strip(), 'name': u_row.iloc[0]['Client_Name']})
                st.rerun()
            else: st.error("❌ Number Not Found!")
            
        except Exception as e:
            st.error(f"Login Failed: {e}")
            st.info("Tip: Check if 'SERVICE_ACCOUNT_JSON' in Secrets is correct.")
    st.stop()

# ==========================================
# 3. DATA ENGINE (X-RAY SCANNER)
# ==========================================
try:
    # --- REPEAT AUTH LOGIC FOR DATA ENGINE ---
    if "SERVICE_ACCOUNT_JSON" in st.secrets:
        secret_val = st.secrets["SERVICE_ACCOUNT_JSON"]
        if isinstance(secret_val, dict): key_dict = secret_val
        else: key_dict = json.loads(secret_val)
        gc = gspread.service_account_from_dict(key_dict)
    else:
        gc = gspread.service_account(filename="service_key.json")
    
    sh = gc.open_by_key(st.session_state.sid)
    h_ws, s_ws, st_ws, mp_ws = sh.worksheet("HOLDING"), sh.worksheet("SOLD"), sh.worksheet("TRADING STEPS 3%"), sh.worksheet("MONTHLY PERFORMANCE")

    h_data = h_ws.get_all_values()
    s_data = s_ws.get_all_values()
    st_data = st_ws.get_all_values()
    mp_data = mp_ws.get_all_values()

    # --- THE X-RAY SEARCH (Finding "NSE:") ---
    auto_stock_code = ""
    auto_qty = "0"
    
    for row_idx, row in enumerate(h_data):
        if row_idx > 15: break 
        for col_idx, cell_val in enumerate(row):
            if "NSE:" in str(cell_val).upper():
                auto_stock_code = cell_val.strip()
                # Smart Quantity Finder (Look 3 cells to right, or Column S/T)
                if len(row) > 18 and row[18].strip().isdigit(): auto_qty = row[18].strip()
                elif len(row) > 19 and row[19].strip().isdigit(): auto_qty = row[19].strip()
                elif len(row) > col_idx + 3: auto_qty = row[col_idx + 3]
                break
        if auto_stock_code: break

    # Core Logic
    equity_bal = h_data[5][0] if len(h_data) > 5 else "0"
    progress_count = len([r[10] for r in st_data[2:] if len(r) > 10 and r[10].strip() != ""])
    sold_steps_count = len([r[2] for r in s_data[4:] if len(r) > 2 and r[2].strip() != ""])

    # AI Time Fix
    start_date = None
    for row in s_data[4:]:
        for cell in row[:2]:
            if cell.strip():
                try:
                    d = pd.to_datetime(cell, dayfirst=True, errors='coerce')
                    if not pd.isnull(d) and (start_date is None or d.date() < start_date): start_date = d.date()
                except: continue

    days_passed = max((date.today() - (start_date or date.today())).days, 1)
    velocity = sold_steps_count / days_passed
    if velocity > 0:
        days_needed = (457 - sold_steps_count) / velocity
        y, rem = divmod(days_needed, 365); m, d = divmod(rem, 30)
        time_display = f"{int(y)}Y {int(m)}M {int(d)}D"
        py, prem = divmod(days_passed, 365); pm, pd = divmod(prem, 30)
        speed_text = f"{sold_steps_count} steps in {int(py)}Y {int(pm)}M {int(pd)}D"
    else:
        time_display = "Start Trading"; speed_text = "0 Steps Done"

    h_target_row = next((i+1 for i, v in enumerate([r[0] for r in h_data]) if i >= 11 and not v.strip()), len(h_data)+1)
    ow_row = next((i+1 for i, r in enumerate(st_data) if i >= 2 and len(r) > 9 and r[9].strip().isdigit()), 3)

except Exception as e:
    st.error(f"Sync Error: {e}"); st.stop()

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.markdown(f'<div class="header-box"><h1>🚀 MISSION 1 CR | {st.session_state.name.upper()}</h1></div>', unsafe_allow_html=True)

st.markdown(f"""
    <div class="prog-container">
        <div style="display:flex; justify-content:space-between; font-weight:bold; color:#555; margin-bottom:10px;">
            <span>Start: ₹ 2L</span><span>Goal: ₹ 1 Cr</span>
        </div>
        <div style="background:#eee; height:24px; border-radius:12px; position:relative;">
            <div style="background:#2ea043; width:{(progress_count/457)*100}%; height:100%; border-radius:12px;"></div>
            <div style="position:absolute; top:-38px; left:{(progress_count/457)*100}%; transform:translateX(-50%); background:#003366; color:white; padding:5px 10px; border-radius:6px; font-weight:bold; font-size:12px; white-space:nowrap;">
                Done: {progress_count} | ₹ {equity_bal}
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
p_row = mp_data[1] if len(mp_data) > 1 else []
metrics = [(c1, "Steps Completed", sold_steps_count, "#2ea043"), (c2, "AI Time Left", time_display, "#003366"), (c3, "Monthly P%", p_row[3] if len(p_row)>3 else "0%", "#003366"), (c4, "Remaining Steps", (457-sold_steps_count), "#d93025"), (c5, "Pocket %", p_row[5] if len(p_row)>5 else "0%", "#003366"), (c6, "Annualized", p_row[6] if len(p_row)>6 else "0%", "#003366")]
for col, lbl, val, color in metrics:
    sub = speed_text if lbl == "AI Time Left" else ""
    col.markdown(f'<div class="stats-card"><span class="stats-lbl">{lbl}</span><br><span class="stats-val" style="color:{color}">{val}</span><span class="stats-sub">{sub}</span></div>', unsafe_allow_html=True)

# ==========================================
# 5. ACTION TERMINAL
# ==========================================
st.write("---")
is_buy_active = auto_stock_code != ""
s_idx = next((i + 12 for i, r in enumerate(h_data[11:]) if len(r) > 12 and r[12].strip()), None)

cb, cs = st.columns(2)
with cb:
    with st.container(border=True):
        st.markdown("<h3 style='color:#2ea043; text-align:center;'>⚡ BUY TASK</h3>", unsafe_allow_html=True)
        if is_buy_active:
            with st.form("buy_form"):
                st.write(f"**Stock:** {auto_stock_code}")
                try: q_val = int(float(auto_qty.replace(',','')))
                except: q_val = 0
                qty = st.number_input("Confirm Qty", value=q_val)
                prc = st.number_input("Execution Price", format="%.2f")
                if st.form_submit_button("✅ EXECUTE BUY"):
                    orig = h_ws.get('O6:T6')[0] 
                    orig[2], orig[4], orig[5] = auto_stock_code, prc, qty
                    h_ws.update(f'A{h_target_row}:F{h_target_row}', [orig], value_input_option='USER_ENTERED')
                    st_ws.update_cell(ow_row, 10, auto_stock_code); st_ws.update_cell(ow_row, 11, prc); st_ws.update_cell(ow_row, 23, str(date.today()))
                    st.balloons(); st.success("Task Completed!"); time.sleep(1); st.rerun()
        else: st.info("Nothing to buy today.")

with cs:
    with st.container(border=True):
        st.markdown("<h3 style='color:#d93025; text-align:center;'>🔻 SELL TASK</h3>", unsafe_allow_html=True)
        if s_idx:
            r_data = h_data[s_idx-1]
            with st.form("sell_form"):
                st.write(f"**Stock:** {r_data[2]} | **Qty:** {r_data[7]}")
                s_prc = st.number_input("Sell Price", format="%.2f")
                if st.form_submit_button("🚨 BOOK PROFIT"):
                    live = h_ws.row_values(s_idx)[:14]; live[11] = s_prc
                    s_ws.append_row(live, value_input_option='USER_ENTERED'); h_ws.delete_rows(s_idx)
                    st.balloons(); st.success("Profit Booked!"); time.sleep(1); st.rerun()
        else: st.info("No Active Sells.")

st.caption(f"Terminal Active | User: {st.session_state.name}")