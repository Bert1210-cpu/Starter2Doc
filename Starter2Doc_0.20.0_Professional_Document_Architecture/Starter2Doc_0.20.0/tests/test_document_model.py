from starter2doc.core.engineering_model import EngineeringModel
from starter2doc.core.models import DCCModel, DCCProgram, DCCInstance, DCCPin, DCCSymbol
from starter2doc.core.usage_analyzer import DCCUsageModel, DCCUsageProgram
from starter2doc.document import DocumentModelBuilder, DocumentBuildOptions


def _model():
    program = DCCProgram(
        name='PositionControl', source_path='dcc/position.xml',
        instances=[
            DCCInstance(name='Add_1', block_type='ADD', inputs=[DCCPin('X1')], outputs=[DCCPin('Y')]),
            DCCInstance(name='Spare_1', block_type='ADD'),
        ],
        symbols=[DCCSymbol(name='p2530', data_type='REAL', comment='Position setpoint')]
    )
    return EngineeringModel(
        source_path='Demo.zip', dcc=DCCModel([program]),
        dcc_usage=DCCUsageModel([DCCUsageProgram(
            program='PositionControl', used_instances=['Add_1'], not_used_instances=['Spare_1']
        )]), metadata={'version': '0.20.0'}
    )


def test_document_builder_keeps_main_document_clean():
    document = DocumentModelBuilder().build(_model(), DocumentBuildOptions(include_unused_appendix=False))
    assert [s.title for s in document.sections] == ['Project Overview', 'DCC']
    dcc = document.sections[1]
    block_table = dcc.sections[0].elements[1]
    assert [r.cells[0] for r in block_table.rows] == ['Add_1']


def test_unused_blocks_can_be_added_to_appendix():
    document = DocumentModelBuilder().build(_model(), DocumentBuildOptions(include_unused_appendix=True))
    appendix = document.sections[-1]
    assert appendix.title == 'Appendix'
    assert appendix.sections[0].title == 'Unused DCC Blocks'
