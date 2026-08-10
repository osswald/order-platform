"""Edge bundle event loading must use selectinload for collections (no JOIN cartesian)."""

from app.routers.edge import _edge_event_bundle_load_options
from app.routers.events_helpers import event_configuration_load_options


def _strategies(options):
    out = []
    for opt in options:
        for attr in opt.context:
            out.append(attr.strategy)
    return out


def test_edge_bundle_load_options_match_configuration_selectinload():
    edge_opts = _edge_event_bundle_load_options()
    cfg_opts = event_configuration_load_options(include_layout_cells=True)

    edge_strats = _strategies(edge_opts)
    cfg_strats = _strategies(cfg_opts)

    assert edge_strats == cfg_strats
    assert (("lazy", "joined"),) in edge_strats  # organisation many-to-one
    collection_strats = [s for s in edge_strats if s != (("lazy", "joined"),)]
    assert collection_strats
    assert all(s == (("lazy", "selectin"),) for s in collection_strats)
