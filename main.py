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
st.set_page_config(page_title="Mission 1 Cr | Live", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f1f3f6; color: #333333; }
    .header-box { background: #003366 !important; padding: 30px; border-radius: 15px; border-bottom: 6px solid #ff7043; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .header-box h1 { color: #ffffff !important; font-weight: 800; margin: 0; font-size: 34px; letter-spacing: 1px; }
    label { color: #000000 !important; font-weight: 900 !important; font-size: 16px !important; display: block !important; margin-bottom: 8px !important; }
    .stTextInput input, .stNumberInput input { border: 2px solid #003366 !important; background-color: #ffffff !important; color: #000000 !important; height: 50px !important; border-radius: 8px !important; font-weight: 600 !important; }
    .progress-container { background: white; padding: 35px; border-radius: 20px; border: 2px solid #ff7043; margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .bar-bg { background: #eeeeee; height: 24px; border-radius: 12px; position: relative; margin-top: 35px; border: 1px solid #ccc; }
    .bar-fill { background: #2ea043; height: 100%; position: absolute; top: 0; left: 0; border-radius: 12px; transition: width 1.5s ease-in-out; }
    .marker { position: absolute; top: -55px; transform: translateX(-50%); background: #003366; color: #ffffff; padding: 8px 16px; border-radius: 10px; font-weight: 900; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); white-space: nowrap; z-index: 10; }
    .stats-card { background: #ffffff; padding: 15px; border-radius: 15px; border: 1px solid #d4af37; text-align: center; height: 140px; box-shadow: 0 3px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stats-label { color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 800; letter-spacing: 0.5px; }
    .stats-value { color: #003366; font-size: 20px; font-weight: 900; margin-top: 10px; display: block; }
    .stats-value-green { color: #2ea043 !important; font-size: 20px; font-weight: 900; margin-top: 10px; display: block; }
    .stats-value-small { color: #2ea043; font-size: 11px; font-weight: 700; display: block; margin-top: 5px; }
    .buy-card-ui { background: #f0fdf4; padding: 35px; border-radius: 25px; border: 4px solid #2ea043; margin-bottom: 25px; }
    .sell-card-ui { background: #fef2f2; padding: 35px; border-radius: 25px; border: 4px solid #f85149; margin-bottom: 25px; }
    div.stButton > button { background-color: #ff7043 !important; color: white !important; border: none !important; width: 100% !important; font-weight: 900 !important; height: 60px !important; font-size: 20px !important; border-radius: 12px !important; box-shadow: 0 4px 15px rgba(255, 112, 67, 0.4); }
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
    st.error(f"Auth Error: {e}"); st.stop()

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'sid': None, 'name': None, 'show_welcome': False})

if not st.session_state.auth:
    st.markdown('<div class="header-box"><h1>🚀 MISSION 1 CR | SECURE LOGIN</h1></div>', unsafe_allow_html=True)
    l_mob = st.text_input("ENTER REGISTERED MOBILE NUMBER")
    if st.button("UNLOCK TERMINAL"):
        with st.spinner("Checking..."):
            try:
                db_ws = gc.open_by_key(MASTER_ID).worksheet("CLIENT_DB")
                df_users = pd.DataFrame(db_ws.get_all_records())
                user = df_users[df_users['Mobile'].astype(str).str.strip() == l_mob.strip()]
                if not user.empty:
                    st.session_state.auth = True
                    st.session_state.sid = str(user.iloc[0]['Sheet_ID']).strip()
                    st.session_state.name = user.iloc[0]['Client_Name']
                    st.session_state.show_welcome = True
                    st.rerun()
                else: st.error("❌ Access Denied.")
            except Exception as e: st.error(f"Login Error: {e}")
    st.stop()

# ==========================================
# 3. DATA ENGINE (SMART DATE FIX)
# ==========================================
try:
    sh = gc.open_by_key(st.session_state.sid)
    h_ws, s_ws, st_ws = sh.worksheet("HOLDING"), sh.worksheet("SOLD"), sh.worksheet("TRADING STEPS 3%")
    mp_ws = sh.worksheet("MONTHLY PERFORMANCE")

    h_data = h_ws.get_all_values()
    s_data = s_ws.get_all_values()
    st_data = st_ws.get_all_values()
    mp_data = mp_ws.get_all_values()

    equity_bal = h_data[5][0] if len(h_data) > 5 else "0"
    auto_stock_code = h_data[5][16] if len(h_data) > 5 else "" 
    auto_qty = h_data[5][17] if len(h_data) > 5 else "0"
    
    # 1. Progress Logic (K3+)
    k_vals = [r[10] if len(r) > 10 else "" for r in st_data[2:]]
    progress_count = len([x for x in k_vals if x.strip() != ""])
    progress_pct = min((progress_count / 457) * 100, 100)
    
    # 2. Sold Steps (Row 5+)
    c_vals_sold = [r[2] if len(r) > 2 else "" for r in s_data[4:]]
    sold_steps_count = len([x for x in c_vals_sold if x.strip() != ""])

    # --- 3. FIX: PANDAS INTELLIGENT DATE PARSER ---
    TARGET_STEPS = 457
    remaining_steps = TARGET_STEPS - sold_steps_count
    
    start_date = date.today() # Default
    
    # Extract Potential Dates from Sold Sheet (Col A, B)
    # Skipping Header rows (0-3), data starts row 4 (index 4)
    raw_date_strings = []
    if len(s_data) > 4:
        for row in s_data[4:]:
            # Try Col A (Buy Date) and Col B (Sell Date)
            if len(row) > 0 and row[0].strip(): raw_date_strings.append(row[0])
            elif len(row) > 1 and row[1].strip(): raw_date_strings.append(row[1])

    if raw_date_strings:
        try:
            # Pandas is smart. It handles '15-Jan-25', '2025-01-15', '15/01/2025' all together.
            dt_series = pd.to_datetime(raw_date_strings, dayfirst=True, errors='coerce')
            valid_dates = dt_series.dropna()
            
            if not valid_dates.empty:
                start_date = valid_dates.min().date()
        except Exception as e:
            # Fallback if pandas fails
            start_date = date.today()

    # Time Calculation Function
    def days_to_ymd(total_days):
        y = int(total_days // 365)
        rem = total_days % 365
        m = int(rem // 30)
        d = int(rem % 30)
        return f"{y}Y {m}M {d}D"

    # Calculate Logic
    if sold_steps_count > 0:
        days_passed = (date.today() - start_date).days
        if days_passed < 1: days_passed = 1 
        
        velocity = sold_steps_count / days_passed 
        
        if velocity > 0:
            days_needed = remaining_steps / velocity
            time_display = days_to_ymd(days_needed)
            
            # Subtext formatted to Y M D
            passed_display = days_to_ymd(days_passed)
            speed_subtext = f"{sold_steps_count} steps in {passed_display}"
        else:
            time_display = "Start Trading"
            speed_subtext = "Velocity 0"
    else:
        time_display = "Start Trading"
        speed_subtext = "0 Steps Done"

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

if st.session_state.show_welcome:
    st.success(f"🎉 Welcome {st.session_state.name}!"); st.balloons(); st.session_state.show_welcome = False

st.markdown(f"""
    <div class="progress-container">
        <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 14px; color: #64748b; margin-bottom: 5px;">
            <span>Start: ₹ 2L</span>
            <span>Goal: ₹ 1 Cr</span>
        </div>
        <div class="bar-bg">
            <div class="marker" style="left: {progress_pct}%;">Completed: {progress_count} Steps | ₹ {equity_bal}</div>
            <div class="bar-fill" style="width: {progress_pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
try:
    p_row = mp_data[1] if len(mp_data) > 1 else []
    
    c1.markdown(f'<div class="stats-card"><span class="stats-label">Steps Completed</span><span class="stats-value-green">{sold_steps_count}</span></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stats-card"><span class="stats-label">AI Time to Goal</span><span class="stats-value">{time_display}</span><span class="stats-value-small">{speed_subtext}</span></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stats-card"><span class="stats-label">Monthly P%</span><span class="stats-value">{p_row[3] if len(p_row)>3 else "0%"}</span></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stats-card"><span class="stats-label">Remaining Steps</span><span class="stats-value">{remaining_steps}</span></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="stats-card"><span class="stats-label">From Pocket %</span><span class="stats-value">{p_row[5] if len(p_row)>5 else "0%"}</span></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="stats-card"><span class="stats-label">Annualized %</span><span class="stats-value">{p_row[6] if len(p_row)>6 else "0%"}</span></div>', unsafe_allow_html=True)
except: pass

# ==========================================
# 5. ACTION TERMINAL
# ==========================================
st.write("---")
c_buy, c_sell = st.columns(2)

with c_buy:
    st.markdown('<div class="buy-card-ui">', unsafe_allow_html=True)
    if auto_stock_code and auto_stock_code.strip() not in ["", "0", "#N/A"]:
        st.markdown(f"<h2>⚡ BUY SIGNAL</h2>", unsafe_allow_html=True)
        with st.form("buy_form"):
            final_code = st.text_input("NSE Code", value=auto_stock_code)
            try: q_val = int(float(auto_qty))
            except: q_val = 0
            final_qty = st.number_input("Quantity (To Col F)", value=q_val, step=1)
            b_price = st.number_input("Execution Price", format="%.2f")
            submitted = st.form_submit_button("CONFIRM BUY & DEPLOY")
            if submitted:
                with st.spinner("Processing..."):
                    raw_vals = h_ws.get('O6:T6')[0]
                    raw_vals[2] = final_code 
                    raw_vals[4] = b_price     
                    raw_vals[5] = final_qty   
                    h_ws.update(f'A{h_target_row}:F{h_target_row}', [raw_vals], value_input_option='USER_ENTERED')
                    st_ws.update_cell(ow_row, 10, final_code)
                    st_ws.update_cell(ow_row, 11, b_price)
                    st_ws.update_cell(ow_row, 23, str(date.today()))
                    st.balloons(); st.success("Buy Executed!"); time.sleep(2); st.rerun()
    else:
        st.info("System Scanning for New Signals...")
    st.markdown('</div>', unsafe_allow_html=True)

with c_sell:
    m_check = [row[12] if len(row) > 12 else "" for row in h_data[11:]] 
    s_idx = next((i + 12 for i, v in enumerate(m_check) if v.strip()), None)
    st.markdown('<div class="sell-card-ui">', unsafe_allow_html=True)
    if s_idx:
        row_data = h_data[s_idx-1]
        st.markdown(f"<h2>🔻 SELL ACHIEVED</h2>", unsafe_allow_html=True)
        try: display_qty = int(float(row_data[7])) if len(row_data) > 7 else 0
        except: display_qty = 0
        curr_code = row_data[2] if len(row_data) > 2 else ""
        with st.form("sell_form"):
            st.markdown(f"**NSE Code:** {curr_code}")
            st.markdown(f"**Quantity (View Only):** {display_qty}")
            s_price = st.number_input("Final Sell Price", format="%.2f")
            s_submitted = st.form_submit_button("CONFIRM SELL & BOOK")
            if s_submitted:
                with st.spinner("Moving to Sold Sheet..."):
                    live_row = h_ws.row_values(s_idx)[:14]
                    live_row[11] = s_price
                    s_ws.append_row(live_row, value_input_option='USER_ENTERED')
                    h_ws.delete_rows(s_idx)
                    st.balloons(); st.success(f"Sold! {curr_code} Moved."); time.sleep(2); st.rerun()
    else:
        st.info("Monitoring Open Positions...")
    st.markdown('</div>', unsafe_allow_html=True)

st.caption(f"Terminal Active | User: {st.session_state.name}")