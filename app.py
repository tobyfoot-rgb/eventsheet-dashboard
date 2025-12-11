import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Miami Event Dashboard", layout="wide", page_icon="🎾")

# --- CUSTOM CSS (DARK MODE & HIGH CONTRAST ORANGE) ---
st.markdown("""
<style>
    /* 1. GLOBAL SETTINGS */
    .stApp {
        background-color: #0E1117;
        color: #FFB74D;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #FF9800 !important;
    }
    p, div, span {
        color: #FFB74D;
    }
    
    /* 2. CARD STYLES */
    .court-card {
        background-color: #1E1E1E;
        border: 1px solid #FF9800;
        border-radius: 10px;
        padding: 20px;
        transition: transform 0.2s;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .court-card:hover {
        transform: scale(1.02);
        box-shadow: 0 0 10px rgba(255, 152, 0, 0.4);
    }
    
    .card-header {
        color: #FF9800 !important;
        font-weight: bold;
        font-size: 1.3em;
    }
    .card-sub {
        color: #FFE0B2 !important;
        font-size: 0.9em;
    }
    .card-stat {
        color: #FFCC80 !important;
        font-size: 0.85em;
    }
    
    /* 3. TASK BOX */
    .task-container {
        background-color: #332600;
        border: 1px solid #FFC107;
        color: #FFECB3 !important;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    /* 4. BUTTONS */
    div.stButton > button {
        color: #000000 !important;
        font-weight: bold;
    }

</style>
""", unsafe_allow_html=True)

# --- 1. DATA LOADING (DEBUGGABLE) ---
@st.cache_data
def load_excel_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'data.xlsx')
    
    # DEBUG: Print where we are looking (Visible in logs only)
    print(f"DEBUG: Looking for file at {file_path}")
    
    if not os.path.exists(file_path):
        st.error(f"❌ CRITICAL ERROR: Could not find 'data.xlsx'.")
        st.info(f"The app is looking in: {current_dir}")
        st.info("Make sure the file is named exactly 'data.xlsx' (case sensitive) in your GitHub repo.")
        return None, None

    try:
        kit = pd.read_excel(file_path, sheet_name='StadiumKit IDs', header=1)
        try:
            feeds = pd.read_excel(file_path, sheet_name='Feeds ', header=None)
        except:
            feeds = pd.read_excel(file_path, sheet_name='Feeds', header=None)
        return kit, feeds
    except Exception as e:
        st.error(f"❌ DATA LOADING ERROR: {e}")
        st.info("Check: Did you add 'openpyxl' to your requirements.txt?")
        return None, None

def check_excel_status(df, court_name, row_label):
    try:
        court_col_idx = -1
        header_row = df.iloc[4]
        for idx, val in header_row.items():
            if isinstance(val, str) and court_name.lower() in val.lower():
                court_col_idx = idx
                break
        if court_col_idx == -1: return False

        for idx, row in df.iterrows():
            if (str(row[0]).lower() in row_label.lower()) or (str(row[1]).lower() in row_label.lower()):
                val = df.iloc[idx, court_col_idx]
                if pd.isna(val): val = df.iloc[idx, court_col_idx + 1]
                return str(val).lower() in ['true', 'yes', 'on', '1', 'ok']
        return False
    except:
        return False

# --- 2. LOGIC ENGINE (SAFE INITIALIZATION) ---
if 'court_data' not in st.session_state:
    # 1. Initialize as empty FIRST to prevent KeyErrors if loading fails
    st.session_state['court_data'] = {} 
    
    # 2. Try to load data
    kit_df, feeds_df = load_excel_data()
    
    if kit_df is not None:
        full_prod_assets = [
            "Camera 1", "Camera 2", "Camera 3", "Camera 4", "Camera 0",
            "Near Mic L", "Near Mic R", "Far Mic L", "Far Mic R", "Umpire Mic",
            "Main Power", "Power Cam 3", "Power Cam 4",
            "Cam 1 Data", "Cam 2 Data", "Cam 3 Data", "Cam 4 Data"
        ]
        streaming_assets = [
            "Camera 0", "Near Mic L", "Near Mic R", "Umpire Mic", "Main Power"
        ]

        for _, row in kit_df.iterrows():
            c_name = str(row['Court Name']).strip()
            if c_name.lower() == 'nan': continue
            
            c_type = str(row['Production Type'])
            blueprint = full_prod_assets if "Full" in c_type else streaming_assets
            
            st.session_state['court_data'][c_name] = {'type': c_type, 'items': {}}
            
            for item in blueprint:
                is_done = False
                if feeds_df is not None and "Camera" in item:
                    is_done = check_excel_status(feeds_df, c_name, item)
                
                state = 2 if is_done else 0 
                st.session_state['court_data'][c_name]['items'][item] = state

if 'selected_court' not in st.session_state:
    st.session_state['selected_court'] = None

# --- 3. HELPER FUNCTIONS ---
def cycle_state(court, item):
    if court in st.session_state['court_data']:
        current = st.session_state['court_data'][court]['items'][item]
        new_state = (current + 1) % 3
        st.session_state['court_data'][court]['items'][item] = new_state

