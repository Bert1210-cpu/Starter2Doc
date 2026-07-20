from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Iterable

from .models import DCCModel, SignalResolverModel
from .bico_parser import BICOModel
from .bico_resolver import BICOResolverModel
from .bico_analysis import BICOAnalysisModel
from .usage_analyzer import DCCUsageModel


class NodeKind(str, Enum):
    PROGRAM = 'program'
    INSTANCE = 'instance'
    PIN = 'pin'
    PARAMETER = 'parameter'
    DEVICE_SIGNAL = 'device_signal'
    SYMBOL = 'symbol'
    ENDPOINT = 'endpoint'
    BICO_LINK = 'bico_link'


class EdgeKind(str, Enum):
    CONNECTION = 'connection'
    INTERNAL_DEPENDENCY = 'internal_dependency'
    REPRESENTS = 'represents'
    CONTAINS = 'contains'
    BICO_CONNECTION = 'bico_connection'


@dataclass(slots=True)
class GraphNode:
    id: str
    kind: str
    name: str = ''
    program: str = ''
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphEdge:
    source: str
    target: str
    kind: str = EdgeKind.CONNECTION.value
    program: str = ''
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SignalGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> GraphNode:
        existing = self.nodes.get(node.id)
        if existing is None:
            self.nodes[node.id] = node
            return node
        if not existing.name and node.name:
            existing.name = node.name
        if not existing.program and node.program:
            existing.program = node.program
        existing.attributes.update({k: v for k, v in node.attributes.items() if v not in ('', None, [], {})})
        return existing

    def add_edge(self, edge: GraphEdge) -> None:
        signature = (edge.source, edge.target, edge.kind, edge.program)
        if any((e.source, e.target, e.kind, e.program) == signature for e in self.edges):
            return
        self.edges.append(edge)

    def outgoing(self, node_id: str, kinds: set[str] | None = None) -> list[GraphEdge]:
        return [e for e in self.edges if e.source == node_id and (kinds is None or e.kind in kinds)]

    def incoming(self, node_id: str, kinds: set[str] | None = None) -> list[GraphEdge]:
        return [e for e in self.edges if e.target == node_id and (kinds is None or e.kind in kinds)]


@dataclass(slots=True)
class CoverageMetrics:
    programs: int = 0
    instances: int = 0
    connections: int = 0
    symbols: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    pzd_bindings: int = 0
    resolved_pzd_bindings: int = 0
    traced_pzd_bindings: int = 0
    complete_trace_bindings: int = 0
    parser_warnings: int = 0
    unresolved_bindings: int = 0

    @property
    def signal_resolution_percent(self) -> float:
        return 100.0 if self.pzd_bindings == 0 else round(self.resolved_pzd_bindings * 100.0 / self.pzd_bindings, 2)

    @property
    def trace_coverage_percent(self) -> float:
        return 100.0 if self.pzd_bindings == 0 else round(self.traced_pzd_bindings * 100.0 / self.pzd_bindings, 2)

    @property
    def complete_trace_percent(self) -> float:
        return 100.0 if self.pzd_bindings == 0 else round(self.complete_trace_bindings * 100.0 / self.pzd_bindings, 2)


@dataclass(slots=True)
class DiagnosticIssue:
    severity: str
    code: str
    message: str
    program: str = ''
    reference: str = ''


@dataclass(slots=True)
class EngineeringDiagnostics:
    coverage: CoverageMetrics = field(default_factory=CoverageMetrics)
    issues: list[DiagnosticIssue] = field(default_factory=list)


@dataclass(slots=True)
class EngineeringModel:
    source_path: str = ''
    dcc: DCCModel = field(default_factory=DCCModel)
    resolver: SignalResolverModel = field(default_factory=SignalResolverModel)
    bico: BICOModel = field(default_factory=BICOModel)
    bico_resolver: BICOResolverModel = field(default_factory=BICOResolverModel)
    bico_analysis: BICOAnalysisModel = field(default_factory=BICOAnalysisModel)
    dcc_usage: DCCUsageModel = field(default_factory=DCCUsageModel)
    graph: SignalGraph = field(default_factory=SignalGraph)
    diagnostics: EngineeringDiagnostics = field(default_factory=EngineeringDiagnostics)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
