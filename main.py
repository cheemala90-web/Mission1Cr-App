import streamlit as st
import gspread
import pandas as pd
from datetime import date, datetime
import time
import json

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Mission 1 Cr | Live V47", layout="wide")

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
    div[role="radiogroup"] { background: #e8f5e9; padding: 10px; border-radius: 8px; border: 1px solid #2ea043; }
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
# 3. DATA ENGINE
# ==========================================
try:
    sh = gc.open_by_key(st.session_state.sid)
    try: r_ws = sh.worksheet("RAW")
    except: r_ws = None
    
    h_ws, s_ws, st_ws = sh.worksheet("HOLDING"), sh.worksheet("SOLD"), sh.worksheet("TRADING STEPS 3%")
    mp_ws = sh.worksheet("MONTHLY PERFORMANCE")

    h_data = h_ws.get_all_values()
    r_data = r_ws.get_all_values() if r_ws else []
    
    s_data = s_ws.get_all_values()
    st_data = st_ws.get_all_values()
    mp_data = mp_ws.get_all_values()

    # Core Data
    equity_bal = h_data[5][0] if len(h_data) > 5 else "0"
    
    # --- AUTO-FILL LOGIC ---
    fill_code = ""
    fill_qty = "0"
    fill_price = "0.00"
    source_msg = "Manual Mode"
    found = False
    
    # Validation Helper
    def looks_like_stock(val):
        v = str(val).strip().upper()
        # Filter garbage
        invalid = ["", "0", "FALSE", "#N/A", "TRUE", "STOCK", "CODE", "QTY", "PRICE", "LTP", "CMP", "TARGET", "SL", "Buy", "Sell"]
        if v in invalid: return False
        if len(v) < 2: return False 
        if v.replace('.','').isdigit(): return False 
        return True

    # --- LAYER 1: CHECK HOLDING (Priority: Q6, Q5, Q7, Q4, Q8) ---
    priority_indices = [5, 4, 6, 3, 7] 
    
    for idx in priority_indices:
        if len(h_data) > idx:
            row = h_data[idx]
            if len(row) > 16:
                val_q = str(row[16]).strip()
                if looks_like_stock(val_q):
                    fill_code = val_q
                    if "NSE:" not in fill_code.upper() and "BSE:" not in fill_code.upper():
                        fill_code = "NSE:" + fill_code
                        
                    source_msg = f"Auto-Filled from HOLDING (Q{idx+1})"
                    if len(row) > 18: fill_price = str(row[18]).strip()
                    if len(row) > 19: fill_qty = str(row[19]).strip()
                    found = True
                    break
    
    # --- LAYER 2: CHECK RAW SHEET ---
    if not found and r_data:
        scan_limit = min(len(r_data), 25)
        # Priority 1: Explicit NSE/BSE
        for r_idx, row in enumerate(r_data[:scan_limit]):
            for c_idx, cell_val in enumerate(row[:8]): 
                val_str = str(cell_val).strip().upper()
                if ("NSE:" in val_str or "BSE:" in val_str) and len(val_str) < 30:
                    fill_code = val_str
                    source_msg = f"Auto-Filled from RAW (Row {r_idx+1})"
                    for offset in range(1, 4):
                        if c_idx + offset < len(row):
                            possible_price = str(row[c_idx + offset]).strip()
                            if possible_price.replace('.','').replace(',','').isdigit():
                                fill_price = possible_price
                                break
                    found = True
                    break
            if found: break
            
        # Priority 2: Guessing stock name
        if not found:
             for r_idx, row in enumerate(r_data[:scan_limit]):
                for c_idx, cell_val in enumerate(row[:8]):
                    val_str = str(cell_val).strip()
                    if looks_like_stock(val_str) and val_str.isupper() and len(val_str) > 2:
                        fill_code = "NSE:" + val_str
                        source_msg = f"Auto-Filled from RAW (Guess) (Row {r_idx+1})"
                        found = True
                        break
                if found: break

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

# FIXED: Removed f-string triple quotes and used format to avoid Syntax Errors
html_template = """
    <div class="prog-container">
        <div style="display:flex; justify-content:space-between; font-weight:bold; color:#555; margin-bottom:10px;">
            <span>Start: ₹ 2L</span><span>Goal: ₹ 1 Cr</span>
        </div>
        <div style="background:#eee; height:24px; border-radius:12px; position:relative;">
            <div style="background:#2ea043; width:{}%; height:100%; border-radius:12px;"></div>
            <div style="position:absolute; top:-38px; left:{}%; transform:translateX(-50%); background:#003366; color:white; padding:5px 10px; border-radius:6px; font-weight:bold; font-size:12px; white-space:nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                Done: {} / {} | ₹ {}
            </div>
        </div>
        <div style="text-align:center; margin-top:5px; font-size:12px; color:#666;">
            Total Roadmap Length: <b>{} Steps</b>
        </div>
    </div>
"""
st.markdown(html_template.format(progress_pct, progress_pct, progress_count, TOTAL_STEPS, equity_bal, TOTAL_STEPS), unsafe_allow_html=True)

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

m_check = [row[12] if len(row) > 12 else "" for row in h_data[11:]] 
s_idx = next((i + 12 for i, v in enumerate(m_check) if v.strip()), None)
is_sell_active = s_idx is not None

c_buy, c_sell = st.columns(2)

with c_buy:
    with st.container(border=True):
        st.markdown(f"<h3 style='color:#2ea043; margin-top:0; text-align:center;'>⚡ BUY TASK</h3>", unsafe_allow_html=True)
        
        if fill_code:
            st.success(f"✅ {source_msg}")
        else:
            st.caption("ℹ️ Manual Mode (Enter details manually)")

        with st.form("buy_form"):
            confirmed_stock_code = st.text_input("Stock Code", value=fill_code, placeholder="Ex: NSE:INDIGO")
            
            if not fill_code:
                st.caption("Tip: Use format NSE:STOCKNAME")

            try: q_val = int(float(fill_qty.replace(',','')))
            except: q_val = 0
            final_qty = st.number_input("Confirm Qty", value=q_val, step=1)
            
            try: p_val = float(fill_price.replace(',',''))
            except: p_val = 0.0
            b_price = st.number_input("Exec Price", value=p_val, format="%.2f")
            
            if st.form_submit_button("✅ EXECUTE BUY"):
                if not confirmed_stock_code.strip():
                    st.error("❌ Stock Code cannot be empty!")
                else:
                    with st.spinner("Saving..."):
                        raw_vals = h_ws.get('O6:T6')[0]
                        stock_write = confirmed_stock_code.strip()
                        if "NSE:" not in stock_write.upper() and "BSE:" not in stock_write.upper():
                            stock_write = "NSE:" + stock_write
                            
                        raw_vals[2] = stock_write
                        raw_vals[4] = b_price
                        raw_vals[5] = final_qty
                        
                        h_ws.update(f'A{h_target_row}:F{h_target_row}', [raw_vals], value_input_option='USER_ENTERED')
                        st_ws.update_cell(ow_row, 10, stock_write)
                        st_ws.update_cell(ow_row, 11, b_price)
                        st_ws.update_cell(ow_row, 23, str(date.today()))
                        st.balloons(); st.success(f"Buy Saved for {stock_write}!"); time.sleep(1); st.rerun()

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