import streamlit as st
import gspread
import pandas as pd
from datetime import date, datetime
import time
import os

# --- 1. PRO EXECUTIVE STYLING (Blue & Orange Theme) ---
st.set_page_config(page_title="Mission 1 Cr | Ultimate Professional Terminal", layout="wide")

st.markdown("""
    <style>
    /* Professional Background */
    .stApp { background-color: #f1f3f6; color: #333333; }
    
    /* Header Section - DEEP BLUE Background, WHITE Text */
    .header-box {
        background: #003366 !important; padding: 25px; border-radius: 15px; 
        border-bottom: 5px solid #ff7043; text-align: center; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .header-box h1 { color: #ffffff !important; font-weight: 800; margin: 0; font-size: 32px; }
    .quote-text { color: #d1d5db; font-style: italic; font-size: 15px; margin-top: 10px; }

    /* VISIBILITY FIX: Labels for Inputs (BLACK) */
    label { 
        color: #000000 !important; 
        font-weight: bold !important; 
        font-size: 16px !important;
        display: block !important;
        margin-bottom: 8px !important;
    }
    
    .stTextInput input, .stNumberInput input {
        border: 2px solid #003366 !important;
        background-color: #ffffff !important;
        color: #000000 !important;
        height: 45px !important;
    }

    /* Progress Wrapper */
    .progress-container {
        background: white; padding: 35px; border-radius: 20px; 
        border: 2px solid #ff7043; margin-bottom: 25px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .bar-bg { background: #eeeeee; height: 22px; border-radius: 11px; position: relative; margin-top: 30px; border: 1px solid #ccc; }
    .bar-fill { background: #2ea043; height: 100%; border-radius: 10px; transition: 1.5s ease-in-out; }
    
    .marker {
        position: absolute; top: -50px; transform: translateX(-50%);
        background: #003366; color: #ffffff; padding: 6px 15px; border-radius: 10px;
        font-weight: 900; font-size: 14px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        white-space: nowrap; z-index: 10;
    }
    .marker::after {
        content: ''; position: absolute; bottom: -6px; left: 50%;
        transform: translateX(-50%); border-left: 6px solid transparent; 
        border-right: 6px solid transparent; border-top: 6px solid #003366;
    }

    /* Stats Cards */
    .stats-card { 
        background: #ffffff; padding: 15px; border-radius: 12px; 
        border: 1px solid #d4af37; text-align: center; height: 120px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    .stats-label { color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: bold; }
    .stats-value { color: #003366; font-size: 20px; font-weight: 800; margin-top: 10px; display: block; }

    /* ACTION CARDS (Internal UI) */
    .buy-card-ui { 
        background: #f0fdf4; padding: 30px; border-radius: 20px; 
        border: 4px solid #2ea043; margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(46, 160, 67, 0.1);
    }
    .sell-card-ui { 
        background: #fef2f2; padding: 30px; border-radius: 20px; 
        border: 4px solid #f85149; margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(248, 81, 73, 0.1);
    }
    .card-title { color: #000000; font-weight: 800; font-size: 26px; margin-bottom: 15px; border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 10px; }

    /* UNIFIED ORANGE BUTTONS */
    div.stButton > button {
        background-color: #ff7043 !important; color: white !important; border: none !important; 
        width: 100% !important; font-weight: bold !important; height: 55px !important;
        font-size: 18px !important; border-radius: 12px !important;
        box-shadow: 0 4px 10px rgba(255, 112, 67, 0.3); transition: 0.3s;
    }
    div.stButton > button:hover { transform: scale(1.02); background-color: #f4511e !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE & SESSION ---
MASTER_ID = "10SunpSW_j5ALESiX1mJweifCbgz2b9z7Q4El7k-J3Pk"

try:
    gc = gspread.service_account(filename="service_key.json")
except Exception as e:
    st.error(f"Sync Error: {e}"); st.stop()

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'sid': None, 'name': None})

# --- 3. LOGIN PAGE ---
if not st.session_state.auth:
    st.markdown('<div class="header-box"><h1>🚀 MISSION 1 CR | LOGIN</h1></div>', unsafe_allow_html=True)
    l_mob = st.text_input("📱 ENTER REGISTERED MOBILE NUMBER", placeholder="Type your registered number...")
    if st.button("Unlock Terminal"):
        with st.spinner("Accessing Database..."):
            db_ws = gc.open_by_key(MASTER_ID).worksheet("CLIENT_DB")
            df = pd.DataFrame(db_ws.get_all_records())
            user = df[df['Mobile'].astype(str).str.strip() == l_mob.strip()]
            if not user.empty:
                sid = str(user.iloc[0]['Sheet_ID']).strip()
                if sid != "PENDING":
                    st.session_state.update({'auth': True, 'sid': sid, 'name': user.iloc[0]['Client_Name']})
                    st.rerun()
                else: st.warning("Sheet Pending! Admin needs to link your ID.")
            else: st.error("User not found.")
    st.stop()

# --- 4. DYNAMIC DATA FETCH ---
try:
    sh = gc.open_by_key(st.session_state.sid)
    h_ws, s_ws, st_ws = sh.worksheet("HOLDING"), sh.worksheet("SOLD"), sh.worksheet("TRADING STEPS 3%")
    mp_ws = sh.worksheet("MONTHLY PERFORMANCE")

    h_all = h_ws.get_all_values()
    equity_bal = h_ws.acell('A6').value or "0"
    free_bal = h_ws.get('M6', value_render_option='UNFORMATTED_VALUE')[0][0]
    inv_age_str = s_ws.acell('Z2').value or "N/A"

    # Progress Calculation
    k_col = st_ws.col_values(11)[2:]
    done_count = len([x for x in k_col if x.strip() != ""])
    total_steps = 457
    progress_pct = min((done_count / total_steps) * 100, 100)

    # AI Time Estimate (Y, M, D)
    try:
        age_num = int(''.join(filter(str.isdigit, str(inv_age_str)))) or 1
        days_p = age_num * 30 if "Month" in str(inv_age_str) else (age_num * 365 if "Year" in str(inv_age_str) else age_num)
        rem_days = int((total_steps - done_count) / (max(done_count, 1) / max(days_p, 1)))
        ai_msg = f"{rem_days // 365}Y, {(rem_days % 365) // 30}M, {(rem_days % 365) % 30}D"
    except: ai_msg = "Calculating..."

    # Find Buy Step Index in TRADING STEPS (J Column)
    j_col_data = st_ws.col_values(10)
    buy_step_row = 3
    for i in range(2, len(j_col_data)):
        if not j_col_data[i].strip():
            buy_step_row = i + 1; break
    else: buy_step_row = len(j_col_data) + 1

except Exception as e:
    st.error(f"Sync Error: {e}"); st.stop()

# --- 5. DASHBOARD UI ---
st.markdown(f'''<div class="header-box"><h1>🚀 MISSION 1 CR | {st.session_state.name.upper()}</h1>
<p class="quote-text">"Patience aur Discipline se hi paisa banega."</p></div>''', unsafe_allow_html=True)

# Progress Bar
st.markdown(f"""
    <div class="progress-container">
        <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 14px; color: #666;">
            <span>STEP 1 (₹ 2,00,000)</span><span>STEP {total_steps} (₹ 1,00,00,000)</span>
        </div>
        <div class="bar-bg">
            <div class="marker" style="left: {progress_pct}%;">Step {done_count}: ₹ {equity_bal}</div>
            <div class="bar-fill" style="width: {progress_pct}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Metrics Grid (8 Cards)
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stats-card"><span class="stats-label">Free Balance (M6)</span><span class="stats-value">₹ {free_bal}</span></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stats-card"><span class="stats-label">AI Estimate Time</span><span class="stats-value" style="color:#ff7043;">{ai_msg}</span></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stats-card"><span class="stats-label">Avg Cap Used (Monthly)</span><span class="stats-value">{mp_ws.acell("C2").value}</span></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stats-card"><span class="stats-label">Monthly P% (D2)</span><span class="stats-value">{mp_ws.acell("D2").value}</span></div>', unsafe_allow_html=True)

c5, c6, c7, c8 = st.columns(4)
c5.markdown(f'<div class="stats-card"><span class="stats-label">Overall P% Max (E2)</span><span class="stats-value">{mp_ws.acell("E2").value}</span></div>', unsafe_allow_html=True)
c6.markdown(f'<div class="stats-card"><span class="stats-label">P% From Pocket (F2)</span><span class="stats-value">{mp_ws.acell("F2").value}</span></div>', unsafe_allow_html=True)
c7.markdown(f'<div class="stats-card"><span class="stats-label">Annualized % (G2)</span><span class="stats-value">{mp_ws.acell("G2").value}</span></div>', unsafe_allow_html=True)
c8.markdown(f'<div class="stats-card"><span class="stats-label">Sold Steps Done</span><span class="stats-value" style="color:green;">{len([x for x in s_ws.col_values(3)[4:] if x.strip()])} BOOKED</span></div>', unsafe_allow_html=True)

# --- 6. TERMINAL ACTIONS ---
st.write("---")
col_buy, col_sell = st.columns(2)

with col_buy:
    buy_stock = h_ws.acell('Q6').value
    st.markdown('<div class="buy-card-ui">', unsafe_allow_html=True)
    if buy_stock and buy_stock.strip() not in ["", "0", "#N/A"]:
        st.markdown(f'<div class="card-title">⚡ BUY SIGNAL: {buy_stock}</div>', unsafe_allow_html=True)
        b_price = st.number_input("Enter Execution Price", key="buy_internal", format="%.2f")
        if st.button("CONFIRM BUY TRANSACTION"):
            with st.spinner("Executing Trade..."):
                # 1. HOLDING: O6:T6 to Column A (Next Blank)
                buy_data = h_ws.get('O6:T6')[0]
                if len(buy_data) >= 5: buy_data[4] = b_price 
                h_ws.append_row(buy_data, value_input_option='USER_ENTERED')
                # 2. TRADING STEPS: J=Code, K=Price, W=Date
                st_ws.update_cell(buy_step_row, 10, buy_stock) # J
                st_ws.update_cell(buy_step_row, 11, b_price)   # K
                st_ws.update_cell(buy_step_row, 23, str(date.today())) # W
                st.balloons(); time.sleep(1.5); st.rerun()
    else:
        st.markdown('<div class="card-title">🔍 SCANNING</div>', unsafe_allow_html=True)
        st.info("Market Scanning... No Active Signal Today.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_sell:
    m_col = h_ws.col_values(13)[11:]
    sell_idx = next((i + 12 for i, v in enumerate(m_col) if v.strip()), None)
    st.markdown('<div class="sell-card-ui">', unsafe_allow_html=True)
    if sell_idx:
        current_row_data = h_all[sell_idx-1]
        s_name = current_row_data[2] # Column C
        st.markdown(f'<div class="card-title">🔻 SELL SIGNAL: {s_name}</div>', unsafe_allow_html=True)
        s_price = st.number_input("Enter Final Sell Price", key="sell_internal", format="%.2f")
        if st.button("CONFIRM SELL TRANSACTION"):
            with st.spinner("Moving to SOLD..."):
                sell_row = current_row_data[0:14] # A to N
                if len(sell_row) >= 12: sell_row[11] = s_price # L update
                s_ws.append_row(sell_row, value_input_option='USER_ENTERED')
                h_ws.delete_rows(sell_idx)
                st.success(f"{s_name} Sold!"); time.sleep(1.5); st.rerun()
    else:
        st.markdown('<div class="card-title">🔻 MONITORING</div>', unsafe_allow_html=True)
        st.info("No targets hit yet. Monitoring open positions...")
    st.markdown('</div>', unsafe_allow_html=True)