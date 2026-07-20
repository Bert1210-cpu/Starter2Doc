from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import PurePosixPath

_PARAM_RE = re.compile(r'(?i)^([pr])(\d+)(?:\[(\d+)\])?$')


def _local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


class SelectorKind(str, Enum):
    LOCAL_SCALAR = 'local_scalar'
    OBJECT_SCALAR = 'object_scalar'
    BIT_OR_INDEX_CANDIDATE = 'bit_or_index_candidate'
    OPAQUE = 'opaque'


class EndpointKind(str, Enum):
    PARAMETER = 'parameter'
    DEFAULT_REFERENCE = 'default_reference'
    UNKNOWN = 'unknown'


class ResolutionStatus(str, Enum):
    PARAMETER_RESOLVED = 'parameter_resolved'
    SELECTOR_PARTIAL = 'selector_partial'
    UNRESOLVED = 'unresolved'


@dataclass(slots=True)
class ParameterValue:
    object_name: str
    reference: str
    value: int
    value_type: str = ''
    source_path: str = ''


@dataclass(slots=True)
class BICOLink:
    object_name: str
    sink_reference: str
    source_reference: str
    raw_value: int
    selector: int
    source_parameter_number: int
    selector_kind: str = SelectorKind.OPAQUE.value
    resolution_status: str = ResolutionStatus.SELECTOR_PARTIAL.value
    endpoint_kind: str = EndpointKind.PARAMETER.value
    source_index: int | None = None
    source_bit: int | None = None
    selector_low_byte: int = 0
    source_object_selector: int | None = None
    source_object_name: str | None = None
    source_path: str = ''
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BICOModel:
    parameter_values: list[ParameterValue] = field(default_factory=list)
    links: list[BICOLink] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BICOParser:
    """Reads packed SINAMICS BICO connector values from object-local ISymbol.xml.

    Proven decoding boundary in V0.18:
    * upper 16 bits: selected source r-parameter number
    * lower 16 bits: selector retained and structurally classified

    Object, bit and index meaning are deliberately not asserted unless supported by
    project structure. This prevents plausible-looking but unverified references.
    """

    def parse_zip(self, zip_path: str) -> BICOModel:
        model = BICOModel()
        with zipfile.ZipFile(zip_path) as archive:
            members = [n for n in archive.namelist()
                       if n.lower().endswith('/isymbol.xml') and '/programs/' not in n.lower()]
            for member in members:
                object_name = PurePosixPath(member).parent.name
                try:
                    root = ET.fromstring(archive.read(member))
                except Exception as exc:
                    model.warnings.append(f'{member}: {type(exc).__name__}: {exc}')
                    continue
                self._parse_symbols(root, member, object_name, model)
        return model

    def _parse_symbols(self, root: ET.Element, member: str, object_name: str, model: BICOModel) -> None:
        for symbol in root.iter():
            if _local(symbol.tag) != 'Symbol':
                continue
            reference = symbol.attrib.get('Name', '')
            match = _PARAM_RE.match(reference)
            if not match or match.group(1).lower() != 'p':
                continue
            value_node = next((c for c in symbol if _local(c.tag) == 'Value'), None)
            if value_node is None:
                continue
            value_type = value_node.attrib.get('Type', '')
            descriptor = next((c for c in symbol if _local(c.tag) == 'ESSymbolDescr'), None)
            type_spec = descriptor.attrib.get('TypeSpec', '') if descriptor is not None else ''
            raw = value_node.attrib.get('Value', '')
            if value_type != 'VT_UI4' or type_spec != 'ES_UDOUBLEINT' or not raw.isdigit():
                continue
            value = int(raw)
            model.parameter_values.append(ParameterValue(
                object_name=object_name, reference=reference, value=value,
                value_type=value_type, source_path=member,
            ))
            link = self.decode_connector(object_name, reference, value, member)
            if link is not None:
                model.links.append(link)

    @staticmethod
    def decode_connector(object_name: str, sink_reference: str, value: int,
                         source_path: str = '') -> BICOLink | None:
        # Explicit non-links.
        if value < 0x10000 or value == 0xFFFFFFFF:
            return None
        source_parameter = (value >> 16) & 0xFFFF
        selector = value & 0xFFFF
        if source_parameter == 0:
            return None

        high = (selector >> 8) & 0xFF
        low = selector & 0xFF
        warnings: list[str] = []

        if selector == 0:
            selector_kind = SelectorKind.LOCAL_SCALAR.value
            status = ResolutionStatus.PARAMETER_RESOLVED.value
            confidence = 1.0
            source_object_name = object_name
        elif low == 0:
            selector_kind = SelectorKind.OBJECT_SCALAR.value
            status = ResolutionStatus.SELECTOR_PARTIAL.value
            confidence = 0.9
            source_object_name = None
            warnings.append(f'Object selector 0x{high:02X} is not mapped to an engineering object')
        elif 1 <= low <= 31:
            selector_kind = SelectorKind.BIT_OR_INDEX_CANDIDATE.value
            status = ResolutionStatus.SELECTOR_PARTIAL.value
            confidence = 0.8
            source_object_name = object_name if high == 0 else None
            warnings.append(
                f'Selector 0x{selector:04X}: low byte {low} may encode bit or index; meaning not yet proven'
            )
            if high != 0:
                warnings.append(f'Object selector 0x{high:02X} is not mapped to an engineering object')
        else:
            selector_kind = SelectorKind.OPAQUE.value
            status = ResolutionStatus.SELECTOR_PARTIAL.value
            confidence = 0.65
            source_object_name = None
            warnings.append(f'Opaque connector selector 0x{selector:04X} retained without interpretation')

        source_reference = f'r{source_parameter}'
        endpoint_kind = (EndpointKind.DEFAULT_REFERENCE.value
                         if source_parameter == 1 else EndpointKind.PARAMETER.value)
        if source_parameter == 1:
            warnings.append('r1 classified as default/reference endpoint; semantic meaning requires STARTER validation')

        return BICOLink(
            object_name=object_name,
            sink_reference=sink_reference,
            source_reference=source_reference,
            raw_value=value,
            selector=selector,
            source_parameter_number=source_parameter,
            selector_kind=selector_kind,
            resolution_status=status,
            endpoint_kind=endpoint_kind,
            selector_low_byte=low,
            source_object_selector=high,
            source_object_name=source_object_name,
            source_path=source_path,
            confidence=confidence,
            warnings=warnings,
        )
