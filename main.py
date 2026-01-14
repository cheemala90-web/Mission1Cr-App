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
st.set_page_config(page_title="Mission 1 Cr | Live Terminal", layout="wide")

st.markdown("""
    <style>
    /* GLOBAL THEME */
    .stApp { background-color: #ffffff; color: #000000; }
    
    /* HEADER */
    .header-box { 
        background: #003366 !important; 
        padding: 20px; 
        border-radius: 10px; 
        border-bottom: 5px solid #ff7043; 
        text-align: center; 
        margin-bottom: 20px; 
    }
    .header-box h1 { color: white !important; margin: 0; font-size: 28px; }

    /* INPUT FIELDS (Black Border & Text) */
    .stTextInput label, .stNumberInput label {
        color: #000000 !important; font-size: 16px !important; font-weight: bold !important;
    }
    div[data-baseweb="input"] > div {
        background-color: #ffffff !important;
        border: 2px solid #333333 !important; 
        color: #000000 !important;
        border-radius: 8px !important;
    }
    input[type="text"], input[type="number"] {
        color: #000000 !important; font-weight: 600 !important;
    }

    /* BUTTONS */
    div.stButton > button {
        background-color: #003366 !important; 
        color: white !important; 
        border: none !important; 
        width: 100% !important; 
        height: 55px !important;
        font-size: 18px !important; 
        font-weight: bold !important;
        border-radius: 8px !important;
    }
    div.stButton > button:hover { background-color: #ff7043 !important; }

    /* CARD STYLES (Always Visible) */
    .buy-box {
        border: 4px solid #2ea043; /* Green */
        padding: 20px;
        border-radius: 15px;
        background-color: #f0fdf4;
        margin-bottom: 20px;
        min-height: 280px; /* Fixed Height */
        display: flex; flex-direction: column; justify-content: center;
    }
    .sell-box {
        border: 4px solid #d93025; /* Red */
        padding: 20px;
        border-radius: 15px;
        background-color: #fef2f2;
        margin-bottom: 20px;
        min-height: 280px; /* Fixed Height */
        display: flex; flex-direction: column; justify-content: center;
    }

    /* METRICS */
    .stats-card { 
        background: #f8f9fa; padding: 15px; border: 1px solid #ccc; 
        border-radius: 10px; text-align: center; margin-bottom: 10px;
    }
    .stats-val { color: #003366; font-size: 18px; font-weight: bold; display: block; }
    .stats-val-green { color: #2ea043; font-size: 18px; font-weight: bold; display: block; }
    .stats-lbl { color: #555; font-size: 12px; font-weight: bold; text-transform: uppercase; }
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
            msg.info("⏳ Verifying Access...")
            try:
                db_ws = gc.open_by_key(MASTER_ID).worksheet("CLIENT_DB")
                df_users = pd.DataFrame(db_ws.get_all_records())
                user = df_users[df_users['Mobile'].astype(str).str.strip() == l_mob.strip()]
                if not user.empty:
                    st.session_state.auth = True
                    st.session_state.sid = str(user.iloc[0]['Sheet_ID']).strip()
                    st.session_state.name = user.iloc[0]['Client_Name']
                    msg.success("✅ Logged In!")
                    time.sleep(1)
                    st.rerun()
                else: msg.error("❌ Number Not Found!")
            except Exception as e: msg.error(f"Error: {e}")
    st.stop()

# ==========================================
# 3. DATA ENGINE
# ==========================================
try:
    sh = gc.open_by_key(st.session_state.sid)
    h_ws, s_ws, st_ws = sh.worksheet("HOLDING"), sh.worksheet("SOLD"), sh.worksheet("TRADING STEPS 3%")
    mp_ws = sh.worksheet("MONTHLY PERFORMANCE")

    h_data = h_ws.get_all_values()
    s_data = s_ws.get_all_values()
    st_data = st_ws.get_all_values()
    mp_data = mp_ws.get_all_values()

    # Core Data
    equity_bal = h_data[5][0] if len(h_data) > 5 else "0"
    auto_stock_code = h_data[5][16] if len(h_data) > 5 else "" 
    auto_qty = h_data[5][17] if len(h_data) > 5 else "0"
    
    # Progress Logic
    k_vals = [r[10] if len(r) > 10 else "" for r in st_data[2:]]
    progress_count = len([x for x in k_vals if x.strip() != ""])
    progress_pct = min((progress_count / 457) * 100, 100)
    
    # Sold Steps
    c_vals_sold = [r[2] if len(r) > 2 else "" for r in s_data[4:]]
    sold_steps_count = len([x for x in c_vals_sold if x.strip() != ""])

    # AI Logic (Date Fix)
    TARGET_STEPS = 457
    remaining_steps = TARGET_STEPS - sold_steps_count
    
    def strict_date_parse(d_str):
        d_str = str(d_str).strip()
        if not d_str: return None
        formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%b-%Y', '%d %b %Y']
        for fmt in formats:
            try: return datetime.strptime(d_str, fmt).date()
            except: continue
        return None

    found_dates = []
    if len(s_data) > 4:
        for row in s_data[4:]:
            if len(row) > 0:
                d = strict_date_parse(row[0])
                if d: found_dates.append(d)
            if len(row) > 1:
                d = strict_date_parse(row[1])
                if d: found_dates.append(d)
    
    start_date = min(found_dates) if found_dates else None
    
    if sold_steps_count > 0 and start_date:
        days_passed = (date.today() - start_date).days
        if days_passed < 1: days_passed = 1
        vel = sold_steps_count / days_passed
        
        # Sanity Check for 0Y issue
        if vel > 20 and days_passed == 1:
            time_display = "Check Dates"
            speed_text = "Date Error"
        else:
            days_req = remaining_steps / vel if vel > 0 else 0
            y, rem = divmod(days_req, 365)
            m, d = divmod(rem, 30)
            
            py, prem = divmod(days_passed, 365)
            pm, pd = divmod(prem, 30)
            
            time_display = f"{int(y)}Y {int(m)}M {int(d)}D"
            passed_display = f"{int(py)}Y {int(pm)}M {int(pd)}D"
            speed_text = f"{sold_steps_count} steps in {passed_display}"
    else:
        time_display = "Start Trading"
        speed_text = "0 Steps Done"

    col_a = [row[0] for row in h_data]
    h_target_row = 12
    for i in range(11, len(col_a)):
        if not col_a[i].strip():
            h_target_row = i + 1
            break
    else: h_target_row = len(col_a) + 1
    if h_target_row < 12: h_target_row = 12

    ow_row = 3
    j_col = [r[9] if len(r) > 9 else "" for r in st_data]
    for i, val in enumerate(j_col):
        if i >= 2 and val.strip().isdigit():
            ow_row = i + 1
            break

except Exception as e:
    st.error(f"Sync Error: {e}"); st.stop()

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.markdown(f'<div class="header-box"><h1>🚀 MISSION 1 CR | {st.session_state.name.upper()}</h1></div>', unsafe_allow_html=True)

# Progress
st.markdown(f"""
    <div class="progress-container">
        <div style="display:flex; justify-content:space-between; font-weight:bold; color:#555;">
            <span>Start: ₹ 2L</span><span>Goal: ₹ 1 Cr</span>
        </div>
        <div style="background:#eee; height:24px; border-radius:12px; margin-top:10px; position:relative;">
            <div style="background:#2ea043; width:{progress_pct}%; height:100%; border-radius:12px;"></div>
            <div style="position:absolute; top:-35px; left:{progress_pct}%; transform:translateX(-50%); background:#003366; color:white; padding:5px 10px; border-radius:5px; font-weight:bold; font-size:12px; white-space:nowrap;">
                Done: {progress_count} | ₹ {equity_bal}
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Metrics
c1, c2, c3, c4, c5, c6 = st.columns(6)
p_row = mp_data[1] if len(mp_data) > 1 else []
metrics = [
    (c1, "Steps Done", sold_steps_count, "#2ea043"),
    (c2, "AI Time Left", time_display, "#003366"),
    (c3, "Monthly P%", p_row[3] if len(p_row)>3 else "0%", "#003366"),
    (c4, "Steps Left", remaining_steps, "#d93025"),
    (c5, "Pocket %", p_row[5] if len(p_row)>5 else "0%", "#003366"),
    (c6, "Annualized", p_row[6] if len(p_row)>6 else "0%", "#003366")
]
for col, lbl, val, color in metrics:
    sub = speed_text if lbl == "AI Time Left" else ""
    col.markdown(f"""
        <div class="stats-card">
            <span class="stats-lbl">{lbl}</span><br>
            <span class="stats-val" style="color:{color}">{val}</span>
            <span style="font-size:10px; color:#666;">{sub}</span>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 5. ACTION TERMINAL (CARDS ALWAYS VISIBLE)
# ==========================================
st.write("---")

is_buy_active = auto_stock_code and auto_stock_code.strip() not in ["", "0", "#N/A"]
m_check = [row[12] if len(row) > 12 else "" for row in h_data[11:]] 
s_idx = next((i + 12 for i, v in enumerate(m_check) if v.strip()), None)
is_sell_active = s_idx is not None

c_buy, c_sell = st.columns(2)

# --- BUY CARD ---
with c_buy:
    st.markdown('<div class="buy-box">', unsafe_allow_html=True) # Always Green Box
    st.markdown(f"<h3 style='color:#2ea043; margin:0; text-align:center;'>⚡ BUY SIGNAL</h3>", unsafe_allow_html=True)
    st.write("")
    
    if is_buy_active:
        with st.form("buy_form"):
            st.markdown(f"**Code:** {auto_stock_code}")
            try: q_val = int(float(auto_qty))
            except: q_val = 0
            final_qty = st.number_input("Confirm Quantity", value=q_val, step=1)
            b_price = st.number_input("Execution Price", format="%.2f")
            
            if st.form_submit_button("✅ EXECUTE BUY"):
                with st.spinner("Saving..."):
                    raw_vals = h_ws.get('O6:T6')[0]
                    raw_vals[2] = auto_stock_code 
                    raw_vals[4] = b_price     
                    raw_vals[5] = final_qty   
                    h_ws.update(f'A{h_target_row}:F{h_target_row}', [raw_vals], value_input_option='USER_ENTERED')
                    st_ws.update_cell(ow_row, 10, auto_stock_code)
                    st_ws.update_cell(ow_row, 11, b_price)
                    st_ws.update_cell(ow_row, 23, str(date.today()))
                    st.success("Buy Saved!"); time.sleep(1); st.rerun()
    else:
        st.markdown("""
            <div style='text-align:center; padding:20px;'>
                <h4 style='color:#555;'>✅ Nothing to buy today.</h4>
                <p style='color:#777;'>Come back tomorrow!</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- SELL CARD ---
with c_sell:
    st.markdown('<div class="sell-box">', unsafe_allow_html=True) # Always Red Box
    st.markdown(f"<h3 style='color:#d93025; margin:0; text-align:center;'>🔻 SELL SIGNAL</h3>", unsafe_allow_html=True)
    st.write("")
    
    if is_sell_active:
        row_data = h_data[s_idx-1]
        try: display_qty = int(float(row_data[7])) if len(row_data) > 7 else 0
        except: display_qty = 0
        curr_code = row_data[2] if len(row_data) > 2 else ""

        with st.form("sell_form"):
            st.markdown(f"**Code:** {curr_code}")
            st.markdown(f"**Holding Qty:** {display_qty}")
            s_price = st.number_input("Sell Price", format="%.2f")
            
            if st.form_submit_button("🚨 BOOK PROFIT"):
                with st.spinner("Booking..."):
                    live_row = h_ws.row_values(s_idx)[:14]
                    live_row[11] = s_price
                    s_ws.append_row(live_row, value_input_option='USER_ENTERED')
                    h_ws.delete_rows(s_idx)
                    st.success("Profit Booked!"); time.sleep(1); st.rerun()
    else:
        st.markdown("""
            <div style='text-align:center; padding:20px;'>
                <h4 style='color:#555;'>🛡️ No Sells Active.</h4>
                <p style='color:#777;'>Hold your positions tight!</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption(f"Terminal Active | User: {st.session_state.name}")