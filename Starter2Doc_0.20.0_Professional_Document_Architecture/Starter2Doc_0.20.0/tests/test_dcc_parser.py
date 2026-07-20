from starter2doc.core.dcc_parser import DCCParser

def test_project3_has_dcc_symbols():
    model = DCCParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    assert model.programs
    assert any(s.name == 'p22002' and s.comment == 'E STOP CH2' for s in model.symbols)
