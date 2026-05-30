import os
import io
import re
import base64
from datetime import datetime
import pandas as pd
import streamlit as st
import altair as alt  
from streamlit_gsheets import GSheetsConnection 
from PIL import Image

# ==========================================
# 🚨 구글 스프레드시트 주소
# ==========================================
EQUIPMENT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1DkU-1hCQuTApnnFxfZAh1MXulrD6HxPHY4P1QjhqJq0/edit?gid=1121757229#gid=1121757229"
RENTAL_SHEET_URL = "https://docs.google.com/spreadsheets/d/1hV8oaUlEIEA4rF6peg083Td_1cNZbWbl6BCcEkRpkT8/edit?gid=183591911#gid=183591911"

# --- 공지사항 설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTICE_FILE = os.path.join(BASE_DIR, "notice.txt")

DEFAULT_NOTICE = """### 📢 글로벌예술학부 기자재 대여 시스템 이용 안내

안녕하세요. 기자재실입니다. 
원활하고 안전한 기자재 대여 및 관리를 위해 아래 안내 사항을 반드시 숙지해 주시기 바랍니다.

**1. 대여 신청 기한 및 시스템 이용 안내**
* 기자재 대여 신청은 대여 희망일 기준 **최소 3일 전 신청을 원칙**으로 합니다.
* 접수된 기자재 대여 신청서는 **매일 오전 10시와 오후 2시**에 일괄적으로 확인 및 승인 처리됩니다.
* **대여 및 반납 시간은 09:00~17:00까지**입니다.
* **기자재 대여(수령) 시, 본인 확인을 위해 반드시 실물 학생증 또는 모바일 학생증을 지참하여 제시해야 합니다.** (미지참 시 대여 불가)
* 본 시스템은 PC 웹 환경에 최적화되어 있으므로, 원활한 신청 및 화면 조회를 위해 **컴퓨터 및 노트북에서 접속하는 것을 권장**합니다.

**2. 신청서 외 장비 당일 현장 추가 불가**
* 시스템에 제출된 **신청서에 기재된 품목 외에, 대여 당일 현장에서 즉흥적으로 장비를 추가하는 것은 절대 불가**합니다.

**3. 기자재 이용 규정 숙지 의무**
* 좌측 메뉴의 **[기자재 이용 규정]**을 반드시 정독해 주시기 바랍니다.

**4. 개인정보 수집 동의 및 면책 안내**
* 대여 신청 시 입력하시는 학번과 연락처는 대여 중 미반납 또는 긴급 상황 발생 시 용도로만 활용되며, 반납 완료 시 즉시 파기됩니다.

우리 모두의 소중한 기자재입니다. 안전하고 올바른 이용을 부탁드립니다. 감사합니다."""

def load_data():
    """구글 스프레드시트에서 데이터를 불러옵니다."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        df_equip = conn.read(spreadsheet=EQUIPMENT_SHEET_URL, ttl=300)
        df_rental = conn.read(spreadsheet=RENTAL_SHEET_URL, ttl=300)

        if df_equip is None or df_equip.empty:
            df_equip = pd.DataFrame(columns=["장비ID", "품명", "규격", "현재상태", "기자재자산번호", "비고", "이미지URL"])
        if df_rental is None or df_rental.empty:
            df_rental = pd.DataFrame(columns=["신청ID", "장비ID", "품명", "규격", "이름", "학번", "연락처", "담당교수", "교과명", "촬영장소", "기타기자재", "대여날짜", "반납일자", "승인상태"])

        required_equip_cols = ["장비ID", "품명", "규격", "현재상태", "기자재자산번호", "비고", "이미지URL"]
        for col in required_equip_cols:
            if col not in df_equip.columns:
                df_equip[col] = ""

        required_rental_cols = ["신청ID", "장비ID", "품명", "규격", "이름", "학번", "연락처", "담당교수", "교과명", "촬영장소", "기타기자재", "대여날짜", "반납일자", "승인상태"]
        for col in required_rental_cols:
            if col not in df_rental.columns:
                df_rental[col] = ""

        for df in [df_equip, df_rental]:
            for col in df.columns:
                df[col] = df[col].astype(str)
                df[col] = df[col].replace(["nan", "None", "<NA>", "NaT"], "").str.strip()
                
        return df_equip, df_rental
    except Exception as e:
        st.error(f"❌ 구글 시트 연동 오류: {e}")
        st.stop()

def save_data(df_equip, df_rental):
    """데이터를 구글 스프레드시트에 저장합니다."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(spreadsheet=EQUIPMENT_SHEET_URL, data=df_equip)
        conn.update(spreadsheet=RENTAL_SHEET_URL, data=df_rental)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ 구글 시트 저장 오류: {e}")

