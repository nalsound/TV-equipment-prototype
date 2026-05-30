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

# --- 공지사항 텍스트 파일 (클라우드 임시 저장용) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTICE_FILE = os.path.join(BASE_DIR, "notice.txt")

def load_data():
    """구글 스프레드시트에서 실시간으로 데이터를 불러오는 함수"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        df_equip = conn.read(spreadsheet=EQUIPMENT_SHEET_URL, ttl=600)
        df_rental = conn.read(spreadsheet=RENTAL_SHEET_URL, ttl=600)

        # 공백 제거 등 데이터 정제
        for df in [df_equip, df_rental]:
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].astype(str).str.strip()

        # (수정됨) 과거 반납 완료 내역 가리기 로직 삭제 -> 이력 보존을 위해 전체 데이터를 가져옵니다.

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
    except Exception as e:
        st.error(f"❌ 구글 시트에 데이터를 저장하는 중 오류가 발생했습니다: {e}")

# ==========================================

# --- 스팀릿 웹 페이지 설정 ---
st.set_page_config(page_title="기자재 관리 시스템", layout="wide")

st.markdown("""
    <style>
    .printable-area { background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 15px; margin-bottom: 15px; }
    .printable-area table {width: 100%; border-collapse: collapse; margin-top: 10px;}
    .printable-area th, .printable-area td {border: 1px solid #ddd; padding: 8px; text-align: left;}
    .printable-area th {background-color: #f2f2f2;}
    @media print {
        header[data-testid="stHeader"] {display: none;} section[data-testid="stSidebar"] {display: none;}
        .stButton {display: none;} iframe {display: none;} div[data-testid="stToolbar"] {display: none;}
        .printable-area { position: absolute; left: 0; top: 0; width: 100%; background-color: white; padding: 20mm; z-index: 9999; font-family: 'Malgun Gothic', sans-serif; border: none; }
        .printable-area table {width: 100%; border-collapse: collapse; margin-top: 20px;}
        .printable-area th, .printable-area td {border: 1px solid black; padding: 10px; text-align: left;}
        .printable-area th {background-color: #f2f2f2;}
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State 초기화 ---
if "cart" not in st.session_state: st.session_state.cart = []
if "admin_auth" not in st.session_state: st.session_state.admin_auth = False
if "clear_inputs" not in st.session_state: st.session_state.clear_inputs = False
if "submit_success" not in st.session_state: st.session_state.submit_success = False

# --- 공지사항 팝업 ---
if "notice_shown" not in st.session_state:
    notice_msg = "여러분들의 소중한 기자재입니다."
    if os.path.exists(NOTICE_FILE):
        with open(NOTICE_FILE, "r", encoding="utf-8") as f:
            notice_msg = f.read().strip()
    st.toast(notice_msg, icon="📢")
    st.session_state.notice_shown = True

st.title("🎬 기자재 관리 시스템")

# 데이터 불러오기
df_equip, df_rental = load_data()

# --- 사이드바 ---
st.sidebar.subheader("🔒 관리자 로그인")
if not st.session_state.admin_auth:
    input_password = st.sidebar.text_input("관리자 비밀번호를 입력하세요", type="password")
    if input_password == "admin1234":
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

menu = st.sidebar.radio("📌 메뉴 선택", ["공지사항", "장비 목록 조회", "대여 신청 현황", "신규 대여 신청", "기자재 반납 처리"])

# --- 0. 공지사항 메뉴 ---
if menu == "공지사항":
    st.header("📢 공지사항")
    current_notice = "등록된 공지사항이 없습니다."
    if os.path.exists(NOTICE_FILE):
        with open(NOTICE_FILE, "r", encoding="utf-8") as f:
            current_notice = f.read().strip()

    if is_admin:
        st.info("관리자 모드입니다. 아래에서 공지사항을 수정하고 저장할 수 있습니다.")
        new_notice = st.text_area("📝 공지사항 내용 수정", value=current_notice, height=200)
        if st.button("💾 공지사항 저장 및 적용하기", type="primary"):
            with open(NOTICE_FILE, "w", encoding="utf-8") as f:
                f.write(new_notice)
            st.success("✅ 공지사항이 성공적으로 업데이트되었습니다!")
            st.session_state.notice_shown = False 
            st.rerun()
    else:
        st.markdown("### 📌 안내 말씀")
        st.success(current_notice)

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
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📋 개별 장비 상세 현황")
    filter_option = st.radio("필터 선택", ["전체 장비 보기", "대여 가능 장비만 보기"], horizontal=True)
    display_df = df_equip[df_equip["현재상태"] == "대여가능"].copy() if filter_option == "대여 가능 장비만 보기" else df_equip.copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if is_admin:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🛠️ 장비 상태 수동 변경")
            equip_options = df_equip.apply(lambda r: f"{r['장비ID']} | {r['품명']} ({r['규격']}) [현재: {r['현재상태']}]", axis=1).tolist()
            selected_equip_opt = st.selectbox("상태를 변경할 장비를 선택하세요", equip_options)
            if selected_equip_opt:
                target_equip_id = selected_equip_opt.split(" | ")[0].strip()
                status_list = ["대여가능", "대여중", "고장", "수리중", "승인대기"]
                current_status = df_equip.loc[df_equip["장비ID"] == target_equip_id, "현재상태"].values[0]
                default_idx = status_list.index(current_status) if current_status in status_list else 0
                new_status = st.selectbox("변경할 새로운 상태를 선택하세요", status_list, index=default_idx)
                if st.button("💾 상태 변경 저장하기", type="primary"):
                    df_equip.loc[df_equip["장비ID"] == target_equip_id, "현재상태"] = new_status
                    save_data(df_equip, df_rental)
                    st.success(f"✅ 장비 [{target_equip_id}] 상태가 '{new_status}'로 변경되었습니다.")
                    st.rerun()
        with col2:
            st.subheader("➕ 신규 기자재 추가 등록")
            with st.form("add_equipment_form", clear_on_submit=True):
                new_name = st.text_input("📦 품명 (예: 캠코더, 미러리스 카메라)")
                new_spec = st.text_input("📐 규격 (예: PWX-Z90, Sony FX3)")
                new_remarks = st.text_input("📝 비고")
                if st.form_submit_button("🚀 새 장비 등록하기"):
                    if not new_name.strip():
                        st.error("❌ 품명은 필수 입력 항목입니다.")
                    else:
                        prefix = "EQ-AUTO-"
                        auto_ids = df_equip[df_equip["장비ID"].str.startswith(prefix, na=False)]
                        new_num = f"{auto_ids['장비ID'].str.split('-').str[-1].astype(int).max() + 1:04d}" if not auto_ids.empty else "0001"
                        generated_id = prefix + new_num
                        new_equip_row = {"장비ID": generated_id, "품명": new_name.strip(), "규격": new_spec.strip() if new_spec.strip() else "-", "현재상태": "대여가능", "비고": new_remarks.strip() if new_remarks.strip() else "-"}
                        df_equip = pd.concat([df_equip, pd.DataFrame([new_equip_row])], ignore_index=True)
                        save_data(df_equip, df_rental)
                        st.success(f"🎉 등록 성공! 자동 발급된 ID: [{generated_id}]")
                        st.rerun()
    else:
        st.markdown("---")
        st.warning("🔒 장비 상태 변경 및 신규 등록은 관리자 기능입니다. 사이드바에 비밀번호를 입력해주세요.")

# --- 2. 대여 신청 현황 ---
elif menu == "대여 신청 현황":
    st.header("📋 기자재 대여 신청 현황")
    if df_rental.empty:
        st.info("현재 대여 및 대기 중인 신청 내역이 없습니다.")
    else:
        # (수정됨) 화면에 띄울 때만 '반납완료' 내역 가리기
        active_rentals_display = df_rental[df_rental["승인상태"] != "반납완료"]
        display_rental = active_rentals_display.drop(columns=["학번", "연락처"], errors="ignore") if not is_admin else active_rentals_display.copy()
        
        st.caption("🔓 관리자 모드: 모든 신청인의 정보가 정상 노출됩니다." if is_admin else "🔒 학생들의 개인정보 보호를 위해 '학번' 및 '연락처'는 관리자 로그인 시에만 조회됩니다.")
        st.dataframe(display_rental, use_container_width=True, hide_index=True)
        st.markdown("---")

        if is_admin:
            st.subheader("🔓 관리자 전용 - 개별 대여 승인 처리")
            pending_rentals = df_rental[df_rental["승인상태"].str.strip().isin(["대기중", "승인대기", "대기"])].copy()
            if pending_rentals.empty:
                st.success("✅ 현재 승인 대기 중인 신청 품목이 없습니다.")
            else:
                st.markdown("**[ 대기 중인 상세 장비 목록 ] - 승인할 장비의 체크박스를 선택하세요.**")
                select_all_pending = st.checkbox("☑️ 표 전체 선택 / 해제", key="select_all_pending")
                pending_rentals.insert(0, "선택", select_all_pending)
                edited_pending = st.data_editor(pending_rentals[["선택", "신청ID", "이름", "장비ID", "품명", "규격", "대여날짜", "반납일자"]], column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)}, hide_index=True, use_container_width=True)
                if st.button("⭕ 선택한 장비 개별 승인하기", type="primary"):
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
            
            st.markdown("---")
            st.subheader("🖨️ 관리자 전용 - 신청서 A4 인쇄")
            all_rental_ids = df_rental["신청ID"].unique().tolist()
            if not all_rental_ids:
                st.info("출력 가능한 대여 신청 내역이 없습니다.")
            else:
                selected_print_id = st.selectbox("🖨️ 출력 서류를 선택하세요", all_rental_ids)
                if selected_print_id:
                    print_rows = df_rental[df_rental["신청ID"] == selected_print_id]
                    if not print_rows.empty:
                        p_first = print_rows.iloc[0]
                        item_counts = print_rows.groupby(["품명", "규격"]).size().reset_index(name="수량")
                        items_str = ", ".join([f"{r['품명']} ({r['규격']}) {r['수량']}대" for _, r in item_counts.iterrows()])
                        html_content = f"""<div class="printable-area"><h1 style="text-align: center; margin-bottom: 30px;">글로벌예술학부 기자재 대여 신청서</h1><table><tr><th>신청ID</th><td colspan="3">{p_first['신청ID']}</td></tr><tr><th>성명</th><td>{p_first['이름']}</td><th>학번</th><td>{p_first['학번']}</td></tr><tr><th>연락처</th><td>{p_first['연락처']}</td><th>담당교수</th><td>{p_first['담당교수']}</td></tr><tr><th>교과명</th><td>{p_first['교과명']}</td><th>촬영장소</th><td>{p_first['촬영장소']}</td></tr><tr><th>대여기간</th><td colspan="3">{p_first['대여날짜']} ~ {p_first['반납일자']}</td></tr><tr><th>대여 품목</th><td colspan="3">{items_str}</td></tr><tr><th>기타 기자재</th><td colspan="3">{p_first['기타기자재']}</td></tr></table><div style="margin-top: 40px; text-align: right;"><p>위와 같이 기자재 대여를 신청합니다.</p><p>20  년   월   일</p><p>신청인 : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인/서명)</p></div></div>"""
                        st.markdown(html_content, unsafe_allow_html=True)
                        st.components.v1.html("""<button onclick="window.print()" style="padding:10px 20px; font-size:16px; font-weight:bold; cursor:pointer; background-color:#FF4B4B; color:white; border:none; border-radius:5px; width:100%;">🖨️ 해당 신청서 A4 용지 인쇄하기</button>""", height=50)

# --- 3. 신규 대여 신청 ---
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
        active_rentals = df_rental[df_rental["승인상태"] == "대여중"]
        if active_rentals.empty: 
            st.info("현재 대여 중인 장비가 없습니다.")
        else: 
            st.dataframe(active_rentals[["신청ID", "품명", "규격", "이름", "대여날짜", "반납일자"]], use_container_width=True, hide_index=True)

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
                            df_rental = pd.concat([df_rental, pd.DataFrame(new_rows)], ignore_index=True)
                            save_data(df_equip, df_rental)
                            st.session_state.cart = []
                            st.session_state.clear_inputs = True
                            st.session_state.submit_success = True
                            st.rerun()

# --- 4. 기자재 반납 처리 ---
elif menu == "기자재 반납 처리":
    st.header("🔄 기자재 반납 처리 (관리자 전용)")
    if is_admin:
        active_rentals = df_rental[df_rental["승인상태"] == "대여중"].copy()
        if active_rentals.empty: st.info("✅ 현재 대여 중이어서 반납 처리할 장비가 없습니다.")
        else:
            st.markdown("**[ 대여 중인 상세 장비 목록 ] - 반납된 장비의 체크박스를 선택하세요.**")
            select_all_return = st.checkbox("☑️ 표 전체 선택 / 해제", key="select_all_return")
            active_rentals.insert(0, "선택", select_all_return)
            edited_active = st.data_editor(active_rentals[["선택", "신청ID", "이름", "장비ID", "품명", "규격", "반납일자"]], column_config={"선택": st.column_config.CheckboxColumn("선택", default=False)}, hide_index=True, use_container_width=True)

            if st.button("👍 선택한 장비 반납 확인", type="primary"):
                selected_to_return = edited_active[edited_active["선택"] == True]
                if not selected_to_return.empty:
                    target_ids = selected_to_return["장비ID"].tolist()
            
                    # (수정됨) 상태를 반납완료로 변경하고 개인정보 파기
                    df_rental.loc[df_rental["장비ID"].isin(target_ids), "승인상태"] = "반납완료"
                    df_rental.loc[df_rental["장비ID"].isin(target_ids), "학번"] = "파기됨"
                    df_rental.loc[df_rental["장비ID"].isin(target_ids), "연락처"] = "파기됨"

                    df_equip.loc[df_equip["장비ID"].isin(target_ids), "현재상태"] = "대여가능"
                    
                    save_data(df_equip, df_rental)
                    st.success(f"✅ 장비 {len(target_ids)}대의 반납 처리 및 개인정보 파기가 완료되었습니다.")
                    st.rerun()
                else: 
                    st.warning("반납 처리할 장비를 표에서 먼저 체크해주세요.")
    else:
        st.warning("🔒 반납 처리는 관리자 전용 메뉴입니다. 사이드바에 비밀번호를 입력해주세요.")
