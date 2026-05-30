import os
import re
from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection 

# ==========================================
# 🚨 구글 스프레드시트 주소
# ==========================================
EQUIPMENT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1DkU-1hCQuTApnnFxfZAh1MXulrD6HxPHY4P1QjhqJq0/edit?gid=1121757229#gid=1121757229"
RENTAL_SHEET_URL = "https://docs.google.com/spreadsheets/d/1hV8oaUlEIEA4rF6peg083Td_1cNZbWbl6BCcEkRpkT8/edit?gid=183591911#gid=183591911"

# ==========================================
# 🖼️ 기자재 사진 URL 매핑 딕셔너리
# ==========================================
EQUIP_IMAGES = {
    "Cinema Line FX3": "https://via.placeholder.com/150/555555/FFFFFF?text=FX3",
    "PWX-FS5": "https://via.placeholder.com/150/555555/FFFFFF?text=FS5",
    "PWX-Z90": "https://via.placeholder.com/150/555555/FFFFFF?text=Z90",
    "A7S 3": "https://via.placeholder.com/150/555555/FFFFFF?text=A7S3",
    "A7 4": "https://via.placeholder.com/150/555555/FFFFFF?text=A7+4",
    "ZV-E10": "https://via.placeholder.com/150/555555/FFFFFF?text=ZV-E10",
    "Gopro (Hero 7 Black)": "https://via.placeholder.com/150/555555/FFFFFF?text=GoPro",
    "오즈모 포켓2": "https://via.placeholder.com/150/555555/FFFFFF?text=Osmo+Pocket2",
    "OM5 오즈모 모바일": "https://via.placeholder.com/150/555555/FFFFFF?text=OM5",
    "Sony 28-135": "https://via.placeholder.com/150/555555/FFFFFF?text=28-135mm",
    "Sony 24-70": "https://via.placeholder.com/150/555555/FFFFFF?text=24-70mm",
    "Sony 70-200": "https://via.placeholder.com/150/555555/FFFFFF?text=70-200mm",
}
DEFAULT_IMAGE_URL = "https://via.placeholder.com/150/CCCCCC/666666?text=No+Image"

# --- 공지사항 텍스트 파일 및 기본 공지 내용 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTICE_FILE = os.path.join(BASE_DIR, "notice.txt")

DEFAULT_NOTICE = """### 📢 글로벌예술학부 기자재 대여 시스템 이용 안내

안녕하세요. 기자재실입니다. 
원활하고 안전한 기자재 대여 및 관리를 위해 아래 안내 사항을 반드시 숙지해 주시기 바랍니다.

**1. 대여 신청 기한 및 시스템 이용 안내**
* 기자재 대여 신청은 대여 희망일 기준 **최소 3일 전 신청을 원칙**으로 합니다.
* 접수된 기자재 대여 신청서는 **매일 오전 10시와 오후 2시**에 일괄적으로 확인 및 승인 처리됩니다.
* **대여 및 반납 시간은 09:00~17:00까지**입니다.
* 원활한 대여 준비를 위해 기한과 승인 시간을 고려하여 사전에 여유 있게 신청서를 제출해 주시기 바랍니다.
* 본 시스템은 PC 웹 환경에 최적화되어 있으므로, 원활한 신청 및 화면 조회를 위해 스마트폰보다는 **컴퓨터 및 노트북에서 접속하는 것을 권장**합니다.

**2. 신청서 외 장비 당일 현장 추가 불가**
* 시스템에 제출된 **신청서에 기재된 품목 외에, 대여 당일 현장에서 즉흥적으로 장비를 추가하는 것은 절대 불가**합니다. 
* 대여 신청 전, 촬영에 필요한 장비가 장바구니에 모두 정확하게 담겼는지 꼼꼼히 확인해 주시기 바랍니다.

**3. 기자재 이용 규정 숙지 의무**
* 좌측 메뉴의 **[기자재 이용 규정]**을 반드시 정독해 주시기 바랍니다. 
* 규정 미숙지로 인해 발생하는 장비 대여 제한 및 배상 등의 불이익은 신청자 본인과 해당 팀에게 책임이 있습니다.

**4. 개인정보(학번 및 연락처) 수집 동의 및 면책 안내**
* 대여 신청 시 입력하시는 학번과 연락처는 대여 중 미반납 또는 긴급 상황 발생 시 연락을 위한 용도로만 활용되며, 반납 완료 시 시스템에서 즉시 파기됩니다.
* 단, 연락처 오기재로 인한 연락 두절, 학생 본인의 부주의로 인한 정보 노출 등 **신청자 측의 귀책사유로 발생하는 어떠한 불이익 및 개인정보 관련 문제에 대해서도 기자재실은 일절 법적·도의적 책임을 지지 않습니다.**
* 본 시스템을 통해 신규 대여를 신청하는 것은 위 개인정보 수집 및 면책 조항에 동의하는 것으로 간주합니다.

우리 모두의 소중한 기자재입니다. 안전하고 올바른 이용을 부탁드립니다. 감사합니다."""

def load_data():
    """구글 스프레드시트에서 실시간으로 데이터를 불러오는 함수"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        df_equip = conn.read(spreadsheet=EQUIPMENT_SHEET_URL, ttl=300)
        df_rental = conn.read(spreadsheet=RENTAL_SHEET_URL, ttl=300)

        # ✨ 기자재자산번호 컬럼 추가 (없으면 생성)
        required_equip_cols = ["장비ID", "품명", "규격", "현재상태", "기자재자산번호", "비고"]
        for col in required_equip_cols:
            if col not in df_equip.columns:
                df_equip[col] = ""

        required_rental_cols = ["신청ID", "장비ID", "품명", "규격", "이름", "학번", "연락처", "담당교수", "교과명", "촬영장소", "기타기자재", "대여날짜", "반납일자", "승인상태"]
        for col in required_rental_cols:
            if col not in df_rental.columns:
                df_rental[col] = ""

        for df in [df_equip, df_rental]:
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].astype(str).str.strip()
                
        return df_equip, df_rental
    except Exception as e:
        st.error(f"❌ 구글 시트에서 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        st.stop()

def save_data(df_equip, df_rental):
    """변경된 데이터를 즉시 구글 스프레드시트에 덮어쓰는 함수"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(spreadsheet=EQUIPMENT_SHEET_URL, data=df_equip)
        conn.update(spreadsheet=RENTAL_SHEET_URL, data=df_rental)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ 구글 시트에 데이터를 저장하는 중 오류가 발생했습니다: {e}")

