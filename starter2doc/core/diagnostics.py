from __future__ import annotations
from .engineering_model import CoverageMetrics, DiagnosticIssue, EngineeringDiagnostics, EngineeringModel


class DiagnosticsBuilder:
    def build(self, model: EngineeringModel) -> EngineeringDiagnostics:
        dcc = model.dcc
        resolver = model.resolver
        bindings = resolver.pzd_bindings
        coverage = CoverageMetrics(
            programs=len(dcc.programs),
            instances=sum(len(p.instances) for p in dcc.programs),
            connections=sum(len(p.connections) for p in dcc.programs),
            symbols=sum(len(p.symbols) for p in dcc.programs),
            graph_nodes=len(model.graph.nodes),
            graph_edges=len(model.graph.edges),
            pzd_bindings=len(bindings),
            resolved_pzd_bindings=sum(bool(b.resolved and b.resolved.is_resolved and b.resolved.source != 'DCC endpoint') for b in bindings),
            traced_pzd_bindings=sum(bool(b.signal_path and len(b.signal_path.steps) > 1) for b in bindings),
            complete_trace_bindings=sum(bool(b.signal_path and b.signal_path.matched_reference) for b in bindings),
            parser_warnings=sum(len(p.parse_warnings) for p in dcc.programs),
        )
        coverage.unresolved_bindings = coverage.pzd_bindings - coverage.resolved_pzd_bindings
        issues: list[DiagnosticIssue] = []
        for program in dcc.programs:
            for warning in program.parse_warnings:
                issues.append(DiagnosticIssue('warning', 'DCC_PARSE_WARNING', warning, program.name))
        for binding in bindings:
            if not binding.signal_path or len(binding.signal_path.steps) <= 1:
                issues.append(DiagnosticIssue('warning', 'TRACE_NOT_EXTENDED',
                    f'{binding.direction} PZD{binding.position} endet am Startknoten', binding.program, binding.dcc_endpoint))
            if not binding.signal_path or not binding.signal_path.matched_reference:
                issues.append(DiagnosticIssue('warning', 'TRACE_NO_SYMBOL_MATCH',
                    f'{binding.direction} PZD{binding.position} ist keinem exportierten DCC-Symbol eindeutig zugeordnet',
                    binding.program, binding.dcc_endpoint))
            if binding.signal_path:
                for warning in binding.signal_path.warnings:
                    issues.append(DiagnosticIssue('info', 'TRACE_WARNING', warning, binding.program, binding.dcc_endpoint))
        return EngineeringDiagnostics(coverage=coverage, issues=issues)
