from __future__ import annotations
import json
from pathlib import Path

from ..core.engineering_model import EngineeringModel


def write_usage_reports(model: EngineeringModel, output_base: str) -> tuple[str, str]:
    base = Path(output_base)
    json_path = str(base.with_suffix('.json'))
    txt_path = str(base.with_suffix('.txt'))
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(
        json.dumps(model.dcc_usage.to_dict(), ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    usage = model.dcc_usage
    lines = [
        'Starter2Doc DCC Usage Analyse V0.19',
        '=' * 48,
        f'Quelle: {model.source_path}',
        '',
        f'Verwendete DCC-Instanzen: {usage.used_instances}',
        f'Nicht verwendete DCC-Instanzen: {usage.not_used_instances}',
        f'Verwendete DCC-Verbindungen: {usage.used_connections}',
        f'Nicht verwendete DCC-Verbindungen: {usage.not_used_connections}',
    ]
    for program in usage.programs:
        lines += [
            '',
            f'Programm: {program.program}',
            f'- Verwendet: {len(program.used_instances)} Instanzen / {len(program.used_connections)} Verbindungen',
            f'- Not used: {len(program.not_used_instances)} Instanzen / {len(program.not_used_connections)} Verbindungen',
        ]
        if program.not_used_instances:
            lines.append('- Nicht verwendete Instanzen:')
            lines.extend(f'  - {name}' for name in program.not_used_instances)
    Path(txt_path).write_text('\n'.join(lines), encoding='utf-8')
    return json_path, txt_path