# ==========================================
# 🎨 아이콘 부여 및 HTML 생성 헬퍼 함수
def get_item_icon_html(name, spec, qty):
    """장비명과 규격을 분석하여 직관적인 아이콘과 HTML 태그를 반환합니다."""
    combined_name = f"{name} {spec}".lower()
    
    if any(k in combined_name for k in ["fx3", "fs5", "z90", "a7", "zv-", "캠코더", "카메라", "gopro", "바디"]): icon = "🎥"
    elif any(k in combined_name for k in ["렌즈", "28-135", "24-70", "70-200", "lens"]): icon = "🔍"
    elif any(k in combined_name for k in ["오즈모", "짐벌", "모바일", "포켓", "로닌", "gimbal"]): icon = "🤳"
    elif any(k in combined_name for k in ["조명", "라이트", "light"]): icon = "💡"
    elif any(k in combined_name for k in ["마이크", "녹음기", "오디오", "mic", "zoom", "pre"]): icon = "🎙️"
    elif any(k in combined_name for k in ["삼각대", "트라이포드", "tripod", "stand"]): icon = "🔭"
    elif any(k in combined_name for k in ["배터리", "충전기", "battery"]): icon = "🔋"
    elif any(k in combined_name for k in ["flag", "플래그"]): icon = "🏴"
    else: icon = "📦"
        
    return f"<div style='background-color:#f8f9fa; padding:6px 8px; border-radius:4px; border:1px solid #e9ecef; font-size:13px;'><b>{icon} {name}</b> <span style='font-size:11px; color:#555;'>({spec})</span> <span style='font-weight:bold; color:#d32f2f; margin-left:5px;'>x {qty}대</span></div>"

# ==========================================
# --- 스팀릿 웹 페이지 설정 ---
st.set_page_config(page_title="기자재 관리 시스템", layout="wide")

