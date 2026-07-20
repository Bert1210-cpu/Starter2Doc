from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from .bico_parser import BICOModel

@dataclass(slots=True)
class SelectorGroup:
    selector: int
    hex_value: str
    count: int
    high_byte: int
    low_byte: int
    selector_kind: str
    example_sinks: list[str] = field(default_factory=list)
    example_sources: list[str] = field(default_factory=list)

@dataclass(slots=True)
class BICOAnalysisModel:
    total_links: int = 0
    unique_selectors: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    endpoint_counts: dict[str, int] = field(default_factory=dict)
    selector_kind_counts: dict[str, int] = field(default_factory=dict)
    groups: list[SelectorGroup] = field(default_factory=list)
    def to_dict(self): return asdict(self)

class BICOSelectorAnalyzer:
    def analyze(self, model: BICOModel, examples_per_group: int = 5) -> BICOAnalysisModel:
        by_selector=defaultdict(list)
        for link in model.links: by_selector[link.selector].append(link)
        groups=[]
        for selector, links in sorted(by_selector.items(), key=lambda x:(-len(x[1]),x[0])):
            groups.append(SelectorGroup(
                selector=selector, hex_value=f'0x{selector:04X}', count=len(links),
                high_byte=(selector>>8)&0xFF, low_byte=selector&0xFF,
                selector_kind=links[0].selector_kind,
                example_sinks=[f'{x.object_name}::{x.sink_reference}' for x in links[:examples_per_group]],
                example_sources=[x.source_reference for x in links[:examples_per_group]],
            ))
        return BICOAnalysisModel(
            total_links=len(model.links), unique_selectors=len(groups),
            status_counts=dict(Counter(x.resolution_status for x in model.links)),
            endpoint_counts=dict(Counter(x.endpoint_kind for x in model.links)),
            selector_kind_counts=dict(Counter(x.selector_kind for x in model.links)),
            groups=groups,
        )
