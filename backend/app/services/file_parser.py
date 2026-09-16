"""Multi-format file parser with unified Markdown output."""
from pptx import Presentation
from docx import Document as DocxDocument
import fitz  # PyMuPDF


class FileParser:
    """Parse PPTX, DOCX, PDF to Markdown text."""

    def parse(self, file_path: str, file_type: str) -> tuple[str, int]:
        """
        Returns: (markdown_content, page_count)
        """
        if file_type == "pptx":
            return self._parse_pptx(file_path)
        elif file_type == "docx":
            return self._parse_docx(file_path)
        elif file_type == "pdf":
            return self._parse_pdf(file_path)
        elif file_type == "md":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read(), 1
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _parse_pptx(self, file_path: str) -> tuple[str, int]:
        prs = Presentation(file_path)
        pages = []
        for slide_num, slide in enumerate(prs.slides, 1):
            texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if text:
                            texts.append(text)
                if shape.has_table:
                    table = shape.table
                    for row in table.rows:
                        row_texts = [cell.text.strip() for cell in row.cells]
                        texts.append(" | ".join(row_texts))
            if texts:
                pages.append(f"## Slide {slide_num}\n\n" + "\n\n".join(texts))
        return "\n\n---\n\n".join(pages), len(prs.slides)

    def _parse_docx(self, file_path: str) -> tuple[str, int]:
        doc = DocxDocument(file_path)
        parts = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                if para.style.name.startswith("Heading"):
                    level = para.style.name.replace("Heading ", "")
                    prefix = "#" * min(int(level), 6)
                    parts.append(f"\n{prefix} {text}\n")
                else:
                    parts.append(text)
        return "\n\n".join(parts), len(doc.paragraphs)

    def _parse_pdf(self, file_path: str) -> tuple[str, int]:
        doc = fitz.open(file_path)
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages.append(text.strip())
        return "\n\n---\n\n".join(pages), len(doc)
