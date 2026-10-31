"""Extract product source documents as Markdown for AI profile drafting."""

from io import BytesIO
from shutil import which
from threading import Lock


_CONVERTER = None
_CONVERTER_LOCK = Lock()
_SUPPORTED_OFFICE_FORMATS = {"docx", "ppt", "pptx"}


def extract_document_text(filename: str, content: bytes) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension == "md":
        return content.decode("utf-8-sig").strip()
    if extension not in _SUPPORTED_OFFICE_FORMATS:
        raise ValueError("仅支持 .docx、.md、.ppt 和 .pptx 文档")
    if extension == "ppt" and not (which("soffice") or which("libreoffice")):
        raise ValueError("解析旧版 .ppt 需要在服务器安装 LibreOffice，或将文件另存为 .pptx")

    from docling.datamodel.base_models import DocumentStream
    from docling.exceptions import ConversionError

    global _CONVERTER
    try:
        with _CONVERTER_LOCK:
            if _CONVERTER is None:
                from docling.document_converter import DocumentConverter

                _CONVERTER = DocumentConverter()
            source = DocumentStream(name=filename, stream=BytesIO(content))
            result = _CONVERTER.convert(source)
    except ConversionError as exc:
        raise ValueError("无法解析该文档，请确认文件未损坏并使用标准 DOCX/PPT/PPTX 格式") from exc

    try:
        return result.document.export_to_markdown().strip()
    finally:
        result.input.release()
