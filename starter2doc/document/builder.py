from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from collections import Counter

from .model import DocumentModel, DocumentSection, Paragraph, Table, TableRow, KeyValueTable, PageBreak
from ..core.engineering_model import EngineeringModel


@dataclass(slots=True)
class DocumentBuildOptions:
    include_unused_appendix: bool = True
    include_internal_diagnostics: bool = False
    include_signal_paths: bool = False


class DocumentModelBuilder:
    """Transforms engineering data into presentation-neutral document content.

    The builder decides *what* appears and in which order. It contains no Word
    styling and does not infer engineering facts that are absent from the model.
    """

    def build(self, engineering: EngineeringModel, options: DocumentBuildOptions | None = None) -> DocumentModel:
        options = options or DocumentBuildOptions()
        source = Path(engineering.source_path).name if engineering.source_path else ''
        project_name = Path(source).stem if source else 'STARTER Project'
        version = str(engineering.metadata.get('version', '0.20.0'))
        document = DocumentModel(
            title='STARTER Project Documentation',
            subtitle='Engineering documentation generated from the STARTER project export',
            project_name=project_name,
            source_name=source,
            generated_by='Starter2Doc',
            version=version,
            metadata={'document_profile': 'standard'},
        )
        document.sections.append(self._overview(engineering))
        if engineering.resolver.pzd_bindings:
            document.sections.append(self._communication(engineering, options))
        if engineering.dcc.programs:
            document.sections.append(self._dcc(engineering, options))
        appendix = self._appendix(engineering, options)
        if appendix.sections or appendix.elements:
            document.sections.append(appendix)
        return document

    def _overview(self, model: EngineeringModel) -> DocumentSection:
        section = DocumentSection('Project Overview')
        program_count = len(model.dcc.programs)
        instance_count = sum(len(p.instances) for p in model.dcc.programs)
        connection_count = sum(len(p.connections) for p in model.dcc.programs)
        symbol_count = sum(len(p.symbols) for p in model.dcc.programs)
        rows = [
            ('Project file', Path(model.source_path).name if model.source_path else '-'),
            ('DCC programs', str(program_count)),
            ('DCC blocks', str(instance_count)),
            ('DCC connections', str(connection_count)),
            ('DCC symbols', str(symbol_count)),
            ('PZD bindings', str(len(model.resolver.pzd_bindings))),
            ('BICO connections', str(len(model.bico.links))),
            ('Used DCC blocks', str(model.dcc_usage.used_instances)),
            ('Unused DCC blocks', str(model.dcc_usage.not_used_instances)),
        ]
        section.elements.append(KeyValueTable(rows=rows))
        return section

    def _communication(self, model: EngineeringModel, options: DocumentBuildOptions) -> DocumentSection:
        root = DocumentSection('Communication')
        by_drive: dict[str, list] = {}
        for binding in model.resolver.pzd_bindings:
            by_drive.setdefault(binding.drive or 'Unassigned drive', []).append(binding)
        for drive, bindings in by_drive.items():
            sub = DocumentSection(drive, level=2)
            rows: list[TableRow] = []
            for b in sorted(bindings, key=lambda x: (x.direction, x.position, x.transport_reference)):
                resolved = b.resolved
                signal = ''
                if resolved:
                    signal = resolved.name or resolved.description or resolved.reference
                rows.append(TableRow([
                    b.direction.upper(), str(b.position), b.transport_reference,
                    signal or '-', b.program or '-', b.dcc_endpoint or '-'
                ]))
            sub.elements.append(Table(
                columns=['Direction', 'PZD', 'Transport reference', 'Signal', 'DCC program', 'DCC endpoint'],
                rows=rows,
                widths=[0.8, 0.6, 1.45, 1.6, 1.35, 2.25],
            ))
            if options.include_signal_paths:
                for b in bindings:
                    if b.signal_path and b.signal_path.steps:
                        path = '  →  '.join(step.endpoint for step in b.signal_path.steps)
                        sub.elements.append(Paragraph(f'PZD {b.position}: {path}', style='compact'))
            root.sections.append(sub)
        return root

    def _dcc(self, model: EngineeringModel, options: DocumentBuildOptions) -> DocumentSection:
        root = DocumentSection('DCC')
        usage_by_program = {u.program: u for u in model.dcc_usage.programs}
        for program in model.dcc.programs:
            usage = usage_by_program.get(program.name)
            used_names = set(usage.used_instances if usage else [i.name for i in program.instances])
            visible_instances = [i for i in program.instances if i.name in used_names]
            sub = DocumentSection(program.name or 'Unnamed program', level=2)
            sub.elements.append(KeyValueTable(rows=[
                ('Source', program.source_path or '-'),
                ('Used blocks', str(len(visible_instances))),
                ('Connections', str(len(usage.used_connections) if usage else len(program.connections))),
                ('Symbols', str(len(program.symbols))),
            ]))
            if visible_instances:
                rows = [TableRow([
                    instance.name,
                    instance.block_type or '-',
                    str(len(instance.inputs)),
                    str(len(instance.outputs)),
                ]) for instance in visible_instances]
                sub.elements.append(Table(
                    title='Used blocks',
                    columns=['Instance', 'Block type', 'Inputs', 'Outputs'],
                    rows=rows,
                    widths=[2.2, 2.5, 0.8, 0.8],
                ))
            else:
                sub.elements.append(Paragraph('No used DCC blocks were identified.', style='note'))

            parameter_symbols = [s for s in program.symbols if s.parameter_kind in {'p', 'r'}]
            if parameter_symbols:
                rows = [TableRow([
                    s.name, s.data_type or '-', s.address or '-', s.comment or '-'
                ]) for s in parameter_symbols]
                sub.elements.append(Table(
                    title='Parameter symbols',
                    columns=['Parameter', 'Data type', 'Address', 'Description'],
                    rows=rows,
                    widths=[1.1, 1.1, 1.6, 3.4],
                ))
            root.sections.append(sub)
        return root

    def _appendix(self, model: EngineeringModel, options: DocumentBuildOptions) -> DocumentSection:
        appendix = DocumentSection('Appendix')
        if options.include_unused_appendix and model.dcc_usage.not_used_instances:
            unused = DocumentSection('Unused DCC Blocks', level=2)
            rows: list[TableRow] = []
            for program in model.dcc_usage.programs:
                for name in program.not_used_instances:
                    rows.append(TableRow([program.program, name]))
            unused.elements.append(Paragraph(
                'These blocks remain part of the engineering model but do not reach an exported STARTER device-parameter sink.',
                style='note', keep_with_next=True,
            ))
            unused.elements.append(Table(
                columns=['DCC program', 'Instance'], rows=rows, widths=[2.7, 4.3]
            ))
            appendix.sections.append(unused)

        if options.include_internal_diagnostics:
            partial_bico = [p for p in model.bico_resolver.paths.values() if p.status not in {'terminal', 'parameter_resolved'}]
            if partial_bico:
                bico = DocumentSection('Open BICO References', level=2)
                rows = [TableRow([
                    p.start, p.end or '-', p.status, '; '.join(p.warnings) or '-'
                ]) for p in partial_bico]
                bico.elements.append(Table(
                    columns=['Start', 'End', 'Status', 'Note'], rows=rows,
                    widths=[1.6, 1.6, 1.2, 3.0]
                ))
                appendix.sections.append(bico)

        if options.include_internal_diagnostics and model.diagnostics.issues:
            diagnostics = DocumentSection('Internal Generation Notes', level=2)
            diagnostics.elements.append(Table(
                columns=['Severity', 'Code', 'Message'],
                rows=[TableRow([i.severity, i.code, i.message]) for i in model.diagnostics.issues],
                widths=[1.0, 1.3, 4.6],
            ))
            appendix.sections.append(diagnostics)
        return appendix
