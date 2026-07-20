from starter2doc.core.bico_parser import (BICOParser, SelectorKind, EndpointKind,
    ResolutionStatus)
from starter2doc.core.bico_resolver import BICOResolver, PathStatus
from starter2doc.core.bico_analysis import BICOSelectorAnalyzer
from starter2doc.core.engineering_builder import EngineeringModelBuilder
from starter2doc.core.engineering_model import EdgeKind


def _link(model, object_name, sink):
    return next(l for l in model.links if l.object_name == object_name and l.sink_reference.lower()==sink.lower())


def test_project3_decodes_parameter_number_without_inventing_selector_meaning():
    model=BICOParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    link=_link(model,'Drive_1','p1070[0]')
    assert link.source_reference=='r22072'
    assert link.selector==0xFC00
    assert link.selector_kind==SelectorKind.OBJECT_SCALAR.value
    assert link.resolution_status==ResolutionStatus.SELECTOR_PARTIAL.value
    assert link.source_object_name is None


def test_local_scalar_is_fully_parameter_resolved():
    link=BICOParser.decode_connector('Drive','p1',(22072<<16)|0)
    assert link.source_object_name=='Drive'
    assert link.resolution_status==ResolutionStatus.PARAMETER_RESOLVED.value


def test_bit_or_index_candidate_is_not_rendered_as_confirmed_bit():
    link=BICOParser.decode_connector('Drive','p1',(2050<<16)|0xFC04)
    assert link.source_reference=='r2050'
    assert link.source_bit is None
    assert link.selector_low_byte==4
    assert link.selector_kind==SelectorKind.BIT_OR_INDEX_CANDIDATE.value
    assert link.warnings


def test_r1_is_classified_separately():
    link=BICOParser.decode_connector('Drive','p1',(1<<16))
    assert link.endpoint_kind==EndpointKind.DEFAULT_REFERENCE.value


def test_invalid_and_unconnected_values_are_ignored():
    assert BICOParser.decode_connector('D','p1',0) is None
    assert BICOParser.decode_connector('D','p1',0xFFFFFFFF) is None


def test_resolver_reports_partial_for_unknown_object_selector():
    model=BICOParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    path=BICOResolver().resolve(model).paths['Drive_1::p1070[0]']
    assert path.end=='r22072'
    assert path.status==PathStatus.PARTIAL.value
    assert not path.complete


def test_selector_analysis_groups_all_links():
    model=BICOParser().parse_zip('/mnt/data/Testprojekt 3.zip')
    analysis=BICOSelectorAnalyzer().analyze(model)
    assert sum(g.count for g in analysis.groups)==len(model.links)
    assert analysis.unique_selectors==len(analysis.groups)


def test_engineering_graph_preserves_unknown_source_object_selector():
    model=EngineeringModelBuilder().build_from_zip('/mnt/data/Testprojekt 3.zip')
    edges=[e for e in model.graph.edges if e.kind==EdgeKind.BICO_CONNECTION.value]
    edge=next(e for e in edges if e.target.endswith('::p1070[0]'))
    assert edge.source.startswith('selector_0xfc::')
    assert edge.attributes['resolution_status']==ResolutionStatus.SELECTOR_PARTIAL.value


def test_all_reference_projects_parse_bico_without_crash():
    parser=BICOParser()
    for project in (1,2,3):
        model=parser.parse_zip(f'/mnt/data/Testprojekt {project}.zip')
        assert isinstance(model.links,list)
