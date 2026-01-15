import streamlit as st
import gspread
import pandas as pd
from datetime import date, datetime
import time
import os
import json

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Mission 1 Cr | Final Terminal", layout="wide")

st.markdown("""
    <style>
    /* GLOBAL RESET */
    .stApp { background-color: #ffffff; color: #000000; }
    
    /* HEADER */
    .header-box { 
        background: #003366 !important; 
        padding: 20px; 
        border-radius: 12px; 
        border-bottom: 5px solid #ff7043; 
        text-align: center; 
        margin-bottom: 30px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .header-box h1 { color: white !important; margin: 0; font-size: 26px; letter-spacing: 1px; }

    /* INPUT FIELDS */
    .stTextInput label, .stNumberInput label {
        color: #000000 !important; font-size: 14px !important; font-weight: bold !important;
    }
    div[data-baseweb="input"] > div {
        background-color: #ffffff !important;
        border: 2px solid #333333 !important; 
        color: #000000 !important;
        border-radius: 6px !important;
    }
    input[type="text"], input[type="number"] {
        color: #000000 !important; font-weight: 600 !important;
    }

    /* BUTTONS - FORCE ORANGE */
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #ff7043 !important; 
        color: white !important; 
        border: none !important; 
        width: 100% !important; 
        height: 50px !important;
        font-size: 18px !important; 
        font-weight: bold !important;
        border-radius: 8px !important;
        margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover { 
        background-color: #e64a19 !important; 
    }

    /* PROGRESS BAR - ORANGE BORDER */
    .prog-container {
        padding: 20px; 
        background: white; 
        border: 2.5px solid #ff7043 !important; 
        border-radius: 12px;
        margin-bottom: 30px;
    }
    
    /* STATS CARDS */
    .stats-card { 
        background: #f8f9fa; 
        padding: 15px; 
        border: 1px solid #ddd; 
        border-radius: 10px; 
        text-align: center; 
        margin-bottom: 15px;
    }
    .stats-lbl { color: #666; font-size: 11px; font-weight: bold; text-transform: uppercase; }
    .stats-val { color: #003366; font-size: 18px; font-weight: 900; margin-top: 5px; display: block; }
    
    /* GREEN SUBTEXT (AI TIME) */
    .stats-sub { 
        font-size: 11px; 
        color: #2ea043 !important; 
        font-weight: 700 !important; 
        margin-top: 4px; 
        display: block; 
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. AUTHENTICATION
# ==========================================
MASTER_ID = "10SunpSW_j5ALESiX1mJweifCbgz2b9z7Q4El7k-J3Pk"

try:
    if "SERVICE_ACCOUNT_JSON" in st.secrets:
        key_dict = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
        gc = gspread.service_account_from_dict(key_dict)
    else:
        gc = gspread.service_account(filename="service_key.json")
except Exception as e:
    st.error(f"Config Error: {e}"); st.stop()

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'sid': None, 'name': None})

# --- LOGIN SCREEN ---
if not st.session_state.auth:
    st.markdown('<div class="header-box"><h1>🔒 SECURE LOGIN</h1></div>', unsafe_allow_html=True)
    st.write("")
    l_mob = st.text_input("Enter Registered Mobile Number", placeholder="Ex: 9876543210")
    
    if st.button("UNLOCK TERMINAL"):
        if l_mob:
            msg = st.empty()
            msg.info("⏳ Connecting...")
            try:
                db_ws = gc.open_by_key(MASTER_ID).worksheet("CLIENT_DB")
                df_users = pd.DataFrame(db_ws.get_all_records())
                user = df_users[df_users['Mobile'].astype(str).str.strip() == l_mob.strip()]
                if not user.empty:
                    st.session_state.auth = True
                    st.session_state.sid = str(user.iloc[0]['Sheet_ID']).strip()
                    st.session_state.name = user.iloc[0]['Client_Name']
                    msg.success("✅ Access Granted!")
                    time.sleep(1)
                    st.rerun()
                else: msg.error("❌ Number Not Found!")
            except Exception as e: msg.error(f"Error: {e}")
    st.stop()

# ==========================================
# 3. DATA ENGINE (FIXED: P2 & S2 FETCH)
# ==========================================
try:
    sh = gc.open_by_key(st.session_state.sid)
    h_ws, s_ws, st_ws = sh.worksheet("HOLDING"), sh.worksheet("SOLD"), sh.worksheet("TRADING STEPS 3%")
    mp_ws = sh.worksheet("MONTHLY PERFORMANCE")

    h_data = h_ws.get_all_values()
    s_data = s_ws.get_all_values()
    st_data = st_ws.get_all_values()
    mp_data = mp_ws.get_all_values()

    # --- BUY SIGNAL (DIRECT FETCH P2 & S2) ---
    # We fetch P2 (Stock Code) and S2 (Quantity) directly as formatted values
    auto_stock_code = h_ws.acell('P2', value_render_option='FORMATTED_VALUE').value
    auto_qty_val = h_ws.acell('S2', value_render_option='FORMATTED_VALUE').value
    
    auto_stock_code = str(auto_stock_code).strip() if auto_stock_code else ""
    auto_qty = str(auto_qty_val).strip() if auto_qty_val else "0"

    # Core Stats
    equity_bal = h_data[5][0] if len(h_data) > 5 else "0"
    progress_count = len([r[10] for r in st_data[2:] if len(r) > 10 and r[10].strip() != ""])
    progress_pct = min((progress_count / 457) * 100, 100)
    sold_steps_count = len([r[2] for r in s_data[4:] if len(r) > 2 and r[2].strip() != ""])
    remaining_steps = 457 - sold_steps_count

    # AI Time (Robust Pandas Logic)
    start_date = date.today()
    try:
        raw_dates = [r[0] for r in s_data[4:] if len(r) > 0 and r[0].strip()]
        if raw_dates:
            dt_index = pd.to_datetime(raw_dates, dayfirst=True, errors='coerce').dropna()
            if not dt_index.empty:
                start_date = dt_index.min().date()
    except: pass

    days_passed = max((date.today() - start_date).days, 1)
    velocity = sold_steps_count / days_passed
    if velocity > 0:
        days_req = remaining_steps / velocity
        y, r = divmod(days_req, 365); m, d = divmod(r, 30)
        time_display = f"{int(y)}Y {int(m)}M {int(d)}D"
        py, pr = divmod(days_passed, 365); pm, pd = divmod(pr, 30)
        speed_text = f"{sold_steps_count} steps in {int(py)}Y {int(pm)}M {int(pd)}D"
    else:
        time_display = "Start Trading"; speed_text = "0 Steps Completed"

    # Saving Helpers
    col_a = [row[0] for row in h_data]
    h_target_row = next((i+1 for i, v in enumerate(col_a) if i >= 11 and not v.strip()), len(col_a)+1)
    ow_row = next((i+1 for i, r in enumerate(st_data) if i >= 2 and len(r) > 9 and r[9].strip().isdigit()), 3)

except Exception as e:
    st.error(f"Sync Error: {e}"); st.stop()

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.markdown(f'<div class="header-box"><h1>🚀 MISSION 1 CR | {st.session_state.name.upper()}</h1></div>', unsafe_allow_html=True)

# Progress Bar (Orange Border)
st.markdown(f"""
    <div class="prog-container">
        <div style="display:flex; justify-content:space-between; font-weight:bold; color:#555; margin-bottom:10px;">
            <span>Start: ₹ 2L</span><span>Goal: ₹ 1 Cr</span>
        </div>
        <div style="background:#eee; height:24px; border-radius:12px; position:relative;">
            <div style="background:#2ea043; width:{progress_pct}%; height:100%; border-radius:12px;"></div>
            <div style="position:absolute; top:-38px; left:{progress_pct}%; transform:translateX(-50%); background:#003366; color:white; padding:5px 10px; border-radius:6px; font-weight:bold; font-size:12px; white-space:nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                Done: {progress_count} | ₹ {equity_bal}
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Metrics
c1, c2, c3, c4, c5, c6 = st.columns(6)
p_row = mp_data[1] if len(mp_data) > 1 else []
metrics = [
    (c1, "Steps Completed", sold_steps_count, "#2ea043"),
    (c2, "AI Time Left", time_display, "#003366"),
    (c3, "Monthly P%", p_row[3] if len(p_row)>3 else "0%", "#003366"),
    (c4, "Remaining Steps", remaining_steps, "#d93025"),
    (c5, "Pocket %", p_row[5] if len(p_row)>5 else "0%", "#003366"),
    (c6, "Annualized", p_row[6] if len(p_row)>6 else "0%", "#003366")
]

for col, lbl, val, color in metrics:
    sub = speed_text if lbl == "AI Time Left" else ""
    col.markdown(f"""
        <div class="stats-card">
            <span class="stats-lbl">{lbl}</span><br>
            <span class="stats-val" style="color:{color}">{val}</span>
            <span class="stats-sub">{sub}</span>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 5. ACTION TERMINAL
# ==========================================
st.write("---")

is_buy_active = auto_stock_code.upper() not in ["", "0", "0.00", "#N/A", "NONE", "FALSE", "TRADING..."]
m_check = [row[12] if len(row) > 12 else "" for row in h_data[11:]] 
s_idx = next((i + 12 for i, v in enumerate(m_check) if v.strip()), None)

c_buy, c_sell = st.columns(2)

# --- BUY CARD ---
with c_buy:
    with st.container(border=True):
        st.markdown(f"<h3 style='color:#2ea043; margin-top:0; text-align:center;'>⚡ BUY TASK</h3>", unsafe_allow_html=True)
        if is_buy_active:
            with st.form("buy_form"):
                st.markdown(f"**Stock:** {auto_stock_code}")
                try: q_val = int(float(auto_qty.replace(',','')))
                except: q_val = 0
                final_qty = st.number_input("Confirm Quantity", value=q_val, step=1)
                b_price = st.number_input("Execution Price", format="%.2f")
                if st.form_submit_button("✅ EXECUTE BUY"):
                    # Use Row 6 to get original layout template O6:T6
                    orig_vals = h_ws.get('O6:T6')[0]
                    orig_vals[2], orig_vals[4], orig_vals[5] = auto_stock_code, b_price, final_qty
                    
                    h_ws.update(f'A{h_target_row}:F{h_target_row}', [orig_vals], value_input_option='USER_ENTERED')
                    st_ws.update_cell(ow_row, 10, auto_stock_code)
                    st_ws.update_cell(ow_row, 11, b_price)
                    st_ws.update_cell(ow_row, 23, str(date.today()))
                    st.balloons()
                    st.success("Buy Task Completed!"); time.sleep(1); st.rerun()
        else:
            st.info("Nothing to buy today. Come back tomorrow!")

# --- SELL CARD ---
with c_sell:
    with st.container(border=True):
        st.markdown(f"<h3 style='color:#d93025; margin-top:0; text-align:center;'>🔻 SELL TASK</h3>", unsafe_allow_html=True)
        if s_idx:
            row_data = h_data[s_idx-1]
            try: display_qty = int(float(row_data[7])) if len(row_data) > 7 else 0
            except: display_qty = 0
            curr_code = row_data[2] if len(row_data) > 2 else ""
            with st.form("sell_form"):
                st.markdown(f"**Stock:** {curr_code} | **Holding:** {display_qty}")
                s_price = st.number_input("Sell Price", format="%.2f")
                if st.form_submit_button("🚨 BOOK PROFIT"):
                    live_row = h_ws.row_values(s_idx)[:14]
                    live_row[11] = s_price
                    s_ws.append_row(live_row, value_input_option='USER_ENTERED')
                    h_ws.delete_rows(s_idx)
                    st.balloons()
                    st.success("Profit Booked!"); time.sleep(1); st.rerun()
        else:
            st.info("No Active Sells. Hold tight!")

st.caption(f"Terminal Active | User: {st.session_state.name}")