from pathlib import Path
from docx import Document
from starter2doc.core.engineering_model import EngineeringModel
from starter2doc.document import DocumentModelBuilder
from starter2doc.exporters import WordExporter


def test_word_exporter_creates_readable_docx(tmp_path: Path):
    model = EngineeringModel(source_path='Demo.zip', metadata={'version': '0.20.0'})
    document_model = DocumentModelBuilder().build(model)
    output = WordExporter().export(document_model, tmp_path / 'demo.docx')
    assert output.exists() and output.stat().st_size > 1000
    doc = Document(output)
    text = '\n'.join(p.text for p in doc.paragraphs)
    assert 'STARTER Project Documentation' in text
    assert 'Project Overview' in text
