"""dv-flow-mgr extension entry point: provides the ``covsight`` package."""
import os


def dvfm_packages():
    here = os.path.dirname(os.path.abspath(__file__))
    return {
        "covsight": os.path.join(here, "flow.yaml"),
    }
