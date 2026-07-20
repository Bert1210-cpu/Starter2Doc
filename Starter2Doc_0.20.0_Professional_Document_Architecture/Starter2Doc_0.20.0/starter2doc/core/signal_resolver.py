from __future__ import annotations
import re
from dataclasses import replace
from .signal_tracer import SignalTracer
from .models import (
    DCCModel, DCCSymbol, SignalEvidence, ResolvedSignal,
    PZDBinding, SignalResolverModel,
)

_PARAM_RE = re.compile(r"(?i)(?<![A-Za-z0-9_])([pr]\d+(?:\[\d+\])?(?:\.\d+)?)")
_PZD_RX_RE = re.compile(r"(?i)_device#(?P<drive>[^.]+)\.(?P<ref>r20(?:50|60)\[(?P<index>\d+)\])")
_PZD_TX_RE = re.compile(r"(?i)_device#(?P<drive>[^.]+)\.(?P<ref>p20(?:51|61)\[(?P<index>\d+)\])")


def _key(value: str) -> str:
    return value.strip().lower()


def _endpoint_label(endpoint: str) -> str:
    # ._DCC_1_PB_COMMANDWORD.IS -> PB_COMMANDWORD
    text = endpoint.strip().lstrip('.')
    text = re.sub(r"^_+", "", text)
    text = re.sub(r"(?i)^dcc_?\d*_", "", text)
    text = text.split('.', 1)[0]
    return text.strip('_')


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


