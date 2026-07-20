from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum

from .bico_parser import BICOModel, BICOLink, ResolutionStatus


class PathStatus(str, Enum):
    TERMINAL = 'terminal'
    PARTIAL = 'partial'
    LOOP = 'loop'
    MAX_DEPTH = 'max_depth'
    UNRESOLVED = 'unresolved'


@dataclass(slots=True)
class BICOPath:
    start: str
    end: str
    links: list[BICOLink] = field(default_factory=list)
    status: str = PathStatus.UNRESOLVED.value
    complete: bool = False
    loop_detected: bool = False
    max_depth_reached: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BICOResolverModel:
    paths: dict[str, BICOPath] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class BICOResolver:
    """Resolves BICO links conservatively.

    A connector is normally a terminal CI<-CO relation. Multi-step traversal is
    attempted only when the resolved source is itself present as a sink in the same
    verified engineering object. Unknown object selectors stop the trace as PARTIAL.
    """

    def resolve(self, model: BICOModel, max_depth: int = 32) -> BICOResolverModel:
        result = BICOResolverModel()
        index = {(l.object_name.lower(), l.sink_reference.lower()): l for l in model.links}
        for link in model.links:
            key = f'{link.object_name}::{link.sink_reference}'
            current = link
            visited: set[tuple[str, str]] = set()
            chain: list[BICOLink] = []
            loop = False
            depth_hit = False
            warnings: list[str] = []
            for _ in range(max_depth):
                signature = (current.object_name.lower(), current.sink_reference.lower())
                if signature in visited:
                    loop = True
                    warnings.append('BICO loop detected')
                    break
                visited.add(signature)
                chain.append(current)
                # Cross-object traversal is forbidden until selector->object mapping is proven.
                if current.source_object_name is None:
                    break
                next_link = index.get((current.source_object_name.lower(), current.source_reference.lower()))
                if next_link is None:
                    break
                current = next_link
            else:
                depth_hit = True
                warnings.append(f'Maximum BICO trace depth {max_depth} reached')

            all_warnings = warnings + [w for item in chain for w in item.warnings]
            if loop:
                status = PathStatus.LOOP.value
            elif depth_hit:
                status = PathStatus.MAX_DEPTH.value
            elif not chain:
                status = PathStatus.UNRESOLVED.value
            elif all(item.resolution_status == ResolutionStatus.PARAMETER_RESOLVED.value for item in chain):
                status = PathStatus.TERMINAL.value
            else:
                status = PathStatus.PARTIAL.value

            result.paths[key] = BICOPath(
                start=link.sink_reference,
                end=chain[-1].source_reference if chain else link.sink_reference,
                links=chain,
                status=status,
                complete=status == PathStatus.TERMINAL.value,
                loop_detected=loop,
                max_depth_reached=depth_hit,
                warnings=all_warnings,
            )
        return result
