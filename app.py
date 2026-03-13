iimport streamlit as st
import random
import json
import gspread
from google.oauth2.service_account import Credentials
from questions_data import raw_data

st.set_page_config(page_title="AI 應用企劃師刷題神器", page_icon="🚀")

# ================= 1. Google Sheets 資料庫邏輯 =================

@st.cache_resource
def get_gsheet_client():
    """設定並連線至 Google Sheets"""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # 從 Streamlit Secrets 讀取金鑰
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=scopes
    )
    client = gspread.authorize(creds)
    return client

def load_progress():
    """從 Google Sheets 讀取進度"""
    try:
        client = get_gsheet_client()
        sheet = client.open("QuizProgress").sheet1
        # 我們將所有的進度紀錄打包成字串，存在 A1 儲存格
        val = sheet.acell('A1').value
        if val:
            return json.loads(val)
        return {}
    except Exception as e:
        # 如果 A1 是空的或是發生錯誤，回傳空字典
        return {}

def save_progress(data):
    """將進度存回 Google Sheets"""
    try:
        client = get_gsheet_client()
        sheet = client.open("QuizProgress").sheet1
        # 將資料轉成 JSON 字串並寫入 A1 儲存格
        sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
    except Exception as e:
        st.error("存檔至雲端時發生錯誤，請稍後再試。")

def init_user_data(username, data):
    """初始化新使用者的進度"""
    if username not in data:
        all_indices = list(range(len(raw_data)))
        random.shuffle(all_indices)
        data[username] = {
            "unseen": all_indices,
            "wrong_pool": [],
            "current_batch": [],
            "batch_index": 0,
            "score": 0
        }
        save_progress(data)
    return data

def get_new_batch(user_data):
    """從題庫抽出新的 50 題"""
    batch_size = 50
    draw_count = min(batch_size, len(user_data["unseen"]))
    user_data["current_batch"] = user_data["unseen"][:draw_count]
    user_data["unseen"] = user_data["unseen"][draw_count:]
    user_data["batch_index"] = 0
    user_data["score"] = 0
    return user_data

# ================= 後面的登入介面與主系統邏輯完全不用變 =================
# (保持原本的 2. 登入介面、3. 主系統邏輯 等後續程式碼)
# ================= 2. 登入介面 (身分選擇) =================
if 'current_user' not in st.session_state:
    st.title("👋 歡迎來到 AI 刷題系統")
    st.write("請選擇你的專屬身分，系統將為你讀取學習進度：")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("登入身分：614", use_container_width=True):
            st.session_state.current_user = "614"
            st.rerun()
    with col2:
        if st.button("登入身分：941", use_container_width=True):
            st.session_state.current_user = "941"
            st.rerun()
    st.stop() # 停止渲染後續內容，直到選擇身分

# ================= 3. 主系統邏輯 =================
user = st.session_state.current_user
all_data = load_progress()
all_data = init_user_data(user, all_data)
udata = all_data[user]

# 側邊欄：強制重新洗牌與身分切換
with st.sidebar:
    st.write(f"👤 目前使用者：**{user}**")
    if st.button("🚪 登出 / 切換身分"):
        del st.session_state.current_user
        st.rerun()
    
    st.divider()
    st.write("⚠️ 危險操作區")
    if st.button("🔄 題庫全面重新洗牌"):
        all_indices = list(range(len(raw_data)))
        random.shuffle(all_indices)
        udata["unseen"] = all_indices
        udata["wrong_pool"] = []
        udata["current_batch"] = []
        udata["batch_index"] = 0
        udata["score"] = 0
        save_progress(all_data)
        st.session_state.pop('answered', None)
        st.rerun()

# 如果本回合沒題目了，且還有剩餘題庫，就抽新題目
if len(udata["current_batch"]) == 0 and len(udata["unseen"]) > 0:
    udata = get_new_batch(udata)
    save_progress(all_data)

st.title("🚀 AI 應用企劃師 刷題神器")
st.divider()

