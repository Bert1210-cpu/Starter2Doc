from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
import re

from .models import DCCModel, DCCProgram


def _canon(endpoint: str) -> str:
    return endpoint.strip().lstrip('.').lower()


def _split(endpoint: str) -> tuple[str, str]:
    text = endpoint.strip().lstrip('.')
    if '.' not in text:
        return text, ''
    return text.rsplit('.', 1)


def _is_device_sink(endpoint: str) -> bool:
    """A connection into a STARTER device parameter is a real DCC consumer boundary."""
    return endpoint.strip().lower().startswith('_device#')


@dataclass(slots=True)
class DCCUsageProgram:
    program: str
    used_instances: list[str] = field(default_factory=list)
    not_used_instances: list[str] = field(default_factory=list)
    used_connections: list[int] = field(default_factory=list)
    not_used_connections: list[int] = field(default_factory=list)
    used_endpoints: list[str] = field(default_factory=list)
    not_used_endpoints: list[str] = field(default_factory=list)
    sink_endpoints: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def used_instance_count(self) -> int:
        return len(self.used_instances)

    @property
    def not_used_instance_count(self) -> int:
        return len(self.not_used_instances)


@dataclass(slots=True)
class DCCUsageModel:
    programs: list[DCCUsageProgram] = field(default_factory=list)

    @property
    def used_instances(self) -> int:
        return sum(p.used_instance_count for p in self.programs)

    @property
    def not_used_instances(self) -> int:
        return sum(p.not_used_instance_count for p in self.programs)

    @property
    def used_connections(self) -> int:
        return sum(len(p.used_connections) for p in self.programs)

    @property
    def not_used_connections(self) -> int:
        return sum(len(p.not_used_connections) for p in self.programs)

    def to_dict(self) -> dict:
        return asdict(self)


class DCCUsageAnalyzer:
    """Marks DCC elements that can influence an exported STARTER device parameter.

    The analysis is deliberately small and structural. It does not simulate block
    values or operating modes. A branch is USED when it has a graph path to a
    connection target beginning with ``_device#``. Everything else remains in the
    EngineeringModel as NOT_USED, so the Word exporter can omit it from the main
    documentation without losing information.
    """

    def analyze(self, dcc: DCCModel) -> DCCUsageModel:
        return DCCUsageModel([self._analyze_program(program) for program in dcc.programs])

    def _analyze_program(self, program: DCCProgram) -> DCCUsageProgram:
        reverse: dict[str, set[str]] = defaultdict(set)
        forward: dict[str, set[str]] = defaultdict(set)
        endpoint_text: dict[str, str] = {}

        # Real DCC wires.
        for connection in program.connections:
            source = _canon(connection.source)
            target = _canon(connection.target)
            endpoint_text.setdefault(source, connection.source)
            endpoint_text.setdefault(target, connection.target)
            forward[source].add(target)
            reverse[target].add(source)

        # Generic block influence: each input can influence every connected output
        # of the same instance. This is the same conservative rule used by the
        # SignalTracer and avoids project- or block-specific logic.
        outgoing_pins: dict[str, set[str]] = defaultdict(set)
        input_pins: dict[str, set[str]] = defaultdict(set)
        for connection in program.connections:
            source_instance, source_pin = _split(connection.source)
            target_instance, target_pin = _split(connection.target)
            if source_pin and not connection.source.lower().startswith('_device#'):
                outgoing_pins[source_instance.lower()].add(_canon(connection.source))
            if target_pin and not connection.target.lower().startswith('_device#'):
                input_pins[target_instance.lower()].add(_canon(connection.target))

        for instance_name, inputs in input_pins.items():
            for input_endpoint in inputs:
                for output_endpoint in outgoing_pins.get(instance_name, set()):
                    if input_endpoint == output_endpoint:
                        continue
                    forward[input_endpoint].add(output_endpoint)
                    reverse[output_endpoint].add(input_endpoint)

        sink_keys = {
            _canon(connection.target)
            for connection in program.connections
            if _is_device_sink(connection.target)
        }

        used: set[str] = set(sink_keys)
        queue = deque(sink_keys)
        while queue:
            current = queue.popleft()
            for predecessor in reverse.get(current, set()):
                if predecessor not in used:
                    used.add(predecessor)
                    queue.append(predecessor)

        all_endpoints = set(endpoint_text)
        not_used = all_endpoints - used

        used_connections: list[int] = []
        not_used_connections: list[int] = []
        for index, connection in enumerate(program.connections):
            # A wire is relevant when its target participates in a path to a real sink.
            if _canon(connection.target) in used:
                used_connections.append(index)
            else:
                not_used_connections.append(index)

        used_instances: list[str] = []
        not_used_instances: list[str] = []
        for instance in program.instances:
            prefix = instance.name.lower() + '.'
            instance_endpoints = {
                key for key in all_endpoints
                if key.startswith(prefix)
            }
            if instance_endpoints & used:
                used_instances.append(instance.name)
            else:
                not_used_instances.append(instance.name)

        return DCCUsageProgram(
            program=program.name,
            used_instances=sorted(used_instances, key=str.lower),
            not_used_instances=sorted(not_used_instances, key=str.lower),
            used_connections=used_connections,
            not_used_connections=not_used_connections,
            used_endpoints=sorted((endpoint_text.get(k, k) for k in used if k in endpoint_text), key=str.lower),
            not_used_endpoints=sorted((endpoint_text.get(k, k) for k in not_used), key=str.lower),
            sink_endpoints=sorted((endpoint_text.get(k, k) for k in sink_keys), key=str.lower),
        )
