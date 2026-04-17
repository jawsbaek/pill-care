"""Streamlit UI for PillCare medication guidance POC."""

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from pillcare.logging_config import setup_logging  # noqa: E402

setup_logging()

from pillcare.llm_factory import create_llm  # noqa: E402
from pillcare.pipeline import build_pipeline  # noqa: E402
from pillcare.schemas import GuidanceResult  # noqa: E402

_DISCLAIMER = (
    "이 서비스는 의료 행위가 아니며, 전문 의료인의 상담을 대체하지 않습니다. "
    "제공되는 정보는 공개된 식약처 데이터를 기반으로 하며, "
    "개인의 건강 상태에 따라 다를 수 있습니다."
)


def _get_db_path() -> str:
    """Resolve DB path: GCS download or local file."""
    gcs_bucket = os.environ.get("GCS_BUCKET")
    if gcs_bucket:
        from pillcare.gcs_loader import download_db, compute_sha256

        local_path = "/tmp/pillcare.db"
        expected_sha = os.environ.get("DB_SHA256")
        needs_download = not Path(local_path).exists()
        if not needs_download and expected_sha:
            actual_sha = compute_sha256(local_path)
            needs_download = actual_sha != expected_sha
        if needs_download:
            try:
                download_db(
                    bucket_name=gcs_bucket,
                    blob_name=os.environ.get("GCS_BLOB", "pillcare.db"),
                    local_path=local_path,
                    expected_sha256=expected_sha,
                )
            except Exception as e:
                raise RuntimeError(f"GCS DB 다운로드 실패: {e}") from e
        return local_path

    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / "data" / "pillcare.db")


@st.cache_resource
def _get_pipeline(db_path: str):
    """Cache compiled graph across Streamlit reruns."""
    llm = create_llm()
    return build_pipeline(db_path=db_path, llm=llm)


def main():
    st.set_page_config(page_title="필케어 — 복약 정보 안내", layout="wide")
    st.title("필케어 (PillCare)")
    st.caption("개인 투약이력 기반 grounded 복약 정보 안내 POC")
    st.info(_DISCLAIMER)

    try:
        db_path = _get_db_path()
    except Exception:
        st.error("데이터베이스를 불러올 수 없습니다. 관리자에게 문의하세요.")
        return
    if not Path(db_path).exists():
        st.error("데이터베이스 파일을 찾을 수 없습니다. 관리자에게 문의하세요.")
        return

    uploaded_files = st.file_uploader(
        "심평원 '내가 먹는 약' 투약이력 파일 업로드 (.xls)",
        type=["xls"],
        accept_multiple_files=True,
    )

    password = st.text_input("파일 비밀번호", type="password")

    departments: dict[str, str] = {}
    if uploaded_files:
        for i, uf in enumerate(uploaded_files):
            departments[uf.name] = st.text_input(
                f"{uf.name}의 진료과", value="미지정", key=f"dept_{i}_{uf.name}"
            )

    if not uploaded_files or not password:
        st.info("투약이력 파일을 업로드하고 비밀번호를 입력하세요.")
        return

    if st.button("분석 시작"):
        from pillcare.history_parser import parse_history_xls

        with st.spinner("투약이력 파싱 중..."):
            all_records = []
            for uf in uploaded_files:
                dept = departments.get(uf.name, "미지정")
                with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
                    tmp.write(uf.read())
                    tmp_path = Path(tmp.name)
                try:
                    records = parse_history_xls(
                        tmp_path, password=password, department=dept
                    )
                except Exception as e:
                    st.error(f"{uf.name} 파싱 실패: {e}")
                    continue
                finally:
                    tmp_path.unlink(missing_ok=True)
                for rec in records:
                    all_records.append(
                        {
                            "drug_name": rec.drug_name,
                            "drug_code": rec.drug_code,
                            "department": rec.department,
                        }
                    )

        st.success(f"{len(all_records)}개 약물 파싱 완료")

        if not all_records:
            st.warning("파싱에 성공한 약물이 없습니다. 파일과 비밀번호를 확인하세요.")
            return

        with st.spinner("LangGraph 파이프라인 실행 중..."):
            try:
                graph = _get_pipeline(db_path)
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
            except Exception:
                st.error(
                    "파이프라인 실행 중 오류가 발생했습니다. 잠시 후 다시 시도하세요."
                )
                return

        errors = final_state.get("errors", [])
        critical_errors = [e for e in errors if e.startswith("[CRITICAL]")]
        if critical_errors:
            st.error("복약 정보 생성에 실패했습니다. 의사 또는 약사에게 문의하세요.")
            return

        result_data = final_state.get("guidance_result")
        if result_data:
            result = (
                GuidanceResult(**result_data)
                if isinstance(result_data, dict)
                else result_data
            )

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
                            st.markdown(
                                f"**{section.title}** `{section.source_tier.value}`"
                            )
                            st.write(section.content)

            if result.summary:
                st.subheader("핵심 요약 (별첨2)")
                for point in result.summary:
                    st.write(f"- {point}")

            if result.warning_labels:
                st.subheader("경고 라벨 (별첨3)")
                for label in result.warning_labels:
                    st.warning(label)

        non_critical_errors = [e for e in errors if not e.startswith("[CRITICAL]")]
        if non_critical_errors:
            st.subheader("검증 결과")
            for e in non_critical_errors:
                st.warning(e)


if __name__ == "__main__":
    main()
