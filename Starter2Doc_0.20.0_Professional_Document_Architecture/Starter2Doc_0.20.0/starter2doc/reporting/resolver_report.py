from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from ..core.models import SignalResolverModel


def summary(model: SignalResolverModel) -> dict:
    signals = list(model.signals.values())
    bindings = model.pzd_bindings
    return {
        'signal_count': len(signals),
        'signals_with_description': sum(bool(s.description) for s in signals),
        'signals_with_warnings': sum(bool(s.warnings) for s in signals),
        'pzd_binding_count': len(bindings),
        'resolved_pzd_binding_count': sum(bool(b.resolved and b.resolved.is_resolved) for b in bindings),
        'rx_binding_count': sum(b.direction == 'RX' for b in bindings),
        'tx_binding_count': sum(b.direction == 'TX' for b in bindings),
        'warnings': model.warnings,
    }


def write_resolver_reports(model: SignalResolverModel, output_base: str) -> tuple[str, str]:
    base = Path(output_base)
    json_path = str(base.with_suffix('.json'))
    txt_path = str(base.with_suffix('.txt'))
    payload = {'summary': summary(model), 'resolver': asdict(model)}
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    s = payload['summary']
    lines = [
        'Starter2Doc SignalResolver Analyse V0.14',
        '=' * 48,
        f"DCC-Signale: {s['signal_count']}",
        f"Signale mit Beschreibung: {s['signals_with_description']}",
        f"PZD-DCC-Verknüpfungen: {s['pzd_binding_count']}",
        f"Davon RX: {s['rx_binding_count']}",
        f"Davon TX: {s['tx_binding_count']}",
        '', 'PZD-Verknüpfungen:'
    ]
    for b in model.pzd_bindings:
        r = b.resolved
        desc = (r.description or r.name) if r else 'nicht aufgelöst'
        ref = r.reference if r else ''
        warning = ' ⚠' if r and r.warnings else ''
        path = ''
        if b.signal_path and b.signal_path.steps:
            path = ' | Pfad: ' + ' -> '.join(step.endpoint for step in b.signal_path.steps)
        lines.append(f"- {b.drive} {b.direction} PZD{b.position}: {b.transport_reference} -> {b.dcc_endpoint} -> {ref} | {desc}{warning}{path}")
    lines += ['', 'Beispielhafte aufgelöste DCC-Signale:']
    for signal in list(model.signals.values())[:40]:
        lines.append(f"- {signal.reference} [{signal.data_type}] -> {signal.description or signal.name}")
    Path(txt_path).write_text('\n'.join(lines), encoding='utf-8')
    return json_path, txt_path
