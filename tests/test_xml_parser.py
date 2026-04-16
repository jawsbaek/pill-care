"""Tests for NB_DOC_DATA XML parser."""

from pathlib import Path
import pytest
from pillcare.xml_parser import parse_nb_doc, Section


@pytest.fixture
def sample_xml(fixtures_dir: Path) -> str:
    return (fixtures_dir / "sample_nb_doc.xml").read_text(encoding="utf-8")


def test_parse_nb_doc_returns_sections(sample_xml):
    sections = parse_nb_doc(sample_xml)
    assert len(sections) >= 8
    types = {s.section_type for s in sections}
    assert "금기" in types
    assert "상호작용" in types
    assert "이상반응" in types


def test_section_type_mapping(sample_xml):
    sections = parse_nb_doc(sample_xml)
    by_type = {s.section_type: s for s in sections}
    assert "위장관궤양" in by_type["금기"].section_text
    assert "비스테로이드" in by_type["상호작용"].section_text
    assert "임신" in by_type["임부수유"].section_text


def test_section_preserves_multiple_paragraphs(sample_xml):
    sections = parse_nb_doc(sample_xml)
    interaction = next(s for s in sections if s.section_type == "상호작용")
    assert "ACE" in interaction.section_text
    assert "비스테로이드" in interaction.section_text


def test_section_order(sample_xml):
    sections = parse_nb_doc(sample_xml)
    orders = [s.section_order for s in sections]
    assert orders == sorted(orders)


def test_parse_empty_xml():
    sections = parse_nb_doc("")
    assert sections == []


def test_parse_none():
    sections = parse_nb_doc(None)
    assert sections == []
