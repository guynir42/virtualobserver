import os
import yaml
import time
import uuid
import pytest
import datetime
from pprint import pprint


from src.project import Project
from src.observatory import VirtualDemoObs


def test_project_download_small_catalog():
    num_sources_with_data = 0
    filenames = []

    try:  # cleanup at end
        proj = Project(
            name="default_test",
            obs_names=["demo"],
            analysis_kwargs={"num_injections": 3},
            obs_kwargs={},
            catalog_kwargs={"default": "test"},
            verbose=0,
        )

        obs = proj.observatories["demo"]
        assert isinstance(obs, VirtualDemoObs)
        obs.pars.check_data_exists = True
        proj.run()

        assert len(obs.sources) > 0

        for s in obs.sources:
            assert len(s.raw_photometry) == 1
            p = s.raw_photometry[0]
            assert p.get_fullname() is not None
            assert os.path.exists(p.get_fullname())
            filenames.append(p.get_fullname())

            if len(p.data):
                num_sources_with_data += 1

        assert num_sources_with_data > 0

    finally:  # cleanup
        proj.delete_all_sources(remove_associated_data=True, remove_raw_data=True)
        proj.delete_outputs()
    for f in filenames:
        assert not os.path.exists(f)
        assert not os.path.exists(os.path.join(proj.output_folder, "config.yaml"))
