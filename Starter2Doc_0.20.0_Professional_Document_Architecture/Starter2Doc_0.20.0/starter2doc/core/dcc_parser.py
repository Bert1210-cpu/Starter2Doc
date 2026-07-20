from __future__ import annotations
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from .models import DCCModel, DCCProgram, DCCSymbol, DCCInstance, DCCPin, DCCConnection

_FRAGMENT_RE = re.compile(r"<\?xml[^>]*\?>\s*(<(?P<tag>SymExport|PLAN|PLAN_OA|PLAN_ALIASES)\b.*?</(?P=tag)>)", re.S | re.I)


def _local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def _safe_xml(text: str) -> ET.Element | None:
    text = text.strip().lstrip('\ufeff')
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        return None


def _embedded_fragments(data: str) -> list[tuple[str, ET.Element]]:
    fragments: list[tuple[str, ET.Element]] = []
    for match in _FRAGMENT_RE.finditer(data):
        root = _safe_xml(match.group(1))
        if root is not None:
            fragments.append((_local(root.tag), root))
    return fragments


class DCCParser:
    """Reads DCC exports from a STARTER project ZIP without interpreting telegram semantics."""

    def parse_zip(self, zip_path: str) -> DCCModel:
        model = DCCModel()
        with zipfile.ZipFile(zip_path) as archive:
            members = [n for n in archive.namelist() if n.lower().endswith('/ieximport.xml')]
            # Only program-local IExImport.xml files. The Programs/IExImport.xml is a library manifest.
            members = [n for n in members if '/programs/' in n.lower() and n.lower().count('/programs/') == 1 and len(PurePosixPath(n).parts) >= 3]
            for member in members:
                parent = PurePosixPath(member).parent
                if parent.name.lower() == 'programs':
                    continue
                program = DCCProgram(name=parent.name, source_path=member)
                try:
                    outer = ET.fromstring(archive.read(member))
                    data_node = next((e for e in outer.iter() if _local(e.tag) == 'Data'), None)
                    data = data_node.text if data_node is not None and data_node.text else ''
                    fragments = _embedded_fragments(data)
                    if not fragments:
                        program.parse_warnings.append('No embedded XML fragments detected')
                    for kind, root in fragments:
                        if kind == 'SymExport':
                            self._parse_symbols(root, program)
                        elif kind == 'PLAN':
                            self._parse_plan(root, program)
                        elif kind == 'PLAN_OA':
                            self._parse_values(root, program)
                except Exception as exc:
                    program.parse_warnings.append(f'{type(exc).__name__}: {exc}')
                model.programs.append(program)
        return model

    @staticmethod
    def _parse_symbols(root: ET.Element, program: DCCProgram) -> None:
        for node in root.iter():
            if _local(node.tag) != 'Symbol':
                continue
            props = {p.attrib.get('Name', ''): p.attrib.get('Val', '')
                     for p in node if _local(p.tag) == 'Property'}
            direction = None
            if props.get('Direction', '').lstrip('-').isdigit():
                direction = int(props['Direction'])
            program.symbols.append(DCCSymbol(
                name=node.attrib.get('Name', ''),
                data_type=node.attrib.get('Type', ''),
                symbol_type=node.attrib.get('SymType', ''),
                address=node.attrib.get('Addr', ''),
                unit_scope=node.attrib.get('UnitScope', ''),
                direction=direction,
                comment=props.get('Comment', '').strip(),
                initial_value=node.attrib.get('Init', ''),
                properties=props,
            ))

    @staticmethod
    def _parse_plan(root: ET.Element, program: DCCProgram) -> None:
        for node in root.iter():
            tag = _local(node.tag)
            if tag == 'INSTANCE':
                inst = DCCInstance(
                    name=node.attrib.get('Name', node.attrib.get('InstanceName', '')),
                    block_type=node.attrib.get('Type', node.attrib.get('BlockType', node.attrib.get('DCBType', ''))),
                    instance_id=node.attrib.get('ID', node.attrib.get('Id', '')),
                )
                for child in node.iter():
                    ctag = _local(child.tag)
                    if ctag in {'INPUT', 'OUTPUT', 'PIN'}:
                        pin = DCCPin(
                            name=child.attrib.get('Name', ''),
                            pin_type=ctag.lower(),
                            data_type=child.attrib.get('Type', child.attrib.get('Datatype', '')),
                            value=child.attrib.get('Val', child.attrib.get('Value', '')),
                            comment=child.attrib.get('Comment', ''),
                            default=child.attrib.get('Default', ''),
                            attributes=dict(child.attrib),
                        )
                        (inst.outputs if ctag == 'OUTPUT' else inst.inputs).append(pin)
                program.instances.append(inst)
            elif tag == 'LINK':
                attrs = dict(node.attrib)
                source = attrs.get('Source') or attrs.get('Src') or attrs.get('From') or attrs.get('Out') or ''
                target = attrs.get('Target') or attrs.get('Dst') or attrs.get('To') or attrs.get('In') or ''
                if not source or not target:
                    values = list(attrs.values())
                    if len(values) >= 2:
                        source, target = values[0], values[1]
                program.connections.append(DCCConnection(source=source, target=target, raw_attributes=attrs))

    @staticmethod
    def _parse_values(root: ET.Element, program: DCCProgram) -> None:
        for node in root.iter():
            if _local(node.tag) == 'VAL':
                name = node.attrib.get('Name', '')
                if name:
                    program.values[name] = node.attrib.get('Val', '')
