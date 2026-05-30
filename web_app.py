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

# --- 공지사항 경로 설정 ---
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
    """구글 스프레드시트에서 데이터를 불러옵니다. 이제 이미지URL 열도 완벽히 관리합니다."""
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
# ✨ 강력한 캐시 새로고침 버튼 (데이터 변경 시 꼬임 방지)
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
    st.header("📜 기자재 이용 규정")
    st.markdown("규정 내용을 숙지해 주세요. (생략)")

# --- 1. 장비 목록 조회 ---
elif menu == "장비 목록 조회":
    st.header("🔍 기자재 목록 조회")
    st.subheader("📊 품목별 보유 현황 (수량 요약)")
    
    if df_equip.empty:
        st.info("등록된 장비가 없습니다.")
    else:
        df_summary_input = df_equip.copy()
        # 괄호 안의 (1호), (2호) 등을 제거하여 품명과 규격을 통일
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
                # 빈 값이나 의미 없는 값이 아닌 실제 이미지 데이터(http 또는 data:)를 우선 추출
                이미지URL=("이미지URL", lambda x: next((u for u in x if str(u).strip() and str(u).strip().lower() not in ["nan", "none", "<na>"] and (str(u).startswith("http") or str(u).startswith("data:"))), ""))
            ).reset_index()
        )
        
        # ✨ 사진이 없을 경우 엑스박스 대신 '장비 이름'이 적힌 깔끔한 플레이스홀더 이미지를 생성합니다.
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
        name = st.text_input("신청인 이름", key="input_name")
        student_id = st.text_input("학번", key="input_student_id")
        phone = st.text_input("연락처", key="input_phone")
        professor = st.text_input("담당 교수명", key="input_professor")
        course_name = st.text_input("교과명", key="input_course")
        shooting_loc = st.text_input("📍 촬영 장소", key="input_location")
        extra_items = st.text_input("🎒 기타 기자재", key="input_extra")

        st.markdown("---")
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

# --- 3. 대여 신청 현황 ---
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

# --- 4. 품목별 대여 통계 ---
elif menu == "품목별 대여 통계":
    st.header("📈 품목별 대여 통계")
    valid_rentals = df_rental[df_rental["품명"] != ""].copy()
    if not valid_rentals.empty:
        valid_rentals["품명_clean"] = valid_rentals["품명"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        valid_rentals["규격_clean"] = valid_rentals["규격"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
        stats_df = valid_rentals.groupby(["품명_clean", "규격_clean"]).size().reset_index(name="누적 대여 횟수")
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

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
    # 이미지 데이터가 너무 길어 표가 깨지는 것을 방지하기 위해 화면 표에서는 숨깁니다.
    cols_order = ["장비ID", "품명", "규격", "현재상태", "기자재자산번호", "비고"]
    edited_equip_df = st.data_editor(df_equip[cols_order], hide_index=True, use_container_width=True)
    if st.button("💾 변경된 상태 한 번에 저장하기", type="primary"):
        # 이미지 열을 보존하면서 나머지 수정된 열 업데이트
        for col in cols_order:
            df_equip[col] = edited_equip_df[col]
        save_data(df_equip, df_rental)
        st.success("저장 완료!")
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
        
        # 📸 이미지 파일 직접 업로드 기능
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
                
                # 💡 [업그레이드] 업로드된 이미지를 썸네일(최대 250px)로 압축 후 텍스트(Base64)로 변환!
                final_image_val = ""
                if uploaded_file is not None:
                    try:
                        img = Image.open(uploaded_file)
                        if img.mode in ("RGBA", "P"): # 투명 배경 오류 방지
                            img = img.convert("RGB")
                        
                        img.thumbnail((250, 250)) # 구글 시트 셀 용량 초과 방지를 위한 크기 최적화
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