class SignalResolver:
    """Combines DCC symbols, DCC connections and traced paths into resolved signals."""

    def __init__(self) -> None:
        self.tracer = SignalTracer()

    def resolve_dcc(self, dcc: DCCModel) -> SignalResolverModel:
        result = SignalResolverModel()
        grouped: dict[str, list[tuple[DCCSymbol, str, str]]] = {}
        for program in dcc.programs:
            for symbol in program.symbols:
                if not symbol.name:
                    continue
                grouped.setdefault(_key(symbol.name), []).append((symbol, program.name, program.source_path))

        for ref, entries in grouped.items():
            result.signals[ref] = self._merge_symbol_entries(ref, entries)

        seen_bindings: set[tuple[str, str, int, str]] = set()
        for program in dcc.programs:
            for connection in program.connections:
                for direction, regex, external, endpoint in (
                    ('RX', _PZD_RX_RE, connection.source, connection.target),
                    ('TX', _PZD_TX_RE, connection.target, connection.source),
                ):
                    match = regex.search(external)
                    if not match:
                        continue
                    position = int(match.group('index')) + 1
                    drive = match.group('drive')
                    transport_ref = match.group('ref')
                    signature = (drive.lower(), direction, position, endpoint.lower())
                    if signature in seen_bindings:
                        continue
                    seen_bindings.add(signature)
                    signal_path = self.tracer.trace_and_resolve(program, endpoint, result.signals)
                    resolved = self._resolve_endpoint(endpoint, program, result)
                    if signal_path.matched_reference:
                        traced = result.signals.get(signal_path.matched_reference.lower())
                        if traced is not None:
                            resolved = replace(traced)
                            resolved.evidences = list(traced.evidences) + [SignalEvidence(
                                source='DCC signal path',
                                value=' -> '.join(step.endpoint for step in signal_path.steps),
                                source_path=program.source_path,
                                program=program.name,
                                confidence=signal_path.confidence,
                            )]
                        elif resolved.source == 'DCC endpoint':
                            # Only use an external BICO/device boundary when the endpoint
                            # itself could not already be resolved to an exported DCC symbol.
                            # Exported STARTER symbols remain the stronger source of truth.
                            label = signal_path.matched_description or _endpoint_label(endpoint)
                            resolved = ResolvedSignal(
                                reference=signal_path.matched_reference,
                                name=label,
                                description=label,
                                source='DCC signal path',
                                program=program.name,
                                source_path=program.source_path,
                                evidences=[SignalEvidence(
                                    source='DCC signal path',
                                    value=' -> '.join(step.endpoint for step in signal_path.steps),
                                    source_path=program.source_path,
                                    program=program.name,
                                    confidence=signal_path.confidence,
                                )],
                            )
                    result.pzd_bindings.append(PZDBinding(
                        drive=drive,
                        direction=direction,
                        position=position,
                        transport_reference=transport_ref,
                        dcc_endpoint=endpoint,
                        program=program.name,
                        resolved=resolved,
                        signal_path=signal_path,
                    ))

        result.pzd_bindings.sort(key=lambda b: (b.drive.lower(), b.direction, b.position, b.dcc_endpoint.lower()))
        return result

    @staticmethod
    def _merge_symbol_entries(ref: str, entries: list[tuple[DCCSymbol, str, str]]) -> ResolvedSignal:
        # Prefer a non-empty comment; otherwise retain the exported symbol name.
        best_symbol, best_program, best_path = max(
            entries,
            key=lambda item: (bool(item[0].comment), bool(item[0].data_type), len(item[0].comment)),
        )
        descriptions = []
        evidences = []
        for symbol, program, path in entries:
            if symbol.comment and symbol.comment not in descriptions:
                descriptions.append(symbol.comment)
            evidences.append(SignalEvidence(
                source='DCC symbol',
                value=symbol.comment or symbol.name,
                source_path=path,
                program=program,
                confidence=1.0,
            ))
        warnings = []
        if len(descriptions) > 1:
            warnings.append('Mehrere unterschiedliche DCC-Kommentare für dasselbe Signal: ' + ' | '.join(descriptions))
        return ResolvedSignal(
            reference=best_symbol.name,
            name=best_symbol.name,
            description=best_symbol.comment,
            data_type=best_symbol.data_type,
            source='DCC',
            program=best_program,
            source_path=best_path,
            evidences=evidences,
            warnings=warnings,
        )

    def _resolve_endpoint(self, endpoint: str, program, model: SignalResolverModel) -> ResolvedSignal:
        label = _endpoint_label(endpoint)
        label_norm = _norm(label)

        # Exact parameter reference embedded in endpoint has highest confidence.
        param_match = _PARAM_RE.search(endpoint)
        if param_match:
            ref = _key(param_match.group(1))
            if ref in model.signals:
                return replace(model.signals[ref])

        candidates: list[tuple[int, ResolvedSignal]] = []
        for signal in model.signals.values():
            if signal.program != program.name:
                continue
            comment_norm = _norm(signal.description)
            name_norm = _norm(signal.name)
            score = 0
            if label_norm and label_norm == comment_norm:
                score = 100
            elif label_norm and label_norm == name_norm:
                score = 95
            elif label_norm and comment_norm and label_norm in comment_norm:
                score = 80
            elif label_norm and comment_norm and comment_norm in label_norm:
                score = 70
            if score:
                candidates.append((score, signal))

        if candidates:
            candidates.sort(key=lambda item: (item[0], len(item[1].description)), reverse=True)
            best_score, best = candidates[0]
            resolved = replace(best)
            resolved.evidences = list(best.evidences) + [SignalEvidence(
                source='DCC connection endpoint', value=endpoint,
                source_path=program.source_path, program=program.name,
                confidence=best_score / 100,
            )]
            return resolved

        # The endpoint itself is still useful project information and must not be discarded.
        return ResolvedSignal(
            reference=endpoint,
            name=label,
            description=label.replace('_', ' '),
            source='DCC endpoint',
            program=program.name,
            source_path=program.source_path,
            evidences=[SignalEvidence(
                source='DCC connection endpoint', value=endpoint,
                source_path=program.source_path, program=program.name,
                confidence=0.6,
            )],
            warnings=['Kein eindeutiges exportiertes DCC-Symbol zum Endpunkt gefunden'],
        )
