from __future__ import annotations
import json
from pathlib import Path
from dataclasses import asdict
from ..core.models import DCCModel


def summary(model: DCCModel) -> dict:
    syms = model.symbols
    return {
        'program_count': len(model.programs),
        'symbol_count': len(syms),
        'p_symbol_count': sum(s.parameter_kind == 'p' for s in syms),
        'r_symbol_count': sum(s.parameter_kind == 'r' for s in syms),
        'commented_symbol_count': sum(bool(s.comment) for s in syms),
        'instance_count': sum(len(p.instances) for p in model.programs),
        'connection_count': len(model.connections),
        'stored_value_count': sum(len(p.values) for p in model.programs),
        'warnings': [w for p in model.programs for w in p.parse_warnings],
        'programs': [
            {
                'name': p.name,
                'source_path': p.source_path,
                'symbols': len(p.symbols),
                'instances': len(p.instances),
                'connections': len(p.connections),
                'values': len(p.values),
                'warnings': p.parse_warnings,
            } for p in model.programs
        ],
    }


def write_reports(model: DCCModel, output_base: str) -> tuple[str, str]:
    base = Path(output_base)
    json_path = str(base.with_suffix('.json'))
    txt_path = str(base.with_suffix('.txt'))
    payload = {'summary': summary(model), 'dcc': asdict(model)}
    Path(json_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    s = payload['summary']
    lines = [
        'Starter2Doc DCC Analyse V0.12',
        '=' * 40,
        f"DCC-Programme: {s['program_count']}",
        f"Symbole gesamt: {s['symbol_count']}",
        f"p-Symbole: {s['p_symbol_count']}",
        f"r-Symbole: {s['r_symbol_count']}",
        f"Symbole mit Kommentar: {s['commented_symbol_count']}",
        f"Bausteininstanzen: {s['instance_count']}",
        f"Verbindungen: {s['connection_count']}",
        f"Gespeicherte Werte: {s['stored_value_count']}",
        '', 'Programme:'
    ]
    for p in s['programs']:
        lines.append(f"- {p['name']}: {p['symbols']} Symbole, {p['instances']} Instanzen, {p['connections']} Verbindungen, {p['values']} Werte")
    commented = [x for x in model.symbols if x.comment][:30]
    lines.extend(['', 'Beispielhafte DCC-Symbole:'])
    lines.extend(f"- {x.name} [{x.data_type}] -> {x.comment}" for x in commented)
    if s['warnings']:
        lines.extend(['', 'Warnungen:'] + [f'- {w}' for w in s['warnings']])
    Path(txt_path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return json_path, txt_path