st.markdown("""
    <style>
    .printable-area { background-color: #ffffff; padding: 25px; border: 1px solid #ddd; border-radius: 8px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- Session State 초기화 ---
if "cart" not in st.session_state: st.session_state.cart = []
if "admin_auth" not in st.session_state: st.session_state.admin_auth = False
if "clear_inputs" not in st.session_state: st.session_state.clear_inputs = False
if "submit_success" not in st.session_state: st.session_state.submit_success = False
if "notice_agreed" not in st.session_state: st.session_state.notice_agreed = False

current_notice = DEFAULT_NOTICE
if os.path.exists(NOTICE_FILE):
    with open(NOTICE_FILE, "r", encoding="utf-8") as f:
        current_notice = f.read().strip()

@st.dialog("📢 시스템 이용 안내 및 동의", width="large")
def show_notice_dialog(notice_text):
    st.markdown(notice_text)
    st.markdown("---")
    if st.checkbox("✅ 위 안내 사항 및 개인정보 수집/면책 조항에 모두 동의합니다."):
        st.session_state.notice_agreed = True
        st.rerun()

if not st.session_state.notice_agreed:
    show_notice_dialog(current_notice)
    st.stop()

st.title("🎬 기자재 관리 시스템")
df_equip, df_rental = load_data()

# --- 사이드바 ---
st.sidebar.subheader("🔒 관리자 로그인")
if not st.session_state.admin_auth:
    input_password = st.sidebar.text_input("관리자 비밀번호를 입력하세요", type="password")
    if input_password == "Cau3352":
        st.session_state.admin_auth = True
        st.rerun()
    elif input_password:
        st.sidebar.error("❌ 비밀번호가 일치하지 않습니다.")
else:
    st.sidebar.success("✅ 인증되었습니다! 관리자 모드 활성화")
    if st.sidebar.button("🔓 관리자 모드 종료 (로그아웃)", use_container_width=True):
        st.session_state.admin_auth = False
        st.rerun()

is_admin = st.session_state.admin_auth
st.sidebar.markdown("---")

menu_options = [
    "공지사항", 
    "기자재 이용 규정", 
    "장비 목록 조회", 
    "신규 대여 신청", 
    "대여 신청 현황", 
    "품목별 대여 통계"
]

if is_admin:
    menu_options.append("기자재 반납 처리")
    menu_options.append("⚙️ 장비 관리 (관리자 전용)")

menu = st.sidebar.radio("📌 메뉴 선택", menu_options)

# --- 0. 공지사항 메뉴 ---
if menu == "공지사항":
    st.header("📢 공지사항")
    if is_admin:
        st.info("관리자 모드입니다. 아래에서 공지사항을 수정하고 저장할 수 있습니다.")
        new_notice = st.text_area("📝 공지사항 내용 수정", value=current_notice, height=400)
        if st.button("💾 공지사항 저장 및 적용하기", type="primary"):
            with open(NOTICE_FILE, "w", encoding="utf-8") as f:
                f.write(new_notice)
            st.success("✅ 공지사항이 성공적으로 업데이트되었습니다!")
            st.rerun()
    else:
        st.markdown("### 📌 안내 말씀")
        st.success(current_notice)

# --- 0-1. 기자재 이용 규정 메뉴 ---
elif menu == "기자재 이용 규정":
    st.header("📜 TV방송연예전공 기자재 이용 규정")
    st.markdown("""
    ---
    **제1조 【목 적】**
    기자재를 이용하는 학생들의 건전한 이용문화 정착과 기자재의 지속적인 유지 및 관리를 위한 체계를 만드는데 그 목적이 있다.

    **제2조 【기자재 이용 목적】**
    기자재는 수업, 글로벌예술학부 워크샵, 과제 및 스터디 모임을 위한 목적으로 이용가능하다.
    * 영리를 목적으로 하는 개인 프로젝트를 위한 사용은 불가하다.

    **제3조 【기자재 이용 대상】**
    1. 연출자, 촬영자, 녹음자가 본교에 재학 중인 학생을 기자재 이용 대상으로한다.
    2. 본교 재학생이더라도 기자재 운용능력이 부족한 학생 및 기자재 관리에 대한 이해가 부족한 학생은 기자재 담당 및 조교의 판단 하에 이용 대상에서 제외된다.
    3. 기자재 교육을 받지 못한 학생은 이용 대상에서 제외된다.
    4. 본교의 졸업생, 휴학생의 장비사용규정은 제15조를 참고하도록한다.

    **제4조 【기자재 관리 책임】**
    기자재의 관리 및 총 책임은 1차적으로 연출자에게 있다. 
    하지만, 장비의 이상 유무를 확인하지 않아서 생기는 불이익과 배상에 대한 책임은 연출자와 촬영자 모두에게 있다. 
    단, 배상에 대한 책임과 절차는 해당 팀 내에서 자체적으로 결정한다.

    **제5조 【기자재 이용 가능일】**
    * 학기/방학 중 이용 가능요일 
      * 대여 : 월~금
      * 반납 및 신청서 접수 : 월~금
    * 대여기간은 대여일을 포함하여 최대 7일까지 가능하다.
    * 수업 실습으로 인한 기자재 대여는 매학기 일정에 맞춰 대여가 가능하다.
    * 제14조에 해당하는 스터디 모임은 월~금 중에도 대여가 가능하다.

    **제6조 【기자재 이용 절차】**
    * **대여 (일주일 전):** 1. 기자재실 홈페이지 신청(연출자신청, 기자재 교육 수료자만 신청가능)
      2. 연출자 신청서 제출(기자재실 담당교수 서명 포함)
    * **대여 당일:** 연출자와 촬영자가 가자재실을 함께 방문하여 대여 (*기자재 이상 유무 확인 철저)
    * **반납 당일:** 연출자와 촬영자가 기자재실을 함께 방문하여 반납 (*기자재 이상 유무 및 기자재 정리상태 확인)
    * 글로벌예술학부의 타 전공(실용음악/게임 콘텐츠 애니메이션) 학생은 일주일 전 1/2학년 대상의 기자재를 대여 할 수 대여 할 수 있다.

    **제7조 【기자재 대여 자격】**
    * 학과 및 학년에 따른 기자재 운용능력을 고려하여 기자재 대여 자격을 순차적으로 부여한다.
    * 카메라는 기본적으로 한 팀당 한 대만 대여가 가능하다.
    * 악세사리는 해당 주용 기자재 대여 시에만 대여한다.(단독으로 대여하지 않는다.)

    **제8조 【보충촬영】**
    * 보충 촬영으로 인한 기자재 대여는 본교의 기자재 내규를 동일하게 따른다.

    **제9조 【기자재 대여 제한】**
    1. 신청 절차 및 규정을 지키지 않은 경우.
    2. 대여 당일 연출자나 촬영자가 참석하지 않은 경우.
    3. 대여 당일 시간을 지키지 않은 경우.
    4. 연출자 및 메인 스텝의 기자재 운용 능력이 부족하다고 판단되는 경우.
    5. 기자재 담당 교수의 승인 없이 경제적 이익을 목적으로 하는 프로젝트인 경우.
    6. 연출자가 본교 학생이 아닌 경우. (단, 촬영자에 한해서 본교의 졸업생인 경우 전임 교수 승인 하에 가능)
    8. 기자재를 신청하거나 이용하는 학생이 징계 중인 학생인 경우.

    **제10조 【기자재 파손 및 분실 보상 절차】**
    1. 기자재 담당에게 해당 내용 보고.
    2. 연출자는 손망실 보고서를 작성하여 기자재 담당에게 제출 후 해당 장비 보상.
    3. 당시 정황을 따져 징계수위 결정 후 책임자에게 징계내용 통보.
    * 보상 기간은 기본적으로 보상에 대한 내용이 책임자에게 전달 된 날부터 일주일 이내로 한다.

    **제11조 【징 계】**
    기자재를 이용하는 학생이 내규를 위반 할 경우 기자재 담당자는 해당 학생에게 징계 할 수 있다.
    * **경징계:** 대여 및 반납 시간을 미준수한 경우, 당일 참석하지 않은 경우 등
    * **중징계:** 장비의 파손 및 분실을 발생시킨 경우, 이해가 부족한 행위를 한 경우 등 (강제 반납조치 가능)

    **제12조 【징계 수위】**
    1. 장비 강제 반납조치
    2. 장비사용제한
       * 경징계 : 최대 14일 이하의 장비사용제한 후 기간이 지나면 회복.
       * 중징계 : 최대 30일 이하의 장비사용제한 후 기간이 지나면 회복.

    **제13조 【스터디 모임】**
    1. 기자재 담당 교수님의 승인을 얻은 모임.
    2. 온라인 학부 카페나 교내 게시판을 통해 목적과 취지가 홍보가 된 모임.
    3. 해당 스터디 내용이 최소 일주일 전에 담당교수와 기자재 담당자에게 공지 된 모임.

    **제14조 【스터디 모임 장비책임자】**
    스터디 모임의 장비책임자는 그 모임을 이끄는 스터디 팀장에게 있다.

    **제15조 【졸업생 및 휴학생의 장비 사용】**
    1. 재학생의 장비사용 일정을 우선으로 한다.
    2. 전임교수의 장비사용 승인을 필수로 한다.
    3. 본교의 장비가 사용된 작품은 본교의 제작지원을 크레딧에 명시하도록 한다.
    4. 본교의 장비가 사용된 작품은 해당년도 글로벌예술학부 영화제에 필히 상영하도록 한다.
    ---
    """)

# --- 1. 장비 목록 조회 ---
elif menu == "장비 목록 조회":
    st.header("🔍 기자재 목록 조회")
    st.subheader("📊 품목별 보유 현황 (수량 요약)")
    if df_equip.empty:
        st.info("등록된 장비가 없습니다.")
    else:
        df_summary_input = df_equip.copy()
        df_summary_input["품명"] = df_summary_input["품명"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        df_summary_input["규격"] = df_summary_input["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        
        df_summary = (
            df_summary_input.groupby(["품명", "규격"])
            .agg(
                총보유수량=("장비ID", "count"),
                대여가능=("현재상태", lambda x: (x == "대여가능").sum()),
                승인대기=("현재상태", lambda x: (x == "승인대기").sum()),
                대여중=("현재상태", lambda x: (x == "대여중").sum()),
                점검및고장=("현재상태", lambda x: x.isin(["고장", "수리중"]).sum()),
            ).reset_index()
        )
        
        df_summary.insert(0, "사진", df_summary["규격"].map(EQUIP_IMAGES).fillna(DEFAULT_IMAGE_URL))
        
        st.dataframe(
            df_summary, 
            column_config={
                "사진": st.column_config.ImageColumn("미리보기", help="기자재 썸네일")
            },
            use_container_width=True, 
            hide_index=True
        )

    st.markdown("---")
    st.subheader("📋 개별 장비 상세 현황")
    filter_option = st.radio("필터 선택", ["전체 장비 보기", "대여 가능 장비만 보기"], horizontal=True)
    display_df = df_equip[df_equip["현재상태"] == "대여가능"].copy() if filter_option == "대여 가능 장비만 보기" else df_equip.copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- 2. 신규 대여 신청 ---
elif menu == "신규 대여 신청":
    if st.session_state.get("submit_success"):
        st.success("🎉 대여 신청이 성공적으로 제출되었습니다! 관리자 승인을 기다려주세요.")
        st.session_state.submit_success = False

    if st.session_state.get("clear_inputs"):
        for k in ["input_name", "input_student_id", "input_phone", "input_professor", "input_course", "input_location", "input_extra"]:
            if k in st.session_state: st.session_state[k] = ""
        st.session_state.clear_inputs = False

    st.header("📝 신규 대여 신청서 작성")
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.subheader("📅 대여 일정 및 시간 선택")
        selected_dates = st.date_input("📆 대여 시작일과 반납 예정일을 지정하세요", value=(datetime.today().date(), datetime.today().date()))
        col_time1, col_time2 = st.columns(2)
        with col_time1: start_time = st.time_input("⏰ 대여 시작 시간", value=datetime.strptime("09:30", "%H:%M").time())
        with col_time2: end_time = st.time_input("⏰ 반납 예정 시간", value=datetime.strptime("15:30", "%H:%M").time())

        s_date = e_date = selected_dates[0] if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 1 else selected_dates[0] if isinstance(selected_dates, (list, tuple)) else selected_dates
        if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2: s_date, e_date = selected_dates
        
        start_date_str = f"{s_date.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M')}"
        end_date_str = f"{e_date.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M')}"
        st.info(f"📍 지정 일정: **{start_date_str} ~ {end_date_str}**")

        st.markdown("---")
        st.subheader("📊 실시간 대여 현황")
        active_rentals_status = df_rental[df_rental["승인상태"] == "대여중"]
        if active_rentals_status.empty: 
            st.info("현재 대여 중인 장비가 없습니다.")
        else: 
            st.dataframe(active_rentals_status[["신청ID", "품명", "규격", "이름", "대여날짜", "반납일자"]], use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("👤 1. 신청인 정보 입력")
        name = st.text_input("신청인 이름", placeholder="홍길동", key="input_name")
        student_id = st.text_input("학번", placeholder="20261234", key="input_student_id")
        phone = st.text_input("연락처", placeholder="010-XXXX-XXXX", key="input_phone")
        professor = st.text_input("담당 교수명", placeholder="김교수", key="input_professor")
        course_name = st.text_input("교과명", placeholder="예: 영상제작기초", key="input_course")
        shooting_loc = st.text_input("📍 촬영 장소", placeholder="예: 스튜디오 A", key="input_location")
        
        st.markdown("---")
        st.subheader("🛒 2. 대여 품목 고르기")
        extra_items = st.text_input("🎒 기타 기자재", placeholder="예: 삼각대 2개", key="input_extra")

        df_avail_copy = df_equip[df_equip["현재상태"] == "대여가능"].copy()
        if df_avail_copy.empty:
            st.warning("⚠️ 대여 가능한 재고가 없습니다.")
        else:
            df_avail_copy["품명_clean"] = df_avail_copy["품명"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
            df_avail_copy["규격_clean"] = df_avail_copy["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
            df_grouped_avail = df_avail_copy.groupby(["품명_clean", "규격_clean"]).size().reset_index(name="가능수량")
            df_grouped_avail.insert(0, "선택", False)
            df_grouped_avail["신청수량"] = 1

            edited_avail = st.data_editor(df_grouped_avail, column_config={"선택": st.column_config.CheckboxColumn("체크", default=False), "품명_clean": "품명", "규격_clean": "규격", "가능수량": "재고 수량", "신청수량": st.column_config.NumberColumn("신청 수량", min_value=1, step=1)}, disabled=["품명_clean", "규격_clean", "가능수량"], hide_index=True, use_container_width=True)

            if st.button("🛒 선택한 항목 장바구니 담기", use_container_width=True):
                selected_items = edited_avail[edited_avail["선택"] == True]
                if selected_items.empty: st.warning("⚠️ 장바구니에 담을 항목을 체크해주세요.")
                else:
                    success_count = 0
                    for _, row in selected_items.iterrows():
                        p_c, s_c, req_qty, max_qty = row["품명_clean"], row["규격_clean"], row["신청수량"], row["가능수량"]
                        already_in_cart = sum(item["수량"] for item in st.session_state.cart if item["품명_clean"] == p_c and item["규격_clean"] == s_c)
                        if req_qty > max_qty - already_in_cart:
                            st.error(f"❌ {p_c} 항목 초과")
                            continue
                        found = False
                        for item in st.session_state.cart:
                            if item["품명_clean"] == p_c and item["규격_clean"] == s_c:
                                item["수량"] += req_qty
                                found = True
                                break
                        if not found: st.session_state.cart.append({"품명_clean": p_c, "규격_clean": s_c, "수량": req_qty})
                        success_count += 1
                    if success_count > 0:
                        st.toast(f"{success_count}개 품목 추가!", icon="🛒")
                        st.rerun()

        if st.session_state.cart:
            st.markdown("### 📋 내 장바구니")
            st.dataframe(pd.DataFrame(st.session_state.cart).rename(columns={"품명_clean":"품명", "규격_clean":"규격", "수량":"담은수량"}), use_container_width=True, hide_index=True)
            col_clear, col_submit = st.columns(2)
            with col_clear:
                if st.button("❌ 전체 비우기", use_container_width=True): 
                    st.session_state.cart = []
                    st.rerun()
            with col_submit:
                if st.button("🚀 최종 대여 신청 제출", type="primary", use_container_width=True):
                    if not name.strip() or not student_id.strip(): st.error("❌ 신청자 이름과 학번을 꼭 채워주세요.")
                    else:
                        prefix = f"REQ-{datetime.today().strftime('%Y%m')}-"
                        same_month_reqs = df_rental[df_rental["신청ID"].astype(str).str.startswith(prefix, na=False)]
                        new_num = "001" if same_month_reqs.empty else f"{max([int(rid.split('-')[-1]) for rid in same_month_reqs['신청ID'] if rid.split('-')[-1].isdigit()] + [0]) + 1:03d}"
                        new_req_id = prefix + new_num
                        new_rows, stock_error = [], False

                        for cart_item in st.session_state.cart:
                            p_c, s_c, qty = cart_item["품명_clean"], cart_item["규격_clean"], cart_item["수량"]
                            matching_items = df_equip[(df_equip["현재상태"] == "대여가능") & (df_equip["품명"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip() == p_c) & (df_equip["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip() == s_c)].head(qty)
                            if len(matching_items) < qty: stock_error = True; break
                            for _, item in matching_items.iterrows():
                                new_rows.append({"신청ID": new_req_id, "장비ID": item["장비ID"], "품명": item["품명"], "규격": item["규격"], "이름": name.strip(), "학번": student_id.strip(), "연락처": phone.strip(), "담당교수": professor.strip(), "교과명": course_name.strip() or "-", "촬영장소": shooting_loc.strip() or "-", "기타기자재": extra_items.strip() or "-", "대여날짜": start_date_str, "반납일자": end_date_str, "승인상태": "승인대기"})
                                df_equip.loc[df_equip["장비ID"] == item["장비ID"], "현재상태"] = "승인대기"

                        if stock_error: st.error("❌ 재고 변동 발생")
                        else:
                            if df_rental.empty or df_rental["품명"].iloc[0] == "":
                                df_rental = pd.DataFrame(new_rows)
                            else:
                                df_rental = pd.concat([df_rental, pd.DataFrame(new_rows)], ignore_index=True)
                            
                            save_data(df_equip, df_rental)
                            st.session_state.cart = []
                            st.session_state.clear_inputs = True
                            st.session_state.submit_success = True
                            st.rerun()

# --- 3. 대여 신청 현황 (팝업 기반 완벽한 A4 인쇄 + 접수처 푸터 구현) ---
elif menu == "대여 신청 현황":
    st.header("📋 기자재 대여 신청 현황")
    if df_rental.empty or df_rental["품명"].iloc[0] == "":
        st.info("현재 대여 및 대기 중인 신청 내역이 없습니다.")
    else:
        active_rentals = df_rental[~df_rental["승인상태"].isin(["반납완료", "승인거절"])].copy()
        display_rental = active_rentals.sort_values(by=["신청ID", "장비ID"]).copy()
        is_duplicate = display_rental.duplicated(subset=["신청ID"])
        cols_to_merge = [
            "신청ID", "이름", "학번", "연락처", "담당교수", 
            "교과명", "촬영장소", "기타기자재", "대여날짜", "반납일자"
        ]
        
        for col in cols_to_merge:
            if col in display_rental.columns:
                display_rental[col] = display_rental[col].astype(str)
                display_rental.loc[is_duplicate, col] = ""

        if not is_admin:
            display_rental = display_rental.drop(columns=["학번", "연락처"], errors="ignore")
            st.caption("🔒 학생들의 개인정보 보호를 위해 '학번' 및 '연락처'는 관리자 로그인 시에만 조회됩니다.")
        else:
            st.caption("🔓 관리자 모드: 모든 신청인의 정보가 정상 노출됩니다.")
            
        st.dataframe(display_rental, use_container_width=True, hide_index=True)
        st.markdown("---")

        if is_admin:
            st.subheader("🔓 관리자 전용 - 개별 대여 승인 및 거절 처리")
            pending_rentals = df_rental[df_rental["승인상태"].str.strip().isin(["대기중", "승인대기", "대기"])].copy()
            if pending_rentals.empty:
                st.success("✅ 현재 승인 대기 중인 신청 품목이 없습니다.")
            else:
                st.markdown("**[ 대기 중인 상세 장비 목록 ] - 승인 또는 거절할 장비의 체크박스를 선택하세요.**")
                select_all_pending = st.checkbox("☑️ 표 전체 선택 / 해제", key="select_all_pending")
                pending_rentals.insert(0, "선택", select_all_pending)
                edited_pending = st.data_editor(pending_rentals[["선택", "신청ID", "이름", "장비ID", "품명", "규격", "대여날짜", "반납일자"]], column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)}, hide_index=True, use_container_width=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("⭕ 선택한 장비 승인하기", type="primary", use_container_width=True):
                        selected_pending = edited_pending[edited_pending["선택"] == True]
                        if not selected_pending.empty:
                            target_ids = selected_pending["장비ID"].tolist()
                            df_rental.loc[df_rental["장비ID"].isin(target_ids), "승인상태"] = "대여중"
                            df_equip.loc[df_equip["장비ID"].isin(target_ids), "현재상태"] = "대여중"
                            save_data(df_equip, df_rental)
                            st.success(f"🎉 장비 {len(target_ids)}대의 대여가 개별 승인되었습니다.")
                            st.rerun()
                        else:
                            st.warning("승인할 장비를 표에서 먼저 체크해주세요.")
                with col_btn2:
                    if st.button("❌ 선택한 장비 거절하기", use_container_width=True):
                        selected_pending = edited_pending[edited_pending["선택"] == True]
                        if not selected_pending.empty:
                            target_ids = selected_pending["장비ID"].tolist()
                            
                            df_rental.loc[df_rental["장비ID"].isin(target_ids), "승인상태"] = "승인거절"
                            
                            df_rental["학번"] = df_rental["학번"].astype(str)
                            df_rental["연락처"] = df_rental["연락처"].astype(str)
                            df_rental.loc[df_rental["장비ID"].isin(target_ids), "학번"] = "파기됨"
                            df_rental.loc[df_rental["장비ID"].isin(target_ids), "연락처"] = "파기됨"
                            
                            df_equip.loc[df_equip["장비ID"].isin(target_ids), "현재상태"] = "대여가능"
                            
                            save_data(df_equip, df_rental)
                            st.error(f"🚫 장비 {len(target_ids)}대의 대여가 거절되었으며, 개인정보가 파기되었습니다.")
                            st.rerun()
                        else:
                            st.warning("거절할 장비를 표에서 먼저 체크해주세요.")
            
            st.markdown("---")
            st.subheader("🖨️ 관리자 전용 - 신청서 A4 인쇄")
            valid_rental_ids = df_rental[df_rental["신청ID"] != ""]["신청ID"].unique().tolist()
            if not valid_rental_ids:
                st.info("출력 가능한 대여 신청 내역이 없습니다.")
            else:
                selected_print_id = st.selectbox("🖨️ 출력 서류를 선택하세요", valid_rental_ids)
                if selected_print_id:
                    print_rows = df_rental[df_rental["신청ID"] == selected_print_id]
                    if not print_rows.empty:
                        p_first = print_rows.iloc[0]
                        
                        item_counts = print_rows.groupby(["품명", "규격"]).size().reset_index(name="수량")
                        items_html_list = []
                        for _, r in item_counts.iterrows():
                            items_html_list.append(get_item_icon_html(r['품명'], r['규격'], r['수량']))
                        items_html_str = "".join(items_html_list)
                        total_items = item_counts['수량'].sum()
                        
                        # ✨ Streamlit 화면 렌더링용 미리보기 마크다운
                        st.markdown("<div class='printable-area'>위 선택한 신청서가 아래 버튼을 통해 A4 서식으로 출력됩니다. (팝업 차단을 해제해 주세요)</div>", unsafe_allow_html=True)
                        
                        # ✨ 화면에는 표시되지 않지만, JS가 읽어갈 완벽한 A4 데이터 (id 부여)
                        # 1번 이미지(접수처/CAU 로고)를 HTML로 완벽히 복제하여 포함시켰습니다.
                        html_content = f"""
                        <div id='print-source-data' style='display:none;'>
                            <h1 style='text-align:center; margin-bottom:30px; font-size:28px;'>글로벌예술학부 기자재 대여 신청서</h1>
                            <table style='width:100%; border-collapse:collapse; border:2px solid black; font-size:14px;'>
                                <tr>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; width:15%; text-align:center;'>신청ID</th>
                                    <td colspan='3' style='border:1px solid black; padding:10px; font-weight:bold; color:#004b87;'>{p_first['신청ID']}</td>
                                </tr>
                                <tr>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; width:15%; text-align:center;'>성명</th>
                                    <td style='border:1px solid black; padding:10px; width:35%;'>{p_first['이름']}</td>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; width:15%; text-align:center;'>학번</th>
                                    <td style='border:1px solid black; padding:10px; width:35%;'>{p_first['학번']}</td>
                                </tr>
                                <tr>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; text-align:center;'>연락처</th>
                                    <td style='border:1px solid black; padding:10px;'>{p_first['연락처']}</td>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; text-align:center;'>담당교수</th>
                                    <td style='border:1px solid black; padding:10px;'>{p_first['담당교수']}</td>
                                </tr>
                                <tr>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; text-align:center;'>교과명</th>
                                    <td style='border:1px solid black; padding:10px;'>{p_first['교과명']}</td>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; text-align:center;'>촬영장소</th>
                                    <td style='border:1px solid black; padding:10px;'>{p_first['촬영장소']}</td>
                                </tr>
                                <tr>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; text-align:center;'>대여기간</th>
                                    <td colspan='3' style='border:1px solid black; padding:10px;'><b>{p_first['대여날짜']}</b> ~ <b>{p_first['반납일자']}</b></td>
                                </tr>
                                <tr>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; text-align:center;'>대여 품목<br><span style='font-size:0.8em; font-weight:normal; color:#555;'>(총 {total_items}대)</span></th>
                                    <td colspan='3' style='border:1px solid black; padding:10px;'>
                                        <div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;'>{items_html_str}</div>
                                    </td>
                                </tr>
                                <tr>
                                    <th style='border:1px solid black; padding:10px; background-color:#f2f2f2; text-align:center;'>기타 기자재</th>
                                    <td colspan='3' style='border:1px solid black; padding:10px;'>{p_first['기타기자재']}</td>
                                </tr>
                            </table>
                            <div style='margin-top:20px; font-size:12px; line-height:1.6; text-align:left; border:1px solid #000; padding:15px;'>
                                <p style='font-weight:bold; margin:0 0 5px 0;'>◎ 준수사항</p>
                                <ol style='margin:0 0 10px 0; padding-left:20px;'>
                                    <li><b>기자재 이용 규정을 숙지 및 준수해야 함</b></li>
                                    <li><b>책임사항:</b> 사용자의 부주의로 인한 기자재의 손상, 분실에 대해서는 사용자가 복구, 또는 변상해야 합니다. 반납 시 기자재의 이상유무를 확인 받으시기 바랍니다.</li>
                                    <li><b>금지사항:</b> 강의 및 실습 이외의 개인적인 용도의 사용</li>
                                    <li><b>관련자료제출:</b></li>
                                </ol>
                                <p style='font-weight:bold; margin:10px 0 5px 0;'>◎ 연체 및 책임사항 불이행에 대한 조치</p>
                                <ol style='margin:0; padding-left:20px;'>
                                    <li><b>장기간의 연체, 손상 및 분실에 대한 복구 또는 변상 불이행:</b> 반납 시까지 또는 복구 및 변상 완료 시까지 제 급여의 지급 보류, 제증명 발급 보류, 학위증서의 전달이 보류될 수 있습니다.</li>
                                    <li><b>용도 이외의 사용:</b> 이후 기자재 대여 금함.</li>
                                </ol>
                            </div>
                            <div style='margin-top:20px; text-align:center; font-size:15px; font-weight:bold;'>
                                <p>위의 준수사항을 수락하며 기자재의 대여를 신청합니다.</p>
                            </div>
                            <div style='margin-top:30px; text-align:center; font-size:14px;'>
                                <span style='margin-right:20px;'>20</span><span style='margin-right:20px;'>년</span><span style='margin-right:20px;'>월</span><span>일</span>
                            </div>
                            <div style='margin-top:30px; text-align:right; font-size:15px; padding-right:50px;'>
                                <p style='margin-bottom:15px;'>신청인 : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인/서명)</p>
                                <p>승인자 : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인/서명)</p>
                            </div>
                            
                            <div style='margin-top: 50px; border-top: 2px dashed #000; padding-top: 20px; display: flex; justify-content: space-between; align-items: flex-end; font-family: "Malgun Gothic", sans-serif;'>
                                <div style='text-align: left; line-height: 1.4;'>
                                    <p style='margin: 0; font-size: 14px; font-weight: 800;'>다빈치캠퍼스 신청서 접수 및 문의</p>
                                    <p style='margin: 8px 0 0 0; font-size: 16px; font-weight: 500;'>1. e-mail: nalsound@cau.ac.kr &nbsp;&nbsp;&nbsp;&nbsp; 2. FAX: 031)675-7157 &nbsp;&nbsp;&nbsp;&nbsp; 이창호 (내선 3352)</p>
                                    <p style='margin: 5px 0 0 0; font-size: 28px; font-weight: 600; letter-spacing: -1px;'>예술대학 글로벌예술학부 &nbsp;<span style='font-weight: 300; font-size:26px;'>|</span>&nbsp; 805관 6101호</p>
                                </div>
                                <div style='text-align: right; padding-bottom: 5px;'>
                                    <h1 style='margin: 0; font-size: 48px; color: #0056a9; font-weight: 900; font-style: italic; font-family: "Arial Black", sans-serif; letter-spacing: -2px;'>CAU</h1>
                                </div>
                            </div>
                        </div>
                        """
                        st.markdown(html_content, unsafe_allow_html=True)
                        
                        # ✨ 자바스크립트를 이용해 숨겨진 html 내용을 새 창(팝업)에 띄우고 인쇄하도록 처리 (스트림릿 레이아웃이 섞이는 문제 완벽 차단)
                        js_print_script = """
                        <div>
                            <button onclick="triggerPrint()" style="padding:12px 24px; font-size:16px; font-weight:bold; cursor:pointer; background-color:#2e7d32; color:white; border:none; border-radius:8px; width:100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🖨️ 해당 신청서 A4 용지 인쇄하기 (Ctrl+P)</button>
                        </div>
                        <script>
                            function triggerPrint() {
                                // 부모 문서(Streamlit 전체 화면)에서 데이터 HTML 추출
                                const printData = window.parent.document.getElementById('print-source-data').innerHTML;
                                
                                // 새 창 열기 (인쇄 전용 팝업)
                                const printWindow = window.open('', '_blank', 'width=900,height=1000');
                                
                                // 새 창에 문서 작성 (CSS 스타일 포함)
                                printWindow.document.write('<html><head><title>기자재 대여 신청서 인쇄</title>');
                                printWindow.document.write('<style>');
                                printWindow.document.write('@page { size: A4; margin: 15mm; }');
                                printWindow.document.write('body { font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; color: #000; background-color: #fff; margin: 0; padding: 0; }');
                                printWindow.document.write('table { border-collapse: collapse; width: 100%; border: 2px solid black; }');
                                printWindow.document.write('th, td { border: 1px solid black; padding: 10px; }');
                                printWindow.document.write('</style>');
                                printWindow.document.write('</head><body>');
                                printWindow.document.write(printData);
                                printWindow.document.write('</body></html>');
                                
                                // 문서 닫고 포커스 후 인쇄 다이얼로그 호출
                                printWindow.document.close();
                                printWindow.focus();
                                
                                // 브라우저가 화면을 렌더링할 약간의 딜레이 확보
                                setTimeout(function() {
                                    printWindow.print();
                                    printWindow.close();
                                }, 300);
                            }
                        </script>
                        """
                        st.components.v1.html(js_print_script, height=70)

# --- 4. 품목별 대여 통계 ---
elif menu == "품목별 대여 통계":
    st.header("📈 품목별 대여 통계")
    
    valid_rentals = df_rental[df_rental["품명"] != ""]
    
    if valid_rentals.empty:
        st.info("💡 아직 누적된 대여 기록이 없어 통계를 산출할 수 없습니다.")
    else:
        st.markdown("학생들이 가장 많이 대여한 인기 기자재 순위를 확인하세요!")
        stats_df = valid_rentals.groupby(["품명", "규격"]).size().reset_index(name="누적 대여 횟수")
        stats_df = stats_df.sort_values(by="누적 대여 횟수", ascending=False).reset_index(drop=True)
        
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        with col2:
            st.bar_chart(stats_df.set_index("규격")["누적 대여 횟수"])

# --- 5. 기자재 반납 처리 (관리자 전용 메뉴로 이동) ---
elif menu == "기자재 반납 처리":
    st.header("🔄 기자재 반납 처리 (관리자 전용)")
    active_rentals = df_rental[df_rental["승인상태"] == "대여중"].copy()
    if active_rentals.empty: 
        st.info("✅ 현재 대여 중이어서 반납 처리할 장비가 없습니다.")
    else:
        st.markdown("**[ 대여 중인 상세 장비 목록 ] - 반납된 장비의 체크박스를 선택하세요.**")
        select_all_return = st.checkbox("☑️ 표 전체 선택 / 해제", key="select_all_return")
        active_rentals.insert(0, "선택", select_all_return)
        edited_active = st.data_editor(active_rentals[["선택", "신청ID", "이름", "장비ID", "품명", "규격", "반납일자"]], column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)}, hide_index=True, use_container_width=True)

        if st.button("👍 선택한 장비 반납 확인", type="primary"):
            selected_to_return = edited_active[edited_active["선택"] == True]
            if not selected_to_return.empty:
                target_ids = selected_to_return["장비ID"].tolist()
        
                df_rental.loc[df_rental["장비ID"].isin(target_ids), "승인상태"] = "반납완료"
                
                df_rental["학번"] = df_rental["학번"].astype(str)
                df_rental["연락처"] = df_rental["연락처"].astype(str)
                
                df_rental.loc[df_rental["장비ID"].isin(target_ids), "학번"] = "파기됨"
                df_rental.loc[df_rental["장비ID"].isin(target_ids), "연락처"] = "파기됨"

                df_equip.loc[df_equip["장비ID"].isin(target_ids), "현재상태"] = "대여가능"
                
                save_data(df_equip, df_rental)
                st.success(f"✅ 장비 {len(target_ids)}대의 반납 처리 및 개인정보 파기가 완료되었습니다.")
                st.rerun()
            else: 
                st.warning("반납 처리할 장비를 표에서 먼저 체크해주세요.")

# --- 6. 장비 관리 (관리자 전용) ---
elif menu == "⚙️ 장비 관리 (관리자 전용)":
    if not is_admin:
        st.warning("접근 권한이 없습니다. 사이드바에서 로그인해주세요.")
        st.stop()
        
    st.header("⚙️ 장비 일괄 관리 및 신규 등록")
    
    st.subheader("🛠️ 장비 상태 일괄/수동 변경")
    st.caption("💡 표 안의 **'현재상태 ✏️'** 또는 **'자산번호 ✏️'** 칸을 더블클릭하면 데이터를 바로 수정할 수 있습니다.")
    
    cols_order = ["장비ID", "품명", "규격", "현재상태", "기자재자산번호", "비고"]
    
    edited_equip_df = st.data_editor(
        df_equip[cols_order],
        column_config={
            "장비ID": st.column_config.TextColumn("장비ID", disabled=True),
            "품명": st.column_config.TextColumn("품명", disabled=True),
            "규격": st.column_config.TextColumn("규격", disabled=True),
            "현재상태": st.column_config.SelectboxColumn(
                "현재상태 ✏️",
                help="클릭하여 장비의 상태를 변경하세요",
                options=["대여가능", "대여중", "고장", "수리중", "승인대기"],
                required=True
            ),
            "기자재자산번호": st.column_config.TextColumn(
                "자산번호 ✏️", 
                help="기자재의 자산번호를 입력하세요 (예: 202102479-001-00)"
            ),
            "비고": st.column_config.TextColumn("비고 ✏️", disabled=False)
        },
        hide_index=True,
        use_container_width=True,
        height=600  
    )

    if st.button("💾 변경된 상태 한 번에 저장하기", type="primary"):
        if not df_equip[cols_order].equals(edited_equip_df):
            df_equip = edited_equip_df.copy()
            save_data(df_equip, df_rental)
            st.success("✅ 장비 정보가 성공적으로 일괄 업데이트되었습니다!")
            st.rerun()
        else:
            st.info("💡 변경된 장비 정보가 없습니다.")
            
    st.markdown("---")
    
    st.subheader("➕ 신규 기자재 추가 등록")
    with st.form("add_equipment_form", clear_on_submit=True):
        new_name = st.text_input("📦 품명 (예: 캠코더, 미러리스 카메라)")
        new_spec = st.text_input("📐 규격 (예: PWX-Z90, Sony FX3)")
        new_asset_no = st.text_input("🏷️ 기자재자산번호 (선택)", placeholder="예: 202102479-001-00")
        new_remarks = st.text_input("📝 비고")
        if st.form_submit_button("🚀 새 장비 등록하기"):
            if not new_name.strip():
                st.error("❌ 품명은 필수 입력 항목입니다.")
            else:
                prefix = "EQ-AUTO-"
                auto_ids = df_equip[df_equip["장비ID"].str.startswith(prefix, na=False)]
                new_num = f"{auto_ids['장비ID'].str.split('-').str[-1].astype(int).max() + 1:04d}" if not auto_ids.empty else "0001"
                generated_id = prefix + new_num
                
                new_equip_row = {
                    "장비ID": generated_id, 
                    "품명": new_name.strip(), 
                    "규격": new_spec.strip() if new_spec.strip() else "-", 
                    "현재상태": "대여가능", 
                    "기자재자산번호": new_asset_no.strip() if new_asset_no.strip() else "-",
                    "비고": new_remarks.strip() if new_remarks.strip() else "-"
                }
                
                df_equip = pd.concat([df_equip, pd.DataFrame([new_equip_row])], ignore_index=True)
                save_data(df_equip, df_rental)
                st.success(f"🎉 등록 성공! 자동 발급된 ID: [{generated_id}]")
                st.rerun()
