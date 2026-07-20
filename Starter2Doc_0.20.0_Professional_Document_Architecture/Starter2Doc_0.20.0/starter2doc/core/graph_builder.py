from __future__ import annotations
import re
from .engineering_model import GraphEdge, GraphNode, SignalGraph, NodeKind, EdgeKind
from .models import DCCModel, DCCInstance
from .bico_parser import BICOModel

_PARAM_RE = re.compile(r'(?i)(?<![A-Za-z0-9_])([pr]\d+(?:\[\d+\])?(?:\.\d+)?)')


def _strip(endpoint: str) -> str:
    return endpoint.strip().lstrip('.')


def _split(endpoint: str) -> tuple[str, str]:
    text = _strip(endpoint)
    if '.' not in text:
        return text, ''
    return text.rsplit('.', 1)


def endpoint_id(program: str, endpoint: str) -> str:
    return f'{program}::endpoint::{endpoint.strip()}'


class GraphBuilder:
    """Transforms parsed DCC information into a neutral directed engineering graph."""

    def build(self, dcc: DCCModel) -> SignalGraph:
        graph = SignalGraph()
        for program in dcc.programs:
            program_id = f'program::{program.name}'
            graph.add_node(GraphNode(program_id, NodeKind.PROGRAM.value, program.name, program.name,
                                     {'source_path': program.source_path}))
            instances = {i.name: i for i in program.instances}
            for inst in program.instances:
                self._add_instance(graph, program.name, program_id, inst)
            for symbol in program.symbols:
                kind = NodeKind.PARAMETER.value if symbol.parameter_kind in {'p', 'r'} else NodeKind.SYMBOL.value
                symbol_id = f'{program.name}::symbol::{symbol.name.lower()}'
                graph.add_node(GraphNode(symbol_id, kind, symbol.name, program.name, {
                    'description': symbol.comment,
                    'data_type': symbol.data_type,
                    'direction': symbol.direction,
                    'address': symbol.address,
                }))
                graph.add_edge(GraphEdge(program_id, symbol_id, EdgeKind.CONTAINS.value, program.name))
            for conn in program.connections:
                source_id = self._ensure_endpoint(graph, program.name, conn.source, instances)
                target_id = self._ensure_endpoint(graph, program.name, conn.target, instances)
                graph.add_edge(GraphEdge(source_id, target_id, EdgeKind.CONNECTION.value, program.name,
                                         dict(conn.raw_attributes)))
        return graph


    def add_bico(self, graph: SignalGraph, bico: BICOModel) -> SignalGraph:
        """Adds neutral parameter nodes and BICO edges to an existing graph."""
        for link in bico.links:
            sink_id = f'{link.object_name}::parameter::{link.sink_reference.lower()}'
            source_object = link.source_object_name or f'selector_0x{link.source_object_selector:02x}'
            source_id = f'{source_object}::parameter::{link.source_reference.lower()}'
            graph.add_node(GraphNode(sink_id, NodeKind.PARAMETER.value, link.sink_reference, link.object_name, {
                'reference': link.sink_reference, 'object_name': link.object_name,
                'source_path': link.source_path,
            }))
            graph.add_node(GraphNode(source_id, NodeKind.PARAMETER.value, link.source_reference, link.object_name, {
                'reference': link.source_reference, 'object_name': link.source_object_name or '',
                'object_selector': link.source_object_selector, 'endpoint_kind': link.endpoint_kind,
            }))
            graph.add_edge(GraphEdge(source_id, sink_id, EdgeKind.BICO_CONNECTION.value, link.object_name, {
                'raw_value': link.raw_value, 'selector': link.selector,
                'confidence': link.confidence, 'resolution_status': link.resolution_status,
                'selector_kind': link.selector_kind, 'warnings': list(link.warnings),
            }))
        return graph

    def _add_instance(self, graph: SignalGraph, program: str, program_id: str, inst: DCCInstance) -> None:
        inst_id = f'{program}::instance::{inst.name}'
        graph.add_node(GraphNode(inst_id, NodeKind.INSTANCE.value, inst.name, program,
                                 {'block_type': inst.block_type, 'instance_id': inst.instance_id}))
        graph.add_edge(GraphEdge(program_id, inst_id, EdgeKind.CONTAINS.value, program))
        for pin in inst.inputs + inst.outputs:
            ep = f'.{inst.name}.{pin.name}'
            pin_id = endpoint_id(program, ep)
            graph.add_node(GraphNode(pin_id, NodeKind.PIN.value, pin.name, program, {
                'endpoint': ep,
                'instance': inst.name,
                'pin': pin.name,
                'pin_type': pin.pin_type,
                'block_type': inst.block_type,
                'comment': pin.comment,
                'data_type': pin.data_type,
                'value': pin.value,
                'default': pin.default,
            }))
            graph.add_edge(GraphEdge(inst_id, pin_id, EdgeKind.CONTAINS.value, program))

    def _ensure_endpoint(self, graph: SignalGraph, program: str, endpoint: str,
                         instances: dict[str, DCCInstance]) -> str:
        node_id = endpoint_id(program, endpoint)
        if node_id in graph.nodes:
            return node_id
        inst_name, pin_name = _split(endpoint)
        param = _PARAM_RE.search(endpoint)
        if endpoint.lower().startswith('_device#'):
            kind = NodeKind.DEVICE_SIGNAL.value
        elif param:
            kind = NodeKind.PARAMETER.value
        elif inst_name in instances and pin_name:
            kind = NodeKind.PIN.value
        else:
            kind = NodeKind.ENDPOINT.value
        attrs = {'endpoint': endpoint, 'instance': inst_name if inst_name in instances else '', 'pin': pin_name}
        if param:
            attrs['parameter_reference'] = param.group(1)
        graph.add_node(GraphNode(node_id, kind, endpoint, program, attrs))
        return node_id
