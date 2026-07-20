from starter2doc.core.engineering_builder import EngineeringModelBuilder


def test_engineering_model_contains_graph_and_diagnostics():
    model = EngineeringModelBuilder().build_from_zip('/mnt/data/Testprojekt 3.zip')
    assert model.graph.nodes
    assert model.graph.edges
    assert model.diagnostics.coverage.programs == len(model.dcc.programs)
    assert model.diagnostics.coverage.pzd_bindings == len(model.resolver.pzd_bindings)


def test_graph_contains_device_and_pin_nodes():
    model = EngineeringModelBuilder().build_from_zip('/mnt/data/Testprojekt 2.zip')
    kinds = {node.kind for node in model.graph.nodes.values()}
    assert 'device_signal' in kinds
    assert 'pin' in kinds


def test_project2_complete_clock_traces_are_measured():
    model = EngineeringModelBuilder().build_from_zip('/mnt/data/Testprojekt 2.zip')
    bindings = {(b.direction, b.position): b for b in model.resolver.pzd_bindings}
    assert bindings[('RX', 10)].signal_path.matched_reference.lower() == 'p21600'
    assert bindings[('RX', 11)].signal_path.matched_reference.lower() == 'p21601'
    assert model.diagnostics.coverage.complete_trace_bindings >= 2
