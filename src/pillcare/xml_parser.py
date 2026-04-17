"""Parse NB_DOC_DATA XML into structured sections."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class Section:
    section_type: str
    section_title: str
    section_text: str
    section_order: int


_TITLE_TO_TYPE: list[tuple[str, str]] = [
    ("투여하지 말 것", "금기"),
    ("복용하지 말 것", "금기"),
    ("신중히 투여", "신중투여"),
    ("상의할 것", "신중투여"),
    ("이상반응", "이상반응"),
    ("부작용", "이상반응"),
    ("상호작용", "상호작용"),
    ("임부", "임부수유"),
    ("수유부", "임부수유"),
    ("소아", "소아"),
    ("고령자", "고령자"),
    ("과량투여", "과량투여"),
    ("일반적 주의", "일반주의"),
    ("복용시 주의", "일반주의"),
    ("보관", "보관주의"),
    ("취급", "보관주의"),
    ("경고", "경고"),
]


def _classify_title(title: str) -> str:
    for keyword, section_type in _TITLE_TO_TYPE:
        if keyword in title:
            return section_type
    return "기타"


def _extract_text(article: ET.Element) -> str:
    paragraphs = []
    for para in article.iter("PARAGRAPH"):
        text = para.text or ""
        tail = para.tail or ""
        full = (text + tail).strip()
        if full:
            paragraphs.append(full)
    if not paragraphs:
        text = ET.tostring(article, encoding="unicode", method="text").strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def parse_nb_doc(xml_str: str | None) -> list[Section]:
    """Parse NB_DOC_DATA XML string into a list of Section objects."""
    if not xml_str:
        return []
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    sections = []
    order = 0
    for article in root.iter("ARTICLE"):
        title = article.get("title", "").strip()
        if not title:
            continue
        text = _extract_text(article)
        if not text:
            continue
        clean_title = re.sub(r"^\d+\.\s*", "", title)
        section_type = _classify_title(clean_title)
        sections.append(
            Section(
                section_type=section_type,
                section_title=title,
                section_text=text,
                section_order=order,
            )
        )
        order += 1
    return sections
