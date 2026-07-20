from __future__ import annotations
import json
from pathlib import Path
from starter2doc.core.bico_parser import BICOModel
from starter2doc.core.bico_resolver import BICOResolverModel
from starter2doc.core.bico_analysis import BICOAnalysisModel


def write_bico_report(model: BICOModel, resolved: BICOResolverModel, path: str,
                      analysis: BICOAnalysisModel | None = None) -> None:
    out = Path(path); out.parent.mkdir(parents=True, exist_ok=True)
    lines = ['Starter2Doc BICO Report', '=======================', '']
    lines += [f'Parameter values scanned: {len(model.parameter_values)}',
              f'BICO links decoded: {len(model.links)}', f'BICO paths: {len(resolved.paths)}', '']
    if analysis:
        lines += ['Selector analysis', '-----------------',
                  f'Unique selectors: {analysis.unique_selectors}',
                  f'Resolution status: {analysis.status_counts}',
                  f'Selector kinds: {analysis.selector_kind_counts}',
                  f'Endpoint kinds: {analysis.endpoint_counts}', '']
        for group in analysis.groups:
            lines.append(f'{group.hex_value}: {group.count} | high=0x{group.high_byte:02X} '
                         f'low={group.low_byte} | {group.selector_kind}')
            for sink, source in zip(group.example_sinks, group.example_sources):
                lines.append(f'  {sink} <- {source}')
        lines.append('')
    lines += ['Resolved paths', '--------------']
    for key in sorted(resolved.paths):
        item=resolved.paths[key]
        chain=' -> '.join([item.start]+[link.source_reference for link in item.links])
        lines.append(f'{key}: [{item.status}] {chain}')
        for warning in item.warnings: lines.append(f'  WARNING: {warning}')
    out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    payload={'bico':model.to_dict(),'resolved':resolved.to_dict()}
    if analysis: payload['analysis']=analysis.to_dict()
    out.with_suffix('.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
