"""Streamlit UI for PillCare medication guidance POC."""

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from langchain_anthropic import ChatAnthropic

from pillcare.history_parser import parse_history_xls
from pillcare.pipeline import build_pipeline, run_pipeline
from pillcare.schemas import GuidanceResult


@st.cache_resource
def _get_pipeline(db_path: str, api_key: str):
    """Cache compiled graph across Streamlit reruns."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key, max_tokens=4096)
    return build_pipeline(db_path=db_path, llm=llm)

DB_PATH = Path("data/pillcare.db")


def main():
    st.set_page_config(page_title="필케어 — 복약 정보 안내", layout="wide")
    st.title("필케어 (PillCare)")
    st.caption("개인 투약이력 기반 grounded 복약 정보 안내 POC")

    if not DB_PATH.exists():
        st.error(f"DB not found at {DB_PATH}. Run `uv run python -m pillcare.db_builder` first.")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY not set in .env")
        return

    uploaded_files = st.file_uploader(
        "심평원 '내가 먹는 약' 투약이력 파일 업로드 (.xls)",
        type=["xls"],
        accept_multiple_files=True,
    )

    password = st.text_input("파일 비밀번호", type="password")

    departments: dict[str, str] = {}
    if uploaded_files:
        for uf in uploaded_files:
            departments[uf.name] = st.text_input(
                f"{uf.name}의 진료과", value="미지정", key=f"dept_{uf.name}"
            )

    if not uploaded_files or not password:
        st.info("투약이력 파일을 업로드하고 비밀번호를 입력하세요.")
        return

    if st.button("분석 시작"):
        with st.spinner("투약이력 파싱 중..."):
            all_records = []
            for uf in uploaded_files:
                dept = departments.get(uf.name, "미지정")
                with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
                    tmp.write(uf.read())
                    tmp_path = Path(tmp.name)
                try:
                    records = parse_history_xls(tmp_path, password=password, department=dept)
                finally:
                    tmp_path.unlink(missing_ok=True)
                for rec in records:
                    all_records.append({
                        "drug_name": rec.drug_name,
                        "drug_code": rec.drug_code,
                        "department": rec.department,
                    })

        st.success(f"{len(all_records)}개 약물 파싱 완료")

        with st.spinner("LangGraph 파이프라인 실행 중..."):
            graph = _get_pipeline(str(DB_PATH), api_key)
            initial_state = {
                "profile_id": "default",
                "raw_records": all_records,
                "matched_drugs": [],
                "dur_alerts": [],
                "drug_infos": [],
                "guidance_result": None,
                "errors": [],
            }
            final_state = graph.invoke(initial_state)

        result_data = final_state.get("guidance_result")
        if result_data:
            result = GuidanceResult(**result_data) if isinstance(result_data, dict) else result_data

            if result.dur_warnings:
                st.subheader("병용금기 경고")
                for w in result.dur_warnings:
                    cross = " (다기관 교차)" if w.cross_clinic else ""
                    st.error(f"**{w.drug_1}** x **{w.drug_2}**: {w.reason}{cross}")

            if result.drug_guidances:
                st.subheader("상세 복약 정보 (별첨1)")
                for dg in result.drug_guidances:
                    with st.expander(dg.drug_name):
                        for section_name, section in dg.sections.items():
                            st.markdown(f"**{section.title}** `{section.source_tier.value}`")
                            st.write(section.content)

            if result.summary:
                st.subheader("핵심 요약 (별첨2)")
                for point in result.summary:
                    st.write(f"- {point}")

            if result.warning_labels:
                st.subheader("경고 라벨 (별첨3)")
                for label in result.warning_labels:
                    st.warning(label)

        errors = final_state.get("errors", [])
        if errors:
            st.subheader("검증 결과")
            for e in errors:
                if e.startswith("[CRITICAL]"):
                    st.error(e)
                else:
                    st.warning(e)


if __name__ == "__main__":
    main()
