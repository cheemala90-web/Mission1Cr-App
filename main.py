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
    /* GLOBAL THEME */
    .stApp { background-color: #ffffff; color: #000000; }
    
    /* HEADER */
    .header-box { 
        background: #003366 !important; padding: 20px; border-radius: 12px; 
        border-bottom: 5px solid #ff7043; text-align: center; margin-bottom: 30px; 
    }
    .header-box h1 { color: white !important; margin: 0; font-size: 26px; }

    /* ORANGE BUTTONS (FORCED) */
    button[kind="primaryFormSubmit"], .stButton > button {
        background-color: #ff7043 !important; color: white !important;
        border: none !important; width: 100% !important; height: 50px !important;
        font-weight: bold !important; font-size: 18px !important; border-radius: 8px !important;
        box-shadow: 0 4px 6px rgba(255, 112, 67, 0.3) !important;
    }

    /* PROGRESS BAR - ORANGE BORDER */
    .prog-container { 
        padding: 20px; border: 2.5px solid #ff7043 !important; 
        border-radius: 12px; margin-bottom: 30px; 
    }

    /* STATS CARDS */
    .stats-card { background: #f8f9fa; padding: 15px; border: 1px solid #ddd; border-radius: 10px; text-align: center; margin-bottom: 15px; }
    .stats-lbl { color: #666; font-size: 11px; font-weight: bold; text-transform: uppercase; }
    .stats-val { color: #003366; font-size: 18px; font-weight: 900; margin-top: 5px; display: block; }
    
    /* GREEN SPEED TEXT */
    .stats-sub { font-size: 11px; color: #2ea043 !important; font-weight: 800 !important; margin-top: 4px; display: block; }

    /* INPUT BOX BLACK BORDER */
    div[data-baseweb="input"] > div { border: 2px solid #333333 !important; }
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
    st.session_state.update({'auth': False, 'sid': None, 'name': None})

if not st.session_state.auth:
    st.markdown('<div class="header-box"><h1>🔒 SECURE LOGIN</h1></div>', unsafe_allow_html=True)
    l_mob = st.text_input("Enter Registered Mobile Number")
    if st.button("UNLOCK TERMINAL"):
        try:
            db_ws = gc.open_by_key(MASTER_ID).worksheet("CLIENT_DB")
            df_users = pd.DataFrame(db_ws.get_all_records())
            user = df_users[df_users['Mobile'].astype(str).str.strip() == l_mob.strip()]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.sid = str(user.iloc[0]['Sheet_ID']).strip()
                st.session_state.name = user.iloc[0]['Client_Name']
                st.rerun()
            else: st.error("❌ Number Not Found!")
        except Exception as e: st.error(f"Login Error: {e}")
    st.stop()

# ==========================================
# 3. DATA ENGINE (P2 & S2 FETCH)
# ==========================================
try:
    sh = gc.open_by_key(st.session_state.sid)
    h_ws, s_ws, st_ws = sh.worksheet("HOLDING"), sh.worksheet("SOLD"), sh.worksheet("TRADING STEPS 3%")
    mp_ws = sh.worksheet("MONTHLY PERFORMANCE")

    h_data = h_ws.get_all_values()
    s_data = s_ws.get_all_values()
    st_data = st_ws.get_all_values()
    mp_data = mp_ws.get_all_values()

    # --- BUY SIGNAL (P2=Stock Code, S2=Quantity) ---
    auto_stock_code = h_ws.acell('P2').value
    auto_qty = h_ws.acell('S2').value 
    
    if not auto_stock_code: auto_stock_code = ""
    if not auto_qty: auto_qty = "0"

    # Core Stats
    equity_bal = h_data[5][0] if len(h_data) > 5 else "0"
    progress_count = len([r[10] for r in st_data[2:] if len(r) > 10 and r[10].strip() != ""])
    progress_pct = min((progress_count / 457) * 100, 100)
    sold_steps_count = len([r[2] for r in s_data[4:] if len(r) > 2 and r[2].strip() != ""])
    remaining_steps = 457 - sold_steps_count

    # AI Time Left Logic
    start_date = date.today()
    try:
        dates = pd.to_datetime([r[0] for r in s_data[4:] if r[0].strip()], dayfirst=True, errors='coerce').dropna()
        if not dates.empty: start_date = dates.min().date()
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
        time_display = "Start Trading"; speed_text = "0 Steps Done"

    # Save Helpers
    col_a = [row[0] for row in h_data]
    h_target_row = next((i+1 for i, v in enumerate(col_a) if i >= 11 and not v.strip()), len(col_a)+1)
    ow_row = next((i+1 for i, r in enumerate(st_data) if i >= 2 and len(r) > 9 and r[9].strip().isdigit()), 3)

except Exception as e:
    st.error(f"Sync Error: {e}"); st.stop()

# ==========================================
# 4. DASHBOARD UI
# ==========================================
st.markdown(f'<div class="header-box"><h1>🚀 MISSION 1 CR | {st.session_state.name.upper()}</h1></div>', unsafe_allow_html=True)

# Progress Bar
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
    col.markdown(f'<div class="stats-card"><span class="stats-lbl">{lbl}</span><br><span class="stats-val" style="color:{color}">{val}</span><span class="stats-sub">{speed_text if lbl=="AI Time Left" else ""}</span></div>', unsafe_allow_html=True)

# ==========================================
# 5. ACTION TERMINAL
# ==========================================
st.write("---")
is_buy_active = str(auto_stock_code).upper() not in ["", "0", "0.00", "#N/A", "NONE", "FALSE", "TRADING..."]
s_idx = next((i + 12 for i, r in enumerate(h_data[11:]) if len(r) > 12 and r[12].strip()), None)

cb, cs = st.columns(2)
# --- BUY CARD ---
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
                    # Row 6 Template used for writing to A:F
                    orig = h_ws.get('O6:T6')[0] 
                    orig[2], orig[4], orig[5] = auto_stock_code, prc, qty
                    h_ws.update(f'A{h_target_row}:F{h_target_row}', [orig], value_input_option='USER_ENTERED')
                    st_ws.update_cell(ow_row, 10, auto_stock_code); st_ws.update_cell(ow_row, 11, prc); st_ws.update_cell(ow_row, 23, str(date.today()))
                    st.balloons(); st.success("Task Completed!"); time.sleep(1); st.rerun()
        else: st.info("Nothing to buy today. Come back tomorrow!")

# --- SELL CARD ---
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
        else: st.info("No Active Sells. Hold tight!")

st.caption(f"Terminal Active | User: {st.session_state.name}")