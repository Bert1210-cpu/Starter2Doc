from __future__ import annotations
from .dcc_parser import DCCParser
from .diagnostics import DiagnosticsBuilder
from .engineering_model import EngineeringModel
from .graph_builder import GraphBuilder
from .signal_resolver import SignalResolver
from .bico_parser import BICOParser
from .bico_resolver import BICOResolver
from .bico_analysis import BICOSelectorAnalyzer
from .usage_analyzer import DCCUsageAnalyzer


class EngineeringModelBuilder:
    """Orchestrates parsers and resolvers; no report/export knowledge lives here."""

    def __init__(self) -> None:
        self.dcc_parser = DCCParser()
        self.graph_builder = GraphBuilder()
        self.signal_resolver = SignalResolver()
        self.bico_parser = BICOParser()
        self.bico_resolver = BICOResolver()
        self.bico_analyzer = BICOSelectorAnalyzer()
        self.usage_analyzer = DCCUsageAnalyzer()
        self.diagnostics_builder = DiagnosticsBuilder()

    def build_from_zip(self, zip_path: str) -> EngineeringModel:
        dcc = self.dcc_parser.parse_zip(zip_path)
        graph = self.graph_builder.build(dcc)
        resolver = self.signal_resolver.resolve_dcc(dcc)
        bico = self.bico_parser.parse_zip(zip_path)
        self.graph_builder.add_bico(graph, bico)
        bico_resolver = self.bico_resolver.resolve(bico)
        bico_analysis = self.bico_analyzer.analyze(bico)
        dcc_usage = self.usage_analyzer.analyze(dcc)
        model = EngineeringModel(source_path=zip_path, dcc=dcc, graph=graph, resolver=resolver,
                                 bico=bico, bico_resolver=bico_resolver, bico_analysis=bico_analysis,
                                 dcc_usage=dcc_usage, metadata={'version': '0.20.0'})
        model.diagnostics = self.diagnostics_builder.build(model)
        return model
