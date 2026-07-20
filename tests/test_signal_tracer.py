from starter2doc.core.dcc_parser import DCCParser
from starter2doc.core.signal_resolver import SignalResolver


def _binding(model, direction, position):
    return next(b for b in model.pzd_bindings if b.direction == direction and b.position == position)


def test_project2_trace_resolves_p21600():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 2.zip')
    model = SignalResolver().resolve_dcc(dcc)
    b = _binding(model, 'RX', 10)
    assert b.resolved.reference.lower() == 'p21600'
    assert b.resolved.description == 'Jahr_Monat von Basis'
    assert b.signal_path is not None
    assert b.signal_path.matched_reference.lower() == 'p21600'


def test_project2_trace_resolves_p21601():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 2.zip')
    model = SignalResolver().resolve_dcc(dcc)
    b = _binding(model, 'RX', 11)
    assert b.resolved.reference.lower() == 'p21601'
    assert b.resolved.description == 'Tag_Stunde von Basis'


def test_project3_existing_resolution_regression():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    model = SignalResolver().resolve_dcc(dcc)
    assert model.signals['p22002'].description == 'E STOP CH2'


def test_project3_traces_speed_setpoint_to_p1070():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    model = SignalResolver().resolve_dcc(dcc)
    b = _binding(model, 'RX', 2)
    assert b.resolved.reference.lower() == 'p1070[0]'
    assert b.signal_path is not None
    assert b.signal_path.end.lower().endswith('.p1070[0]')


def test_project3_traces_position_and_oscillation_inputs_to_p2530():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    model = SignalResolver().resolve_dcc(dcc)
    for position in (10, 14, 15):
        b = _binding(model, 'RX', position)
        assert b.resolved.reference.lower() == 'p2530'
        assert b.signal_path is not None
        assert b.signal_path.end.lower().endswith('.p2530')


def test_project3_exported_symbol_resolution_has_priority_over_external_boundary():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    model = SignalResolver().resolve_dcc(dcc)
    expected = {1: 'p22001', 12: 'p22000', 13: 'r22072'}
    for position, reference in expected.items():
        assert _binding(model, 'RX', position).resolved.reference.lower() == reference
    assert _binding(model, 'TX', 11).resolved.reference.lower() == 'r22070'
    assert _binding(model, 'TX', 12).resolved.reference.lower() == 'r22071'
