from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional

@dataclass(slots=True)
class DCCSymbol:
    name: str
    data_type: str = ""
    symbol_type: str = ""
    address: str = ""
    unit_scope: str = ""
    direction: Optional[int] = None
    comment: str = ""
    initial_value: str = ""
    properties: dict[str, str] = field(default_factory=dict)

    @property
    def parameter_kind(self) -> str:
        n = self.name.lower()
        if n.startswith("p"): return "p"
        if n.startswith("r"): return "r"
        return "other"

@dataclass(slots=True)
class DCCPin:
    name: str
    pin_type: str = ""
    data_type: str = ""
    value: str = ""
    comment: str = ""
    default: str = ""
    attributes: dict[str, str] = field(default_factory=dict)

@dataclass(slots=True)
class DCCInstance:
    name: str
    block_type: str = ""
    instance_id: str = ""
    inputs: list[DCCPin] = field(default_factory=list)
    outputs: list[DCCPin] = field(default_factory=list)

@dataclass(slots=True)
class DCCConnection:
    source: str
    target: str
    raw_attributes: dict[str, str] = field(default_factory=dict)

@dataclass(slots=True)
class DCCProgram:
    name: str
    source_path: str
    symbols: list[DCCSymbol] = field(default_factory=list)
    instances: list[DCCInstance] = field(default_factory=list)
    connections: list[DCCConnection] = field(default_factory=list)
    values: dict[str, str] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)

@dataclass(slots=True)
class DCCModel:
    programs: list[DCCProgram] = field(default_factory=list)

    @property
    def symbols(self) -> list[DCCSymbol]:
        return [s for p in self.programs for s in p.symbols]

    @property
    def connections(self) -> list[DCCConnection]:
        return [c for p in self.programs for c in p.connections]

    def symbol_index(self) -> dict[str, DCCSymbol]:
        result: dict[str, DCCSymbol] = {}
        for symbol in self.symbols:
            result.setdefault(symbol.name.lower(), symbol)
        return result

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class SignalPathStep:
    endpoint: str
    kind: str = "connection"
    instance: str = ""
    pin: str = ""
    block_type: str = ""
    comment: str = ""

@dataclass(slots=True)
class SignalPath:
    start: str
    end: str = ""
    direction: str = "forward"
    steps: list[SignalPathStep] = field(default_factory=list)
    matched_reference: str = ""
    matched_description: str = ""
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

@dataclass(slots=True)
class SignalEvidence:
    source: str
    value: str
    source_path: str = ""
    program: str = ""
    confidence: float = 1.0

@dataclass(slots=True)
class ResolvedSignal:
    reference: str
    name: str = ""
    description: str = ""
    data_type: str = ""
    source: str = "unresolved"
    program: str = ""
    source_path: str = ""
    evidences: list[SignalEvidence] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        return bool(self.name or self.description)

@dataclass(slots=True)
class PZDBinding:
    drive: str
    direction: str
    position: int
    transport_reference: str
    dcc_endpoint: str
    program: str
    resolved: Optional[ResolvedSignal] = None
    signal_path: Optional[SignalPath] = None

@dataclass(slots=True)
class SignalResolverModel:
    signals: dict[str, ResolvedSignal] = field(default_factory=dict)
    pzd_bindings: list[PZDBinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
