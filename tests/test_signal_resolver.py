from starter2doc.core.dcc_parser import DCCParser
from starter2doc.core.signal_resolver import SignalResolver


def test_project3_resolves_dcc_symbol():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    model = SignalResolver().resolve_dcc(dcc)
    signal = model.signals['p22002']
    assert signal.description == 'E STOP CH2'
    assert signal.source == 'DCC'


def test_project3_detects_receive_pzd_connections():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    model = SignalResolver().resolve_dcc(dcc)
    assert any(b.direction == 'RX' and b.position == 1 and b.drive == 'Drive_1' for b in model.pzd_bindings)
    assert any(b.direction == 'RX' and b.position == 12 and b.drive == 'Drive_1' for b in model.pzd_bindings)


def test_project2_detects_clock_pzd_connections():
    dcc = DCCParser().parse_zip('/mnt/data/Testprojekt 2.zip')
    model = SignalResolver().resolve_dcc(dcc)
    assert any(b.direction == 'RX' and b.position == 10 for b in model.pzd_bindings)
    assert any(b.direction == 'RX' and b.position == 11 for b in model.pzd_bindings)
