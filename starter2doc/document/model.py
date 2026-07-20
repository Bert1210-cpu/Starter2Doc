from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(slots=True)
class Paragraph:
    text: str
    style: str = 'body'
    keep_with_next: bool = False


@dataclass(slots=True)
class TableRow:
    cells: list[str]


@dataclass(slots=True)
class Table:
    columns: list[str]
    rows: list[TableRow] = field(default_factory=list)
    title: str = ''
    widths: list[float] = field(default_factory=list)
    repeat_header: bool = True


@dataclass(slots=True)
class KeyValueTable:
    rows: list[tuple[str, str]] = field(default_factory=list)
    title: str = ''


@dataclass(slots=True)
class PageBreak:
    pass


DocumentElement = Paragraph | Table | KeyValueTable | PageBreak


@dataclass(slots=True)
class DocumentSection:
    title: str
    level: int = 1
    elements: list[DocumentElement] = field(default_factory=list)
    sections: list['DocumentSection'] = field(default_factory=list)


@dataclass(slots=True)
class DocumentModel:
    title: str
    subtitle: str = ''
    project_name: str = ''
    generated_by: str = 'Starter2Doc'
    version: str = ''
    source_name: str = ''
    sections: list[DocumentSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
