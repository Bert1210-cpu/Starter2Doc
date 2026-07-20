from __future__ import annotations
from collections import defaultdict, deque
import re
from .models import DCCProgram, SignalPath, SignalPathStep, ResolvedSignal


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _strip_endpoint(endpoint: str) -> str:
    return endpoint.strip().lstrip('.')


def _split_endpoint(endpoint: str) -> tuple[str, str]:
    text = _strip_endpoint(endpoint)
    if '.' not in text:
        return text, ''
    instance, pin = text.rsplit('.', 1)
    return instance, pin


def _endpoint_key(endpoint: str) -> str:
    """STARTER exports the same DCC graph in mixed case; compare endpoints canonically."""
    return _strip_endpoint(endpoint).lower()


def _parameter_from_device(endpoint: str) -> str:
    if not endpoint.lower().startswith('_device#'):
        return ''
    match = re.search(r"(?i)\.([pr]\d+(?:\[\d+\])?(?:\.\d+)?)$", endpoint)
    return match.group(1) if match else ''


class SignalTracer:
    """Trace signal influence through a DCC connection graph.

    Pin direction is inferred from the graph itself: pins used as connection targets are
    consumers; pins used as connection sources are producers. This avoids block-name or
    project-specific rules and also works when STARTER stores all pins in one XML list.
    """

    def trace(self, program: DCCProgram, start: str, *, max_depth: int = 80) -> SignalPath:
        outgoing: dict[str, list[str]] = defaultdict(list)
        producer_pins: dict[str, list[str]] = defaultdict(list)

        for connection in program.connections:
            outgoing[_endpoint_key(connection.source)].append(connection.target)
            source_instance, source_pin = _split_endpoint(connection.source)
            if source_pin and not connection.source.lower().startswith('_device#'):
                key = source_instance.lower()
                if all(_endpoint_key(p) != _endpoint_key(connection.source) for p in producer_pins[key]):
                    producer_pins[key].append(connection.source)

        # Preserve one representative instance for metadata, independent of XML casing.
        instance_index = {}
        for instance in program.instances:
            instance_index.setdefault(instance.name.lower(), instance)

        queue = deque([(start, [start])])
        visited_depth: dict[str, int] = {}
        candidate_paths: list[list[str]] = []
        fallback_path = [start]

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            key = _endpoint_key(current)
            previous_depth = visited_depth.get(key)
            if previous_depth is not None and previous_depth <= len(path):
                continue
            visited_depth[key] = len(path)
            if len(path) > len(fallback_path):
                fallback_path = path

            # A device parameter reached from DCC is a meaningful engineering boundary.
            # Do not continue through it into unrelated BICO consumers.
            if _parameter_from_device(current):
                candidate_paths.append(path)
                continue

            neighbours = list(outgoing.get(key, []))
            instance_name, pin_name = _split_endpoint(current)
            if pin_name:
                # Generic block dependency: every producer pin of the same instance may
                # depend on the current consumer pin. Exact numerical simulation is not
                # required for documentation; influence tracing is sufficient.
                for producer in producer_pins.get(instance_name.lower(), []):
                    if _endpoint_key(producer) != key:
                        neighbours.append(producer)

            # Deduplicate mixed-case duplicate graph exports while retaining real text.
            unique_neighbours = []
            seen_neighbours = set()
            for neighbour in neighbours:
                neighbour_key = _endpoint_key(neighbour)
                if neighbour_key not in seen_neighbours:
                    seen_neighbours.add(neighbour_key)
                    unique_neighbours.append(neighbour)

            if not unique_neighbours:
                candidate_paths.append(path)
            else:
                for neighbour in unique_neighbours:
                    if _endpoint_key(neighbour) not in {_endpoint_key(p) for p in path}:
                        queue.append((neighbour, path + [neighbour]))

        best_path = self._select_path(candidate_paths, fallback_path, instance_index)
        steps = [self._step_for_endpoint(endpoint, instance_index) for endpoint in best_path]
        return SignalPath(start=start, end=best_path[-1], steps=steps)

    def resolve_path(self, program: DCCProgram, path: SignalPath, signals: dict[str, ResolvedSignal]) -> SignalPath:
        candidates: list[tuple[int, int, ResolvedSignal, str]] = []
        for step_index, step in enumerate(path.steps):
            if not step.comment:
                continue
            comment_norm = _norm(self._clean_pin_comment(step.comment))
            for signal in signals.values():
                if signal.program != program.name:
                    continue
                desc_norm = _norm(signal.description)
                if not comment_norm or not desc_norm:
                    continue
                score = 100 if comment_norm == desc_norm else 0
                if not score and comment_norm in desc_norm:
                    score = 85
                if not score and desc_norm in comment_norm:
                    score = 80
                if score:
                    candidates.append((score, step_index, signal, step.comment))

        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1], -len(x[2].description)))
            score, _, signal, _ = candidates[0]
            path.matched_reference = signal.reference
            path.matched_description = signal.description or signal.name
            path.confidence = score / 100
            return path

        # If no exported DCC symbol identifies the path, use the first external device
        # parameter reached by graph traversal. This is project-independent BICO evidence.
        for step in path.steps[1:]:
            reference = _parameter_from_device(step.endpoint)
            if reference:
                path.matched_reference = reference
                path.matched_description = self._semantic_path_label(path)
                path.confidence = 0.9
                return path

        path.warnings.append('Kein DCC-Symbol oder externer Parameter über den Signalpfad gefunden')
        return path

    def trace_and_resolve(self, program: DCCProgram, start: str, signals: dict[str, ResolvedSignal]) -> SignalPath:
        return self.resolve_path(program, self.trace(program, start), signals)

    @classmethod
    def _select_path(cls, paths: list[list[str]], fallback: list[str], instance_index) -> list[str]:
        if not paths:
            return fallback

        def comment_count(path: list[str]) -> int:
            count = 0
            for endpoint in path:
                instance_name, pin_name = _split_endpoint(endpoint)
                instance = instance_index.get(instance_name.lower())
                if not instance:
                    continue
                pin = next((p for p in instance.inputs + instance.outputs
                            if p.name.lower() == pin_name.lower()), None)
                if pin and cls._clean_pin_comment(pin.comment):
                    count += 1
            return count

        # STARTER pin comments are stronger semantic evidence than an arbitrary nearby
        # device boundary. Among equally described paths, prefer an external parameter
        # and then the shortest path.
        return min(
            paths,
            key=lambda path: (
                -comment_count(path),
                0 if _parameter_from_device(path[-1]) else 1,
                len(path),
                ' -> '.join(_endpoint_key(p) for p in path),
            ),
        )

    @staticmethod
    def _semantic_path_label(path: SignalPath) -> str:
        if not path.steps:
            return ''
        # The entry instance is the stable STARTER engineering label for the received PZD.
        instance = path.steps[0].instance
        text = re.sub(r"(?i)^_?dcc_?\d*_", "", instance).strip('_')
        return text.replace('_', ' ').strip()

    @staticmethod
    def _clean_pin_comment(comment: str) -> str:
        text = re.sub(r'^\s*@\*?\d+\s*', '', comment)
        text = re.sub(r'^\s*<>\s*', '', text)
        text = re.sub(r'^\s*@\d+\s*<>\s*@\d+\s*', '', text)
        return text.strip()

    @staticmethod
    def _step_for_endpoint(endpoint: str, instance_index) -> SignalPathStep:
        instance_name, pin_name = _split_endpoint(endpoint)
        instance = instance_index.get(instance_name.lower())
        comment = ''
        block_type = ''
        if instance:
            block_type = instance.block_type
            pin = next(
                (p for p in instance.inputs + instance.outputs if p.name.lower() == pin_name.lower()),
                None,
            )
            if pin:
                comment = pin.comment
        kind = 'device' if endpoint.lower().startswith('_device#') else ('pin' if pin_name else 'endpoint')
        return SignalPathStep(
            endpoint=endpoint,
            kind=kind,
            instance=instance_name if instance else '',
            pin=pin_name,
            block_type=block_type,
            comment=comment,
        )
