from __future__ import annotations
import json
from pathlib import Path
from ..core.engineering_model import EngineeringModel


def write_engineering_reports(model: EngineeringModel, output_base: str) -> tuple[str, str]:
    base = Path(output_base)
    json_path = str(base.with_suffix('.json'))
    txt_path = str(base.with_suffix('.txt'))
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(model.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
    c = model.diagnostics.coverage
    lines = [
        'Starter2Doc Engineering Analyse V0.19',
        '=' * 48,
        f'Quelle: {model.source_path}',
        '',
        'Engineering Model:',
        f'- DCC-Programme: {c.programs}',
        f'- DCC-Instanzen: {c.instances}',
        f'- DCC-Verbindungen: {c.connections}',
        f'- DCC-Symbole: {c.symbols}',
        f'- Graph-Knoten: {c.graph_nodes}',
        f'- Graph-Kanten: {c.graph_edges}',
        '',
        'Coverage:',
        f'- PZD-Verknüpfungen: {c.pzd_bindings}',
        f'- Eindeutig aufgelöst: {c.resolved_pzd_bindings} ({c.signal_resolution_percent:.2f} %)',
        f'- Signalpfad erweitert: {c.traced_pzd_bindings} ({c.trace_coverage_percent:.2f} %)',
        f'- Bis DCC-Symbol vollständig: {c.complete_trace_bindings} ({c.complete_trace_percent:.2f} %)',
        f'- Nicht eindeutig aufgelöst: {c.unresolved_bindings}',
        f'- Parser-Warnungen: {c.parser_warnings}',
        '',
        'DCC Usage:',
        f'- Verwendete Instanzen: {model.dcc_usage.used_instances}',
        f'- Not used Instanzen: {model.dcc_usage.not_used_instances}',
        f'- Verwendete Verbindungen: {model.dcc_usage.used_connections}',
        f'- Not used Verbindungen: {model.dcc_usage.not_used_connections}',
        '',
        'PZD-Verknüpfungen:',
    ]
    for b in model.resolver.pzd_bindings:
        resolved = b.resolved
        ref = resolved.reference if resolved else ''
        desc = (resolved.description or resolved.name) if resolved else 'nicht aufgelöst'
        path = ' -> '.join(step.endpoint for step in b.signal_path.steps) if b.signal_path else ''
        status = 'OK' if b.signal_path and b.signal_path.matched_reference else 'OFFEN'
        lines.append(f'- [{status}] {b.drive} {b.direction} PZD{b.position}: {b.transport_reference} -> {ref} | {desc}')
        if path:
            lines.append(f'  Pfad: {path}')
    lines += ['', 'Diagnostics:']
    if not model.diagnostics.issues:
        lines.append('- Keine Auffälligkeiten')
    else:
        for issue in model.diagnostics.issues:
            context = ' / '.join(x for x in (issue.program, issue.reference) if x)
            lines.append(f'- {issue.severity.upper()} {issue.code}: {issue.message}' + (f' [{context}]' if context else ''))
    Path(txt_path).write_text('\n'.join(lines), encoding='utf-8')
    return json_path, txt_path
