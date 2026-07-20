from __future__ import annotations
import argparse
from pathlib import Path
from .core.dcc_parser import DCCParser
from .core.engineering_builder import EngineeringModelBuilder
from .core.signal_resolver import SignalResolver
from .document import DocumentModelBuilder, DocumentBuildOptions
from .exporters import WordExporter
from .reporting.debug_report import write_reports
from .reporting.engineering_report import write_engineering_reports
from .reporting.resolver_report import write_resolver_reports
from .reporting.usage_report import write_usage_reports


def main() -> int:
    ap = argparse.ArgumentParser(description='Starter2Doc 0.20.0')
    ap.add_argument('project_zip')
    ap.add_argument('-o', '--output', default='starter2doc_report')
    ap.add_argument('--word', action='store_true', help='Generate the clean Word documentation')
    ap.add_argument('--debug', action='store_true', help='Also write engineering JSON/TXT reports')
    ap.add_argument('--include-unused', action='store_true', help='Include unused DCC blocks in a compact appendix')
    ap.add_argument('--dcc-only', action='store_true')
    ap.add_argument('--resolver-only', action='store_true')
    ap.add_argument('--usage-only', action='store_true')
    args = ap.parse_args()

    if args.dcc_only:
        jp, tp = write_reports(DCCParser().parse_zip(args.project_zip), args.output)
        print(tp); print(jp); return 0
    if args.resolver_only:
        dcc = DCCParser().parse_zip(args.project_zip)
        jp, tp = write_resolver_reports(SignalResolver().resolve_dcc(dcc), args.output)
        print(tp); print(jp); return 0

    engineering = EngineeringModelBuilder().build_from_zip(args.project_zip)
    if args.usage_only:
        jp, tp = write_usage_reports(engineering, args.output)
        print(tp); print(jp); return 0

    # Word is the primary output in V0.20. --word remains accepted for clarity.
    out = Path(args.output)
    docx_path = out if out.suffix.lower() == '.docx' else out.with_suffix('.docx')
    document = DocumentModelBuilder().build(
        engineering,
        DocumentBuildOptions(include_unused_appendix=args.include_unused)
    )
    WordExporter().export(document, docx_path)
    print(docx_path)

    if args.debug:
        debug_base = str(out.parent / (out.stem + '_debug'))
        jp, tp = write_engineering_reports(engineering, debug_base)
        print(tp); print(jp)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