def calculate_progress(court):
    if court not in st.session_state['court_data']: return 0
    items = st.session_state['court_data'][court]['items']
    total_points = len(items) * 2 
    current_points = sum(items.values())
    return int((current_points / total_points) * 100) if total_points > 0 else 0

def get_next_tasks(court):
    if court not in st.session_state['court_data']: return []
    items = st.session_state['court_data'][court]['items']
    
    rig_tasks = []
    test_tasks = []
    
    for name, state in items.items():
        if "Power" in name:
            if state == 0: rig_tasks.append(f"Locate {name}")
            elif state == 1: test_tasks.append(f"Get {name} Up & Running")
        else:
            if state == 0: rig_tasks.append(f"Rig {name}")
            elif state == 1: test_tasks.append(f"Test {name}")
            
    return rig_tasks + test_tasks

# --- 4. RENDER: HOME PAGE ---
if st.session_state['selected_court'] is None:
    st.title("🎾 Event Overview")
    
    # Check if data loaded correctly
    if not st.session_state['court_data']:
        st.warning("No court data found. Please fix the data loading error above.")
    else:
        col_full, col_stream = st.columns(2)
        
        with col_full:
            st.subheader("Production Courts")
            for court, data in st.session_state['court_data'].items():
                if "Full" in data['type']:
                    progress = calculate_progress(court)
                    color = "#4CAF50" if progress == 100 else "#FF9800"
                    st.markdown(f"""
                    <div class="court-card">
                        <div class="card-header">{court}</div>
                        <div class="card-sub">{data['type']}</div>
                        <div style="background-color:#333; height:8px; border-radius:4px; overflow:hidden; margin: 10px 0;">
                            <div style="width:{progress}%; background-color:{color}; height:100%;"></div>
                        </div>
                        <div class="card-stat" style="text-align:right;">{progress}% Ready</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Manage {court}", key=f"btn_{court}"):
                        st.session_state['selected_court'] = court
                        st.rerun()

        with col_stream:
            st.subheader("Streaming Courts")
            for court, data in st.session_state['court_data'].items():
                if "Streaming" in data['type']:
                    progress = calculate_progress(court)
                    color = "#4CAF50" if progress == 100 else "#FFC107"
                    st.markdown(f"""
                    <div class="court-card">
                        <div class="card-header">{court}</div>
                        <div class="card-sub">{data['type']}</div>
                        <div style="background-color:#333; height:8px; border-radius:4px; overflow:hidden; margin: 10px 0;">
                            <div style="width:{progress}%; background-color:{color}; height:100%;"></div>
                        </div>
                        <div class="card-stat" style="text-align:right;">{progress}% Ready</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Manage {court}", key=f"btn_{court}"):
                        st.session_state['selected_court'] = court
                        st.rerun()

# --- 5. RENDER: DETAIL VIEW ---
else:
    court = st.session_state['selected_court']
    
    # Safety check in case session state gets weird
    if court not in st.session_state['court_data']:
        st.session_state['selected_court'] = None
        st.rerun()
        
    data = st.session_state['court_data'][court]
    
    c1, c2 = st.columns([1, 6])
    if c1.button("⬅ Back"):
        st.session_state['selected_court'] = None
        st.rerun()
    c2.title(f"{court}")

    # TASK LIST
    tasks = get_next_tasks(court)
    if tasks:
        task_list = "<br>".join([f"• {t}" for t in tasks[:4]])
        remaining = f"<br><i>...and {len(tasks)-4} more</i>" if len(tasks) > 4 else ""
        st.markdown(f"""
        <div class="task-container">
            <div style="font-weight:bold; font-size:1.1em; margin-bottom:5px; color: #FF9800;">⚠️ Priority Actions</div>
            {task_list}
            {remaining}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ Court Complete")

    st.divider()

    cats = {
        "🎥 Video": ["Camera"],
        "💾 Data": ["Data"],
        "🎤 Audio": ["Mic"],
        "⚡ Power": ["Power"]
    }
    
    cols = st.columns(4)
    
    for i, (cat_name, keywords) in enumerate(cats.items()):
        with cols[i]:
            with st.container(border=True):
                st.subheader(cat_name)
                items = [k for k in data['items'].keys() if any(x in k for x in keywords)]
                
                for item in items:
                    state = data['items'][item]
                    is_power = "Power" in cat_name
                    
                    if is_power:
                        if state == 0:
                            pill_text = "NOT PROVIDED"
                            pill_color = "#333" 
                        elif state == 1:
                            pill_text = "LOCATED"
                            pill_color = "#FFC107" 
                        else:
                            pill_text = "UP & RUNNING"
                            pill_color = "#4CAF50" 
                    else:
                        if state == 0:
                            pill_text = "NOT RIGGED"
                            pill_color = "#333"
                        elif state == 1:
                            pill_text = "RIGGED"
                            pill_color = "#2196F3"
                        else:
                            pill_text = "TESTED"
                            pill_color = "#4CAF50"
                    
                    c_label, c_btn = st.columns([1.5, 1])
                    c_label.markdown(f"<div style='font-size:0.9em; margin-top:8px; color: #FFB74D; font-weight: 500;'>{item}</div>", unsafe_allow_html=True)
                    
                    if c_btn.button(pill_text, key=f"{court