# ================= 4. 題庫耗盡的結算畫面 (重點功能) =================
if len(udata["current_batch"]) == 0 and len(udata["unseen"]) == 0:
    st.balloons()
    st.success("🏆 恭喜你！你已經把目前題庫裡所有的題目都刷過至少一輪了！")
    st.write(f"📝 你的「錯題本」裡面目前累積了 **{len(udata['wrong_pool'])}** 道不熟悉的題目。")
    
    col1, col2 = st.columns(2)
    with col1:
        if len(udata['wrong_pool']) > 0:
            if st.button("🎯 將錯誤的題目打亂再一次", use_container_width=True):
                # 把錯題本變成新的未做題庫
                udata["unseen"] = udata["wrong_pool"].copy()
                random.shuffle(udata["unseen"])
                udata["wrong_pool"] = []
                udata = get_new_batch(udata)
                save_progress(all_data)
                st.session_state.pop('answered', None)
                st.rerun()
        else:
            st.info("🎉 你的錯題本是空的！太神啦！")
            
    with col2:
        if st.button("🔄 將 345 題重新洗牌重刷", use_container_width=True):
            all_indices = list(range(len(raw_data)))
            random.shuffle(all_indices)
            udata["unseen"] = all_indices
            udata["wrong_pool"] = []
            udata = get_new_batch(udata)
            save_progress(all_data)
            st.session_state.pop('answered', None)
            st.rerun()
    st.stop()

# ================= 5. 測驗介面 =================
batch_total = len(udata["current_batch"])
current_q_idx = udata["batch_index"]
real_q_index = udata["current_batch"][current_q_idx]
q_data = raw_data[real_q_index]

st.caption(f"📦 總題庫剩餘：{len(udata['unseen'])} 題 ｜ 📓 錯題本累積：{len(udata['wrong_pool'])} 題")
st.caption(f"🏃 本回合進度：第 {current_q_idx + 1} / {batch_total} 題 ｜ 🎯 得分：{udata['score']}")
st.write(f"### {q_data['question']}")

# 洗牌選項 (確保每次出現選項順序都不同)
if 'shuffled_options' not in st.session_state or st.session_state.get('current_real_q') != real_q_index:
    opts = q_data['options'].copy()
    random.shuffle(opts)
    st.session_state.shuffled_options = opts
    st.session_state.current_real_q = real_q_index
    st.session_state.answered = False # 確保新題目的狀態是未作答

# 顯示選項
user_choice = st.radio("請選擇：", st.session_state.shuffled_options, index=None, disabled=st.session_state.answered)

if not st.session_state.answered:
    if st.button("確認答案"):
        if user_choice == None:
            st.warning("⚠️ 請先選擇一個答案喔！")
        else:
            st.session_state.answered = True
            st.session_state.user_choice = user_choice
            
            # 判斷對錯並記錄
            if user_choice == q_data['answer']:
                udata["score"] += 1
            else:
                # 答錯了，加入錯題本 (如果還沒加過)
                if real_q_index not in udata["wrong_pool"]:
                    udata["wrong_pool"].append(real_q_index)
            
            save_progress(all_data) # 立即存檔
            st.rerun()

if st.session_state.answered:
    if st.session_state.user_choice == q_data['answer']:
        st.success("🎉 答對了！")
    else:
        st.error(f"❌ 答錯囉！正確答案是： {q_data['answer']}")
        
    st.info(q_data['explanation'])
    st.divider()

    # 判斷下一題還是結算
    if current_q_idx < batch_total - 1:
        if st.button("下一題 ➡️"):
            udata["batch_index"] += 1
            save_progress(all_data)
            st.session_state.answered = False
            st.rerun()
    else:
        st.success(f"🏆 休息一下！這回合結束！你的得分是：{udata['score']} / {batch_total}")
        if st.button("☕ 繼續下一回合"):
            udata = get_new_batch(udata)
            save_progress(all_data)
            st.session_state.answered = False
            st.rerun()