def get_item_icon_html(name, spec, qty):
    """장비명 기반 텍스트 아이콘 생성"""
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
        
    return f"<div style='background-color:#f8f9fa; padding:6px 6px; border-radius:4px; border:1px solid #e9ecef; font-size:12px; word-break:keep-all; line-height:1.4;'><b>{icon} {spec}</b> <span style='font-size:10px; color:#555;'>({name})</span> <span style='font-weight:bold; color:#d32f2f; margin-left:4px; white-space:nowrap;'>x {qty}대</span></div>"

# ==========================================
# --- 스팀릿 웹 페이지 설정 ---
st.set_page_config(page_title="기자재 관리 시스템", layout="wide")

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
if st.sidebar.button("🔄 최신 데이터 새로고침", help="구글 시트의 최신 데이터를 즉시 불러옵니다.", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
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

# --- 0. 공지사항 ---
if menu == "공지사항":
    st.header("📢 공지사항")
    if is_admin:
        new_notice = st.text_area("📝 공지사항 내용 수정", value=current_notice, height=400)
        if st.button("💾 공지사항 저장 및 적용하기", type="primary"):
            with open(NOTICE_FILE, "w", encoding="utf-8") as f:
                f.write(new_notice)
            st.success("✅ 업데이트 성공!")
            st.rerun()
    else:
        st.success(current_notice)

# --- 0-1. 기자재 이용 규정 ---
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
    6. 연출자가 본교 학생이 아닌 경우.
    (단, 촬영자에 한해서 본교의 졸업생인 경우 전임 교수 승인 하에 가능)
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
        df_summary_input["품명_clean"] = df_summary_input["품명"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        df_summary_input["규격_clean"] = df_summary_input["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        
        df_summary = (
            df_summary_input.groupby(["품명_clean", "규격_clean"])
            .agg(
                총보유수량=("장비ID", "count"),
                대여가능=("현재상태", lambda x: (x == "대여가능").sum()),
                승인대기=("현재상태", lambda x: (x == "승인대기").sum()),
                대여중=("현재상태", lambda x: (x == "대여중").sum()),
                점검및고장=("현재상태", lambda x: x.isin(["고장", "수리중"]).sum()),
                이미지URL=("이미지URL", lambda x: next((u for u in x if str(u).strip() and str(u).strip().lower() not in ["nan", "none", "<na>"] and (str(u).startswith("http") or str(u).startswith("data:"))), ""))
            ).reset_index()
        )
        
        def get_final_image_url(row):
            val = str(row["이미지URL"]).strip()
            if val.startswith("http") or val.startswith("data:"):
                return val
            encoded_spec = str(row["규격_clean"]).replace(" ", "+")
            return f"https://via.placeholder.com/150/EAEAEA/333333?text={encoded_spec}"

        df_summary["사진"] = df_summary.apply(get_final_image_url, axis=1)
        
        df_summary = df_summary.rename(columns={"품명_clean": "품명", "규격_clean": "규격"})
        cols = ["사진", "품명", "규격", "총보유수량", "대여가능", "승인대기", "대여중", "점검및고장"]
        df_summary = df_summary[cols]
        
        st.dataframe(
            df_summary, 
            column_config={
                "사진": st.column_config.ImageColumn("미리보기", help="구글 시트에 등록된 사진")
            },
            use_container_width=True, 
            hide_index=True
        )

    st.markdown("---")
    st.subheader("📋 개별 장비 상세 현황")
    filter_option = st.radio("필터 선택", ["전체 장비 보기", "대여 가능 장비만 보기"], horizontal=True)
    display_df = df_equip[df_equip["현재상태"] == "대여가능"].copy() if filter_option == "대여 가능 장비만 보기" else df_equip.copy()
    st.dataframe(display_df.drop(columns=["이미지URL"], errors="ignore"), use_container_width=True, hide_index=True)

# --- 2. 신규 대여 신청 ---
elif menu == "신규 대여 신청":
    if st.session_state.get("submit_success"):
        st.success("🎉 대여 신청이 성공적으로 제출되었습니다!")
        st.session_state.submit_success = False

    if st.session_state.get("clear_inputs"):
        for k in ["input_name", "input_student_id", "input_phone", "input_professor", "input_course", "input_location", "input_extra"]:
            if k in st.session_state: st.session_state[k] = ""
        st.session_state.clear_inputs = False

    st.header("📝 신규 대여 신청서 작성")
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.subheader("📅 대여 일정 및 시간 선택")
        selected_dates = st.date_input("📆 대여 시작/반납 예정일", value=(datetime.today().date(), datetime.today().date()))
        col_time1, col_time2 = st.columns(2)
        with col_time1: start_time = st.time_input("⏰ 시작 시간", value=datetime.strptime("09:30", "%H:%M").time())
        with col_time2: end_time = st.time_input("⏰ 반납 시간", value=datetime.strptime("15:30", "%H:%M").time())

        s_date = e_date = selected_dates[0] if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 1 else selected_dates[0] if isinstance(selected_dates, (list, tuple)) else selected_dates
        if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2: s_date, e_date = selected_dates
        
        start_date_str = f"{s_date.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M')}"
        end_date_str = f"{e_date.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M')}"
        
        st.markdown("---")
        st.subheader("📊 실시간 대여 현황")
        active_rentals_status = df_rental[df_rental["승인상태"] == "대여중"]
        if active_rentals_status.empty: 
            st.info("현재 대여 중인 장비가 없습니다.")
        else: 
            st.dataframe(active_rentals_status[["신청ID", "품명", "규격", "이름"]], use_container_width=True, hide_index=True)

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
        extra_items = st.text_input("🎒 기타 기자재", placeholder="예) 삼각대 1, SD카드 2", key="input_extra")

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
                for _, row in selected_items.iterrows():
                    p_c, s_c, req_qty = row["품명_clean"], row["규격_clean"], row["신청수량"]
                    found = False
                    for item in st.session_state.cart:
                        if item["품명_clean"] == p_c and item["규격_clean"] == s_c:
                            item["수량"] += req_qty
                            found = True
                    if not found: st.session_state.cart.append({"품명_clean": p_c, "규격_clean": s_c, "수량": req_qty})
                st.rerun()

        if st.session_state.cart:
            st.markdown("### 📋 내 장바구니")
            st.dataframe(pd.DataFrame(st.session_state.cart).rename(columns={"품명_clean":"품명", "규격_clean":"규격", "수량":"수량"}), hide_index=True)
            if st.button("🚀 최종 대여 신청 제출", type="primary", use_container_width=True):
                if not name.strip() or not student_id.strip(): st.error("❌ 이름과 학번을 입력해주세요.")
                else:
                    prefix = f"REQ-{datetime.today().strftime('%Y%m')}-"
                    same_month = df_rental[df_rental["신청ID"].astype(str).str.startswith(prefix, na=False)]
                    new_num = f"{len(same_month) + 1:03d}"
                    new_req_id = prefix + new_num
                    new_rows = []

                    for cart_item in st.session_state.cart:
                        p_c, s_c, qty = cart_item["품명_clean"], cart_item["규격_clean"], cart_item["수량"]
                        matching = df_equip[(df_equip["현재상태"] == "대여가능") & (df_equip["품명"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip() == p_c) & (df_equip["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip() == s_c)].head(qty)
                        for _, item in matching.iterrows():
                            new_rows.append({"신청ID": new_req_id, "장비ID": item["장비ID"], "품명": item["품명"], "규격": item["규격"], "이름": name.strip(), "학번": student_id.strip(), "연락처": phone.strip(), "담당교수": professor.strip(), "교과명": course_name.strip(), "촬영장소": shooting_loc.strip(), "기타기자재": extra_items.strip(), "대여날짜": start_date_str, "반납일자": end_date_str, "승인상태": "승인대기"})
                            df_equip.loc[df_equip["장비ID"] == item["장비ID"], "현재상태"] = "승인대기"

                    df_rental = pd.concat([df_rental, pd.DataFrame(new_rows)], ignore_index=True) if not df_rental.empty else pd.DataFrame(new_rows)
                    save_data(df_equip, df_rental)
                    st.session_state.cart = []
                    st.session_state.submit_success = True
                    st.rerun()

# --- 3. 대여 신청 현황 (✨ A4 인쇄 출력 기능 완벽 복구됨) ---
elif menu == "대여 신청 현황":
    st.header("📋 기자재 대여 신청 현황")
    if df_rental.empty or df_rental["품명"].iloc[0] == "":
        st.info("신청 내역이 없습니다.")
    else:
        active_rentals = df_rental[~df_rental["승인상태"].isin(["반납완료", "승인거절"])].copy()
        st.dataframe(active_rentals, use_container_width=True, hide_index=True)

        if is_admin:
            st.subheader("🔓 관리자 전용 - 개별 대여 승인 및 거절 처리")
            pending = df_rental[df_rental["승인상태"].isin(["승인대기", "대기중"])].copy()
            if not pending.empty:
                pending.insert(0, "선택", False)
                edited_pending = st.data_editor(pending, hide_index=True, use_container_width=True)
                if st.button("⭕ 승인하기", type="primary"):
                    sel = edited_pending[edited_pending["선택"] == True]
                    if not sel.empty:
                        target_ids = sel["장비ID"].tolist()
                        df_rental.loc[df_rental["장비ID"].isin(target_ids), "승인상태"] = "대여중"
                        df_equip.loc[df_equip["장비ID"].isin(target_ids), "현재상태"] = "대여중"
                        save_data(df_equip, df_rental)
                        st.rerun()
                if st.button("❌ 거절하기"):
                    sel = edited_pending[edited_pending["선택"] == True]
                    if not sel.empty:
                        target_ids = sel["장비ID"].tolist()
                        df_rental.loc[df_rental["장비ID"].isin(target_ids), "승인상태"] = "승인거절"
                        df_rental.loc[df_rental["장비ID"].isin(target_ids), "학번"] = "파기됨"
                        df_rental.loc[df_rental["장비ID"].isin(target_ids), "연락처"] = "파기됨"
                        df_equip.loc[df_equip["장비ID"].isin(target_ids), "현재상태"] = "대여가능"
                        save_data(df_equip, df_rental)
                        st.rerun()

            st.markdown("---")
            st.subheader("🖨️ 관리자 전용 - 신청서 A4 인쇄 (팝업 전용)")
            
            valid_print_df = df_rental[~df_rental["승인상태"].isin(["승인거절", "반납완료"])].copy()
            valid_rental_ids = valid_print_df[valid_print_df["신청ID"] != ""]["신청ID"].unique().tolist()
            
            if not valid_rental_ids:
                st.info("출력 가능한 대여 신청 내역이 없습니다. (모두 파기되었거나 신청 내역이 없습니다)")
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

                        html_content = f"""
                        <div style="display: flex; flex-direction: column; min-height: 270mm; justify-content: space-between;">
                            <div>
                                <h1 style="text-align:center; margin:0 0 20px 0; font-size:26px;">글로벌예술학부 기자재 대여 신청서</h1>
                                <table style="width:100%; border-collapse:collapse; border:2px solid black; font-size:13px;">
                                    <tr>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; width:15%; text-align:center;">신청ID</th>
                                        <td colspan="3" style="border:1px solid black; padding:8px; font-weight:bold; color:#004b87;">{p_first['신청ID']}</td>
                                    </tr>
                                    <tr>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; width:15%; text-align:center;">성명</th>
                                        <td style="border:1px solid black; padding:8px; width:35%;">{p_first['이름']}</td>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; width:15%; text-align:center;">학번</th>
                                        <td style="border:1px solid black; padding:8px; width:35%;">{p_first['학번']}</td>
                                    </tr>
                                    <tr>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; text-align:center;">연락처</th>
                                        <td style="border:1px solid black; padding:8px;">{p_first['연락처']}</td>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; text-align:center;">담당교수</th>
                                        <td style="border:1px solid black; padding:8px;">{p_first['담당교수']}</td>
                                    </tr>
                                    <tr>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; text-align:center;">교과명</th>
                                        <td style="border:1px solid black; padding:8px;">{p_first['교과명']}</td>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; text-align:center;">촬영장소</th>
                                        <td style="border:1px solid black; padding:8px;">{p_first['촬영장소']}</td>
                                    </tr>
                                    <tr>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; text-align:center;">대여기간</th>
                                        <td colspan="3" style="border:1px solid black; padding:8px;"><b>{p_first['대여날짜']}</b> ~ <b>{p_first['반납일자']}</b></td>
                                    </tr>
                                    <tr>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; text-align:center;">대여 품목<br><span style="font-size:0.85em; font-weight:normal; color:#555;">(총 {total_items}대)</span></th>
                                        <td colspan="3" style="border:1px solid black; padding:8px;">
                                            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:4px;">{items_html_str}</div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <th style="border:1px solid black; padding:8px; background-color:#f2f2f2; text-align:center;">기타 기자재</th>
                                        <td colspan="3" style="border:1px solid black; padding:8px;">{p_first['기타기자재']}</td>
                                    </tr>
                                </table>
                            </div>
                            
                            <div style="margin-top: auto; padding-top: 20px;">
                                <div style="font-size:12px; line-height:1.5; text-align:left; border:1px solid #000; padding:10px;">
                                    <p style="font-weight:bold; margin:0 0 4px 0;">◎ 준수사항</p>
                                    <ol style="margin:0 0 8px 0; padding-left:20px;">
                                        <li><b>기자재 이용 규정을 숙지 및 준수해야 함</b></li>
                                        <li><b>책임사항:</b> 사용자의 부주의로 인한 기자재의 손상, 분실에 대해서는 사용자가 복구, 또는 변상해야 합니다. 반납 시 기자재의 이상유무를 확인 받으시기 바랍니다.</li>
                                        <li><b>금지사항:</b> 강의 및 실습 이외의 개인적인 용도의 사용</li>
                                    </ol>
                                    <p style="font-weight:bold; margin:8px 0 4px 0;">◎ 연체 및 책임사항 불이행에 대한 조치</p>
                                    <ol style="margin:0; padding-left:20px;">
                                        <li><b>장기간의 연체, 손상 및 분실에 대한 복구 또는 변상 불이행:</b> 반납 시까지 또는 복구 및 변상 완료 시까지 제 급여의 지급 보류, 제증명 발급 보류, 학위증서의 전달이 보류될 수 있습니다.</li>
                                        <li><b>용도 이외의 사용:</b> 이후 기자재 대여 금함.</li>
                                    </ol>
                                </div>
                                
                                <div style="margin-top:15px; text-align:center; font-size:14px; font-weight:bold;">
                                    <p>위의 준수사항을 수락하며 기자재의 대여를 신청합니다.</p>
                                </div>
                                
                                <div style="margin-top:15px; text-align:center; font-size:14px;">
                                    <span style="margin-right:20px;">20</span><span style="margin-right:20px;">년</span><span style="margin-right:20px;">월</span><span>일</span>
                                </div>
                                
                                <div style="margin-top:15px; text-align:right; font-size:14px; padding-right:50px;">
                                    <p style="margin-bottom:10px;">신청인 : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인/서명)</p>
                                    <p>승인자 : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인/서명)</p>
                                </div>
                                
                                <div style="margin-top: 15px; border-top: 2px dashed #000; padding-top: 15px; text-align: left; font-family: 'Malgun Gothic', sans-serif; line-height: 1.3;">
                                    <p style="margin: 0; font-size: 13px; font-weight: 800;">다빈치캠퍼스 신청서 접수 및 문의</p>
                                    <p style="margin: 5px 0 0 0; font-size: 14px; font-weight: 500;">1. e-mail: nalsound@cau.ac.kr &nbsp;&nbsp;&nbsp;&nbsp; 2. FAX: 031)675-7157 &nbsp;&nbsp;&nbsp;&nbsp; 이창호 (내선 3352)</p>
                                    <p style="margin: 5px 0 0 0; font-size: 24px; font-weight: 600; letter-spacing: -1px;">예술대학 글로벌예술학부 &nbsp;<span style="font-weight: 300; font-size:22px;">|</span>&nbsp; 805관 6101호</p>
                                </div>
                            </div>
                        </div>
                        """
                        
                        st.markdown("<div style='background-color:#f1f8e9; padding:15px; border-radius:8px; border:1px solid #c5e1a5; color:#2e7d32; font-weight:bold; margin-bottom:15px;'>✅ 준비 완료! 하단 버튼을 클릭하면 독립된 A4 사이즈 팝업이 열리며 즉시 인쇄 화면이 나타납니다. (반드시 브라우저 팝업 차단을 해제해주세요)</div>", unsafe_allow_html=True)
                        
                        full_iframe_html = """
                        <!DOCTYPE html>
                        <html>
                        <head>
                        <style>
                            body { font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; color: #000; margin: 0; padding: 10px; }
                        </style>
                        </head>
                        <body>
                            <div style="margin-bottom: 20px;">
                                <button onclick="triggerPrint()" style="padding:15px 24px; font-size:18px; font-weight:bold; cursor:pointer; background-color:#2e7d32; color:white; border:none; border-radius:8px; width:100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🖨️ 해당 신청서 A4 용지 팝업 인쇄하기 (Ctrl+P)</button>
                            </div>
                            
                            <div id="print-source-data" style="display:none;">
                                __HTML_CONTENT_PLACEHOLDER__
                            </div>
                            
                            <script>
                                function triggerPrint() {
                                    const printData = document.getElementById('print-source-data').innerHTML;
                                    const printWindow = window.open('', '_blank', 'width=850,height=950');
                                    printWindow.document.write('<!DOCTYPE html><html><head><title>기자재 대여 신청서 인쇄</title>');
                                    printWindow.document.write('<style>');
                                    printWindow.document.write('@page { size: A4; margin: 10mm; }');
                                    printWindow.document.write('body { font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; color: #000; background-color: #fff; margin: 0; padding: 0; box-sizing: border-box; }');
                                    printWindow.document.write('table { border-collapse: collapse; width: 100%; border: 2px solid black; font-size: 13px; }');
                                    printWindow.document.write('th, td { border: 1px solid black; padding: 8px; }');
                                    printWindow.document.write('th { background-color: #f2f2f2 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; text-align: center; }');
                                    printWindow.document.write('</style>');
                                    printWindow.document.write('</head><body>');
                                    printWindow.document.write(printData);
                                    printWindow.document.write('</body></html>');
                                    printWindow.document.close();
                                    printWindow.focus();
                                    setTimeout(function() {
                                        printWindow.print();
                                        printWindow.close();
                                    }, 250);
                                }
                            </script>
                        </body>
                        </html>
                        """.replace("__HTML_CONTENT_PLACEHOLDER__", html_content)
                        
                        st.components.v1.html(full_iframe_html, height=100)

# --- 4. 품목별 대여 통계 ---
elif menu == "품목별 대여 통계":
    st.header("📈 품목별 대여 통계")
    valid_rentals = df_rental[df_rental["품명"] != ""].copy()
    if valid_rentals.empty:
        st.info("💡 아직 누적된 대여 기록이 없어 통계를 산출할 수 없습니다.")
    else:
        st.markdown("학생들이 가장 많이 대여한 인기 기자재 순위를 확인하세요!")
        
        valid_rentals["품명_clean"] = valid_rentals["품명"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        valid_rentals["규격_clean"] = valid_rentals["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        
        stats_df = valid_rentals.groupby(["품명_clean", "규격_clean"]).size().reset_index(name="누적 대여 횟수")
        stats_df = stats_df.rename(columns={"품명_clean": "품명", "규격_clean": "규격"})
        stats_df = stats_df.sort_values(by="누적 대여 횟수", ascending=False).reset_index(drop=True)
        
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📊 대여 빈도 시각화")
        
        chart = alt.Chart(stats_df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X('규격', sort='-y', axis=alt.Axis(labelAngle=-45, title="기자재 규격")),
            y=alt.Y('누적 대여 횟수', axis=alt.Axis(tickMinStep=1, title="대여 횟수 (건)")),
            color=alt.Color('품명', legend=alt.Legend(orient="bottom", title="품목 (품명)")),
            tooltip=['품명', '규격', '누적 대여 횟수']
        ).properties(
            height=400
        ).configure_axis(
            grid=False
        ).configure_view(
            strokeWidth=0
        )
        
        st.altair_chart(chart, use_container_width=True)

# --- 5. 반납 처리 ---
elif menu == "기자재 반납 처리":
    st.header("🔄 기자재 반납 처리 (관리자 전용)")
    active_rentals = df_rental[df_rental["승인상태"] == "대여중"].copy()
    if not active_rentals.empty:
        active_rentals.insert(0, "선택", False)
        edited_active = st.data_editor(active_rentals, hide_index=True)
        if st.button("👍 반납 확인 (기록 완전 삭제)", type="primary"):
            sel = edited_active[edited_active["선택"] == True]
            if not sel.empty:
                t_ids = sel["장비ID"].tolist()
                df_equip.loc[df_equip["장비ID"].isin(t_ids), "현재상태"] = "대여가능"
                df_rental = df_rental[~df_rental["장비ID"].isin(t_ids)].copy()
                save_data(df_equip, df_rental)
                st.success("반납 완료 및 정보 삭제 완료")
                st.rerun()

# --- 6. 장비 관리 ---
elif menu == "⚙️ 장비 관리 (관리자 전용)":
    if not is_admin: st.stop()
    st.header("⚙️ 장비 일괄 관리 및 신규 등록")
    
    st.subheader("🛠️ 장비 상태 일괄/수동 변경")
    cols_order = ["장비ID", "품명", "규격", "현재상태", "기자재자산번호", "비고"]
    edited_equip_df = st.data_editor(df_equip[cols_order], hide_index=True, use_container_width=True)
    if st.button("💾 변경된 상태 한 번에 저장하기", type="primary"):
        for col in cols_order:
            df_equip[col] = edited_equip_df[col]
        save_data(df_equip, df_rental)
        st.success("저장 완료!")
        st.rerun()

    st.markdown("---")
    st.subheader("🖼️ 기존 장비 사진 업데이트 (일괄 적용)")
    st.caption("선택한 규격을 가진 모든 장비의 사진이 썸네일로 한 번에 업데이트됩니다.")
    
    unique_specs = df_equip["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip().unique()
    target_spec = st.selectbox("사진을 업데이트할 규격 선택", [s for s in unique_specs if s])
    
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        update_file = st.file_uploader(f"[{target_spec}] 사진 파일 업로드", type=["jpg", "jpeg", "png"], key="update_img")
    with col_img2:
        update_url = st.text_input("또는 인터넷 이미지 URL 주소 직접 입력", placeholder="https://...", key="update_url")
        
    if st.button("💾 선택한 규격의 사진 일괄 업데이트", type="primary"):
        if not update_file and not update_url.strip():
            st.warning("업로드할 사진 파일이나 URL을 입력해주세요.")
        else:
            final_update_val = ""
            if update_file is not None:
                try:
                    img = Image.open(update_file)
                    if img.mode in ("RGBA", "P"): 
                        img = img.convert("RGB")
                    img.thumbnail((250, 250)) 
                    buffered = io.BytesIO()
                    img.save(buffered, format="JPEG", quality=80)
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    final_update_val = f"data:image/jpeg;base64,{img_str}"
                except Exception as e:
                    st.error(f"이미지 변환 오류: {e}")
            elif update_url.strip():
                final_update_val = update_url.strip()
                
            if final_update_val:
                mask = df_equip["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip() == target_spec
                df_equip.loc[mask, "이미지URL"] = final_update_val
                save_data(df_equip, df_rental)
                st.success(f"✅ '{target_spec}' 규격의 모든 장비 사진이 일괄 업데이트되었습니다!")
                st.rerun()
            
    st.markdown("---")
    st.subheader("➕ 신규 기자재 추가 등록")
    
    with st.form("add_equipment_form", clear_on_submit=True):
        new_name = st.text_input("📦 품명 (예: 캠코더, 미러리스 카메라)")
        new_spec = st.text_input("📐 규격 (예: PWX-Z90, Sony FX3)")
        new_asset_no = st.text_input("🏷️ 기자재자산번호 (선택)")
        
        st.markdown("---")
        st.markdown("🖼️ **장비 사진 등록 (선택)**")
        st.caption("PC에 있는 사진을 업로드하면 시스템이 썸네일로 압축하여 구글 시트에 안전하게 저장합니다.")
        
        uploaded_file = st.file_uploader("PC에서 사진 파일 업로드", type=["jpg", "jpeg", "png"])
        new_img_url = st.text_input("또는 인터넷 이미지 URL 주소 직접 입력 (업로드 시 무시됨)", placeholder="https://...")
        
        new_remarks = st.text_input("📝 비고")
        
        if st.form_submit_button("🚀 새 장비 등록하기"):
            if not new_name.strip():
                st.error("❌ 품명은 필수 입력 항목입니다.")
            else:
                prefix = "EQ-AUTO-"
                auto_ids = df_equip[df_equip["장비ID"].str.startswith(prefix, na=False)]
                new_num = f"{auto_ids['장비ID'].str.split('-').str[-1].astype(int).max() + 1:04d}" if not auto_ids.empty else "0001"
                generated_id = prefix + new_num
                
                final_image_val = ""
                if uploaded_file is not None:
                    try:
                        img = Image.open(uploaded_file)
                        if img.mode in ("RGBA", "P"): 
                            img = img.convert("RGB")
                        
                        img.thumbnail((250, 250)) 
                        buffered = io.BytesIO()
                        img.save(buffered, format="JPEG", quality=80)
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        final_image_val = f"data:image/jpeg;base64,{img_str}"
                    except Exception as e:
                        st.warning(f"이미지 변환 중 오류 발생: {e}")
                        final_image_val = new_img_url.strip()
                elif new_img_url.strip():
                    final_image_val = new_img_url.strip()
                
                new_equip_row = {
                    "장비ID": generated_id, 
                    "품명": new_name.strip(), 
                    "규격": new_spec.strip() if new_spec.strip() else "-", 
                    "현재상태": "대여가능", 
                    "기자재자산번호": new_asset_no.strip() if new_asset_no.strip() else "-",
                    "비고": new_remarks.strip() if new_remarks.strip() else "-",
                    "이미지URL": final_image_val
                }
                
                df_equip = pd.concat([df_equip, pd.DataFrame([new_equip_row])], ignore_index=True)
                save_data(df_equip, df_rental)
                st.success(f"🎉 등록 성공! 자동 발급된 ID: [{generated_id}]")
                st.rerun()
