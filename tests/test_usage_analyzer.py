from starter2doc.core.models import DCCConnection, DCCInstance, DCCModel, DCCPin, DCCProgram
from starter2doc.core.usage_analyzer import DCCUsageAnalyzer
from starter2doc.core.engineering_builder import EngineeringModelBuilder


def test_marks_branch_to_device_parameter_as_used():
    program = DCCProgram(
        name='DCC_1', source_path='x',
        instances=[
            DCCInstance('Source', outputs=[DCCPin('q')]),
            DCCInstance('Used', inputs=[DCCPin('i')], outputs=[DCCPin('q')]),
            DCCInstance('Reserve', inputs=[DCCPin('i')], outputs=[DCCPin('q')]),
        ],
        connections=[
            DCCConnection('.Source.q', '.Used.i'),
            DCCConnection('.Used.q', '_device#Drive_1.p1070[0]'),
            DCCConnection('.Source.q', '.Reserve.i'),
        ],
    )
    result = DCCUsageAnalyzer().analyze(DCCModel([program])).programs[0]
    assert set(result.used_instances) == {'Source', 'Used'}
    assert result.not_used_instances == ['Reserve']
    assert result.used_connections == [0, 1]
    assert result.not_used_connections == [2]


def test_real_reference_projects_build_with_usage_model():
    builder = EngineeringModelBuilder()
    for path in ('/mnt/data/Testprojekt 1.zip', '/mnt/data/Testprojekt 2.zip', '/mnt/data/Testprojekt 3.zip'):
        model = builder.build_from_zip(path)
        assert model.metadata['version'] == '0.20.0'
        assert model.dcc_usage.programs
        assert model.dcc_usage.used_connections > 0
