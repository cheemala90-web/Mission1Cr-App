import streamlit as st
import gspread
import pandas as pd
from datetime import date, datetime
import time
import json

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Mission 1 Cr | Live V31", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .header-box { background: #003366 !important; padding: 20px; border-radius: 12px; border-bottom: 5px solid #ff7043; text-align: center; margin-bottom: 30px; }
    .header-box h1 { color: white !important; margin: 0; font-size: 26px; }
    button[kind="primaryFormSubmit"], .stButton > button { background-color: #ff7043 !important; color: white !important; border: none !important; width: 100% !important; height: 50px !important; font-weight: bold !important; font-size: 18px !important; border-radius: 8px !important; }
    .prog-container { padding: 20px; border: 2.5px solid #ff7043 !important; border-radius: 12px; margin-bottom: 30px; }
    .stats-card { background: #f8f9fa; padding: 15px; border: 1px solid #ddd; border-radius: 10px; text-align: center; margin-bottom: 15px; }
    .stats-lbl { color: #666; font-size: 11px; font-weight: bold; text-transform: uppercase; }
    .stats-val { color: #003366; font-size: 18px; font-weight: 900; margin-top: 5px; display: block; }
    .stats-sub { font-size: 11px; color: #2ea043 !important; font-weight: 800 !important; margin-top: 4px; display: block; }
    div[data-baseweb="input"] > div { border: 2px solid #333333 !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. AUTHENTICATION
# ==========================================
MASTER_ID = "10SunpSW_j5ALESiX1mJweifCbgz2b9z7Q4El7k-J3Pk"

try:
    if "SERVICE_ACCOUNT_JSON" in st.secrets:
        raw_secret = st.secrets["SERVICE_ACCOUNT_JSON"]
        if isinstance(raw_secret, dict): key_dict = dict(raw_secret)
        elif isinstance(raw_secret, str): 
            try: key_dict = json.loads(raw_secret)
            except: st.error("❌ Secrets Error: Invalid Format."); st.stop()
        else: key_dict = dict(raw_secret)

        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n").strip('"').strip("'")
            
        gc = gspread.service_account_from_dict(key_dict)
    else:
        gc = gspread.service_account(filename="service_key.json")
except Exception as e:
    st.error(f"Login Failed: {e}"); st.stop()

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'sid': None, 'name': None})

# --- LOGIN SCREEN ---
if not st.session_state.auth:
    st.markdown('<div class="header-box"><h1>🔒 SECURE LOGIN</h1></div>', unsafe_allow_html=True)
    l_mob = st.text_input("Enter Registered Mobile Number")
    
    if st.button("UNLOCK TERMINAL"):
        if l_mob:
            msg = st.empty(); msg.info("⏳ Connecting...")
            try:
                db_ws = gc.open_by_key(MASTER_ID).worksheet("CLIENT_DB")
                df_users = pd.DataFrame(db_ws.get_all_records())
                user = df_users[df_users['Mobile'].astype(str).str.strip() == l_mob.strip()]
                if not user.empty:
                    st.session_state.auth = True
                    st.session_state.sid = str(user.iloc[0]['Sheet_ID']).strip()
                    st.session_state.name = user.iloc[0]['Client_Name']
                    msg.success("✅ Access Granted!"); time.sleep(1); st.rerun()
                else: msg.error("❌ Number Not Found!")
            except Exception as e: msg.error(f"Error: {e}")
    st.stop()

# ==========================================
# 3. DATA ENGINE (V31: SMART RANGE Q2 + Q5-Q8)
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
    
    # --- LOGIC START ---
    auto_stock_code = ""
    auto_qty = "0"
    auto_price = "0.00"
    debug_info = [] # For troubleshooting
    found_signal = False
    
    # --- 1. PRIORITY: CHECK Q2 (Row 2 / Index 1) ---
    if len(h_data) > 1:
        row_2 = h_data[1]
        if len(row_2) > 16:
            val_q2 = str(row_2[16]).strip()
            debug_info.append(f"Q2: {val_q2}")
            if val_q2 and ("NSE:" in val_q2.upper() or "BSE:" in val_q2.upper()):
                auto_stock_code = val_q2
                
                # S2 (Price)
                if len(row_2) > 18:
                    val_s2 = str(row_2[18]).strip()
                    if val_s2.replace('.','').replace(',','').isdigit(): auto_price = val_s2
                # T2 (Qty)
                if len(row_2) > 19:
                    val_t2 = str(row_2[19]).strip()
                    if val_t2.replace('.','').isdigit(): auto_qty = val_t2
                
                found_signal = True 

    # --- 2. SECONDARY: CHECK RANGE Q5 to Q8 (Rows 5, 6, 7, 8) ---
    # Hum Row 12 tak nahi jayenge, sirf Row 8 tak limit rahenge.
    if not found_signal and len(h_data) > 4:
        # Scan indices 4, 5, 6, 7 (Rows 5, 6, 7, 8)
        search_rows = h_data[4:8] 
        
        for i, row in enumerate(search_rows):
            actual_row_num = i + 5
            if len(row) > 16:
                val_q = str(row[16]).strip()
                debug_info.append(f"Q{actual_row_num}: {val_q}")
                
                if val_q and ("NSE:" in val_q.upper() or "BSE:" in val_q.upper()):
                    auto_stock_code = val_q
                    
                    # S (Price)
                    if len(row) > 18:
                        val_s = str(row[18]).strip()
                        if val_s.replace('.','').replace(',','').isdigit(): auto_price = val_s
                    # T (Qty)
                    if len(row) > 19:
                        val_t = str(row[19]).strip()
                        if val_t.replace('.','').isdigit(): auto_qty = val_t
                    
                    break # Stop as soon as we find match in Q5, Q6, Q7, or Q8

    # --- DYNAMIC TOTAL STEPS ---
    total_steps_list = [r[0] for r in st_data[2:] if len(r) > 0 and r[0].strip() != ""]
    TOTAL_STEPS = len(total_steps_list)
    if TOTAL_STEPS < 10: TOTAL_STEPS = 457 

    # Progress Calculation
    k_vals = [r[10] if len(r) > 10 else "" for r in st_data[2:]]
    progress_count = len([x for x in k_vals if x.strip() != ""])
    progress_pct = min((progress_count / TOTAL_STEPS) * 100, 100)
    
    c_vals_sold = [r[2] if len(r) > 2 else "" for r in s_data[4:]]
    sold_steps_count = len([x for x in c_vals_sold if x.strip() != ""])

    # AI Logic
    remaining_steps = TOTAL_STEPS - sold_steps_count
    start_date = date.today(); raw_dates = []
    if len(s_data) > 4:
        for row in s_data[4:]:
            if len(row) > 0 and row[0].strip(): raw_dates.append(row[0])
            if len(row) > 1 and row[1].strip(): raw_dates.append(row[1])
    if raw_dates:
        try:
            dt_index = pd.to_datetime(raw_dates, dayfirst=True, errors='coerce')
            valid_dates = dt_index.dropna()
            if not valid_dates.empty: start_date = valid_dates.min().date()
        except: pass

    if sold_steps_count > 0:
        days_passed = max((date.today() - start_date).days, 1)
        velocity = sold_steps_count / days_passed
        days_req = remaining_steps / velocity if velocity > 0 else 0
        y, rem = divmod(days_req, 365); m, d = divmod(rem, 30)
        time_display = f"{int(y)}Y {int(m)}M {int(d)}D"
        py, prem = divmod(days_passed, 365); pm, pd = divmod(prem, 30)
        speed_text = f"{sold_steps_count} steps in {int(py)}Y {int(pm)}M {int(pd)}D"
    else: time_display = "Start Trading"; speed_text = "0 Steps Completed"

    col_a = [row[0] for row in h_data]
    h_target_row = next((i+1 for i, v in enumerate(col_a) if i >= 11 and not v.strip()), len(col_a)+1)
    if h_target_row < 12: h_target_row = 12
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
            <div style="background:#2ea043; width:{progress_pct}%; height:100%; border-radius:12px;"></div>
            <div style="position:absolute; top:-38px; left:{progress_pct}%; transform:translateX(-50%); background:#003366; color:white; padding:5px 10px; border-radius:6px; font-weight:bold; font-size:12px; white-space:nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                Done: {progress_count} / {TOTAL_STEPS} | ₹ {equity_bal}
            </div>
        </div>
        <div style="text-align:center; margin-top:5px; font-size:12px; color:#666;">
            Total Roadmap Length: <b>{TOTAL_STEPS} Steps</b>
        </div>
    </div>
""", unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6 = st.columns(6)
p_row = mp_data[1] if len(mp_data) > 1 else []
metrics = [(c1, "Steps Completed", f"{sold_steps_count} / {TOTAL_STEPS}", "green"), (c2, "AI Time Left", time_display, "blue"), (c3, "Monthly P%", p_row[3] if len(p_row)>3 else "0%", "blue"), (c4, "Remaining Steps", remaining_steps, "red"), (c5, "Pocket %", p_row[5] if len(p_row)>5 else "0%", "blue"), (c6, "Annualized", p_row[6] if len(p_row)>6 else "0%", "blue")]

for col, lbl, val, color_type in metrics:
    color = "#2ea043" if color_type == "green" else ("#d93025" if color_type == "red" else "#003366")
    sub = speed_text if lbl == "AI Time Left" else ""
    col.markdown(f'<div class="stats-card"><span class="stats-lbl">{lbl}</span><br><span class="stats-val" style="color:{color}">{val}</span><span class="stats-sub">{sub}</span></div>', unsafe_allow_html=True)

# ==========================================
# 5. ACTION TERMINAL
# ==========================================
st.write("---")
is_buy_active = auto_stock_code and auto_stock_code.strip() not in ["", "0", "#N/A"]
m_check = [row[12] if len(row) > 12 else "" for row in h_data[11:]] 
s_idx = next((i + 12 for i, v in enumerate(m_check) if v.strip()), None)
is_sell_active = s_idx is not None

c_buy, c_sell = st.columns(2)

with c_buy:
    with st.container(border=True):
        st.markdown(f"<h3 style='color:#2ea043; margin-top:0; text-align:center;'>⚡ BUY TASK</h3>", unsafe_allow_html=True)
        if is_buy_active:
            with st.form("buy_form"):
                confirmed_stock_code = st.text_input("Stock Code (Editable)", value=auto_stock_code)
                try: q_val = int(float(auto_qty.replace(',','')))
                except: q_val = 0
                final_qty = st.number_input("Confirm Qty", value=q_val, step=1)
                
                try: p_val = float(auto_price.replace(',',''))
                except: p_val = 0.0
                b_price = st.number_input("Exec Price", value=p_val, format="%.2f")
                
                if st.form_submit_button("✅ EXECUTE BUY"):
                    with st.spinner("Saving..."):
                        raw_vals = h_ws.get('O6:T6')[0]
                        raw_vals[2] = confirmed_stock_code
                        raw_vals[4] = b_price
                        raw_vals[5] = final_qty
                        h_ws.update(f'A{h_target_row}:F{h_target_row}', [raw_vals], value_input_option='USER_ENTERED')
                        st_ws.update_cell(ow_row, 10, confirmed_stock_code)
                        st_ws.update_cell(ow_row, 11, b_price)
                        st_ws.update_cell(ow_row, 23, str(date.today()))
                        st.balloons(); st.success(f"Buy Saved for {confirmed_stock_code}!"); time.sleep(1); st.rerun()
        else: 
            st.info("Nothing to buy today. Come back tomorrow!")
            # DEBUGGER: Only visible if Nothing Found
            with st.expander("🔍 Debugging (Why no stock?)"):
                st.write("**Scanned Cells (Look here):**")
                for info in debug_info:
                    st.write(info)
                st.write("---")
                st.write("*Note: Checking Q2 first, then Q5, Q6, Q7, Q8. Stopping before Q9.*")

with c_sell:
    with st.container(border=True):
        st.markdown(f"<h3 style='color:#d93025; margin-top:0; text-align:center;'>🔻 SELL TASK</h3>", unsafe_allow_html=True)
        if is_sell_active:
            row_data = h_data[s_idx-1]
            try: display_qty = int(float(row_data[7])) if len(row_data) > 7 else 0
            except: display_qty = 0
            with st.form("sell_form"):
                st.markdown(f"**Stock:** {row_data[2] if len(row_data) > 2 else ''}"); st.markdown(f"**Holding:** {display_qty}")
                s_price = st.number_input("Sell Price", format="%.2f")
                if st.form_submit_button("🚨 BOOK PROFIT"):
                    with st.spinner("Booking..."):
                        live_row = h_ws.row_values(s_idx)[:14]; live_row[11] = s_price
                        s_ws.append_row(live_row, value_input_option='USER_ENTERED'); h_ws.delete_rows(s_idx)
                        st.balloons(); st.success("Profit Booked!"); time.sleep(1); st.rerun()
        else: st.info("No Active Sells. Hold your positions.")

st.caption(f"Terminal Active | User: {st.session_state.name}")