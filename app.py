"""로컬 여행 블로그 봇 1.0 — Streamlit + OpenAI Responses web search."""
import os
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="로컬 여행 블로그 봇 1.0", page_icon="🧭", layout="wide")
st.markdown("""<style>.block-container{max-width:1150px;padding-top:1.8rem}h1{letter-spacing:-1px}</style>""", unsafe_allow_html=True)
st.title("🧭 로컬 여행 블로그 봇 1.0")
st.caption("숨은 장소 발굴 → 경쟁 콘텐츠 비교 → 검색형 제목 → 실제 여행에 도움이 되는 블로그")


def secret(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


def response_text(client, model, instructions, prompt, search=True):
    args = dict(model=model, instructions=instructions, input=prompt, max_output_tokens=5500)
    if search:
        args["tools"] = [{"type": "web_search"}]
    response = client.responses.create(**args)
    result = (response.output_text or "").strip()
    if not result:
        raise RuntimeError("생성된 텍스트가 없습니다. 모델 권한과 응답 상태를 확인하세요.")
    return result


def download_html(markdown_text):
    try:
        import markdown
        body = markdown.markdown(markdown_text, extensions=["tables", "fenced_code"])
    except ImportError:
        body = "<pre>" + escape(markdown_text) + "</pre>"
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<title>여행 블로그 초안</title><style>body{font-family:system-ui, sans-serif;'
            'line-height:1.8;max-width:760px;margin:40px auto;padding:0 20px}'
            'table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:8px}'
            'img{max-width:100%}</style></head><body>'+body+'</body></html>')


if "research" not in st.session_state:
    st.session_state.research = ""
if "draft" not in st.session_state:
    st.session_state.draft = ""
if "chosen_title" not in st.session_state:
    st.session_state.chosen_title = ""

with st.sidebar:
    st.header("⚙️ 설정")
    key_from_settings = secret("OPENAI_API_KEY")
    api_key = st.text_input("OpenAI API 키", type="password", value=key_from_settings,
                            help="Streamlit Cloud의 Secrets에 OPENAI_API_KEY를 등록하면 직접 입력할 필요가 없습니다.")
    model = st.text_input("API 모델", value=secret("OPENAI_MODEL", "gpt-6-astra"),
                          help="계정에서 사용 가능한 Responses API + web_search 지원 모델로 변경할 수 있습니다.")
    st.info("웹 검색 기능에는 별도 API 사용료가 발생할 수 있습니다. 키는 코드 파일에 저장하지 마세요.")

with st.form("travel_options"):
    a, b, c = st.columns(3)
    region = a.text_input("여행 지역", value="부산", placeholder="부산, 창원, 통영…")
    neighborhood = b.text_input("세부 지역·관광지 (선택)", value="", placeholder="아미동, 초량, 영도…")
    age = c.selectbox("핵심 독자", ["20~40대", "20대", "30대", "40대", "전 연령"])
    d, e, f = st.columns(3)
    days = d.selectbox("여행 일정", ["당일치기", "반나절", "1박 2일", "2박 3일"], index=2)
    spend = e.selectbox("예산 방향", ["가성비", "다양한 가격대", "프리미엄 포함"], index=1)
    window = f.selectbox("검색 조사 기간", ["최근 30일", "최근 7일", "최근 90일"], index=0)
    included = st.multiselect("본문 포함 항목", ["숨은 관광지", "역사·사연", "현지인 맛집", "분식·간식", "카페", "로컬 쇼핑", "호텔·모텔·게스트하우스", "동선·교통", "경비"], default=["숨은 관광지", "역사·사연", "현지인 맛집", "분식·간식", "카페", "로컬 쇼핑", "호텔·모텔·게스트하우스", "동선·교통"])
    exclude = st.text_input("제외할 유명 관광지/추가 지시 (선택)", placeholder="해운대·광안리 제외, 조용한 동네 위주")
    research = st.form_submit_button("🔎 1단계: 웹 조사 + 경쟁 분석 + 제목 10개", use_container_width=True, type="primary")

policy = """당신은 한국 지역 여행 블로그의 사실 검증 및 SEO 편집자다.
웹 검색을 실제 사용해 근거와 URL을 제시하라. 확인되지 않은 장소/상호/영업시간/가격/현지인 단골 여부/숙박 가능 여부/연령별 검색순위 등을 꾸며내지 마라.
검색 결과에 나왔다는 이유만으로 검색량이나 순위를 단정하지 마라. 20~40대 실측 연령별 데이터가 없다면 명시하라.
경쟁 블로그와 겹치는 점, 검증 가능한 차별화 포인트, 확인이 필요한 사항을 구분하라.
시점이 오래된 자료는 날짜를 적고 현재 운영 확인이 필요함을 알려라. 홍보글이나 광고성 후기는 구분하라.
한국어로 자연스럽게 작성하며 과장·낚시성 제목·키워드 남용을 피하라. 실제 방문하지 않았으면 체험한 듯이 쓰지 마라.
"""

if research:
    if not api_key:
        st.error("OpenAI API 키를 설정해 주세요. ChatGPT 구독과 API 요금은 별도입니다.")
    elif not region.strip():
        st.error("여행 지역을 입력해 주세요.")
    else:
        prompt = f"""오늘(한국시간): {datetime.now(ZoneInfo('Asia/Seoul')).date()}
지역: {region}; 세부 지역: {neighborhood or '자동 추천'}; 대상: {age}; 일정: {days}; 예산: {spend}; 조사 시점: {window}
포함: {', '.join(included)}; 추가요구: {exclude or '없음'}.
실제 웹 자료를 확인하고 아래 형식의 조사 보고서를 만드세요.
1) 3~5개 숨은 여행지 후보 (근거 있는 실존 장소만). 대표적인 유명 관광지는 우선 제외. 각 장소의 스토리와 발굴 가치, 근거 URL.
2) 후보별 도보/현실적 동선에 있는 식당·분식·카페·쇼핑·숙소 예시. 검색 결과에서 실제 확인된 상호만 쓰고 주소·출처·미확인 사항 구분.
3) 유사 블로그 및 가이드 글 5개 내외를 웹에서 검색해 제목+URL+공통점+빠진 정보 분석. 찾지 못하면 솔직히 부족하다고 기록.
4) 제목 10개: 검색어 선두배치 + 호기심 + 사실성의 조화. 10개를 번호 매겨 주고 1개를 추천. 수치 점수는 실측 순위처럼 보이지 않도록 생략.
5) 검색 추세/연령 정보: 확인된 공적 데이터가 있으면 수치·날짜·출처를 제시. 없으면 검색량 랭킹 불가 명시.
6) 차별화 관점 3개 및 사실 확인 체크리스트.
출처 URL은 본문에서 클릭 가능하게 표기하세요. 실제로 검색하지 않은 URL은 만들지 마세요."""
        try:
            with st.spinner("웹 자료를 확인하고 경쟁 글을 비교하고 있습니다…"):
                client = OpenAI(api_key=api_key)
                st.session_state.research = response_text(client, model, policy, prompt, search=True)
                st.session_state.draft = ""
            st.success("조사 결과가 생성됐습니다. 아래에서 제목을 선택하거나 수정한 뒤 초안을 생성하세요.")
        except Exception as ex:
            st.error(f"웹 조사 호출 실패: {ex}")

if st.session_state.research:
    st.divider()
    st.subheader("🔎 조사 보고서 · 제목 후보")
    st.markdown(st.session_state.research)
    st.download_button("조사 보고서 다운로드 (.md)", st.session_state.research, file_name="travel_research.md", mime="text/markdown")
    st.markdown("### ✍️ 제목 확정")
    st.caption("위 제목 10개 가운데 마음에 드는 하나를 복사해 넣거나 직접 편집하세요.")
    title = st.text_input("선정한 제목", key="chosen_title", placeholder="예: 부산 숨은 명소, 골목에 남은 뜻밖의 이야기")
    draft_click = st.button("📝 2단계: 이 제목으로 블로그 본문 생성", type="primary", use_container_width=True)
    if draft_click:
        if not title.strip():
            st.warning("제목을 먼저 입력해 주세요.")
        else:
            instructions = policy + "\n작성 글은 최소한의 쓸모없는 수식보다 구체적 이야기·이동·실용성을 중시한다. 조사 보고서 속 검증 정보만 사실처럼 단정하라. 직접 체험했다고 주장하지 마라."
            prompt = f"""다음 웹 조사 보고서에 근거해 한국어 여행 블로그 게시용 원고를 Markdown으로 작성하세요.
제목: {title}
여행 지역: {region} / {neighborhood}; 독자: {age}; 일정: {days}; 포함 항목: {', '.join(included)}.
주제 선정 이유와 제목이 본문에 반드시 맞도록 쓰고, 첫 문장 2~3개는 궁금증을 자극하되 과장하지 마세요.
실존 확인된 관광지·식당·분식·카페·로컬 매장·숙소만 구체적으로 소개하세요. 추천 이유, 매장 주소/확인 필요한 영업정보, 선택의 대안을 포함하세요.
여행자의 시점에서 순서대로 이동 가능한 일정을 작성하되 미확인 이동시간은 지어내지 말고 교통/시간 확인 표시를 남기세요.
본문은 1,600~2,400자 정도의 의미 있는 이야기, 역사·사연·의외성 1개 이상, 예산 안내, 여행 주의사항, 해시태그 10개, 사실 검증/업데이트 체크리스트, 참고 출처 URL로 구성하세요.
제목·본문에서 사실 확인되지 않은 '현지인 단골' 같은 주장은 피하세요. 수치 SEO 점수나 실측 검색순위는 만들지 마세요.

[웹 조사 보고서]
{st.session_state.research[:25000]}"""
            try:
                with st.spinner("여행 블로그 초안을 작성하고 있습니다…"):
                    st.session_state.draft = response_text(OpenAI(api_key=api_key), model, instructions, prompt, search=True)
                st.success("본문을 생성했습니다. 편집하고 다운로드할 수 있습니다.")
            except Exception as ex:
                st.error(f"본문 생성 호출 실패: {ex}")

if st.session_state.draft:
    st.divider()
    st.subheader("📄 네이버·구글 블로그 공용 초안")
    edited = st.text_area("블로그 원고 편집", value=st.session_state.draft, height=550)
    with st.expander("미리보기", expanded=False):
        st.markdown(edited)
    col1, col2 = st.columns(2)
    col1.download_button("Markdown 저장", edited, file_name="local_travel_blog.md", mime="text/markdown", use_container_width=True)
    col2.download_button("HTML 저장", download_html(edited), file_name="local_travel_blog.html", mime="text/html", use_container_width=True)
    st.info("네이버 편집기에 HTML 파일을 직접 붙여넣으면 서식이 보존되지 않을 수 있습니다. 미리보기에서 필요한 글과 표를 복사하거나 네이버 에디터에 맞춰 조정하세요.")

st.divider()
st.caption("1.0 제한: 네이버 데이터랩 연령별 실측 검색량 API 연동, 실시간 숙박 예약·요금, 지도 이동시간 자동 계산, 발행 후 검색 노출 추적은 아직 구현되지 않았습니다. 모든 내용은 발행 전에 확인해 주세요.")
