import os
from pathlib import Path
import tempfile
import scipy.io as sio
import yaml

from pyplecs.pyplecs import PlecsServer, FileLoadError


def test_load_model_vars_from_dict(tmp_path):
    ps = PlecsServer(sim_path='.', sim_name='model.plecs', load=False)
    res = ps.load_model_vars_unified({'a': 1, 'b': 2}, merge=True, validate=False, convert_types=True)
    assert 'ModelVars' in res
    assert res['ModelVars']['a'] == 1.0


def test_load_model_vars_replace():
    ps = PlecsServer(sim_path='.', sim_name='model.plecs', load=False)
    ps.optStruct = {'ModelVars': {'x': 10}}
    res = ps.load_model_vars_unified({'y': 5}, merge=False)
    assert res['ModelVars'] == {'y': 5}


def test_load_model_vars_from_yaml(tmp_path):
    ps = PlecsServer(sim_path='.', sim_name='model.plecs', load=False)
    data = {'Vi': 230, 'Vo': 12}
    p = tmp_path / 'vars.yaml'
    p.write_text(yaml.safe_dump(data))
    res = ps.load_model_vars_unified(str(p), merge=True)
    assert res['ModelVars']['Vi'] == 230.0 or res['ModelVars']['Vi'] == 230


def test_load_model_vars_from_mat(tmp_path):
    ps = PlecsServer(sim_path='.', sim_name='model.plecs', load=False)
    data = {'Vi': 123, 'Vo': 4}
    p = tmp_path / 'vars.mat'
    sio.savemat(str(p), data)
    res = ps.load_model_vars_unified(str(p), merge=True)
    assert 'Vi' in res['ModelVars']


def test_load_model_vars_file_not_found():
    ps = PlecsServer(sim_path='.', sim_name='model.plecs', load=False)
    try:
        ps.load_model_vars_unified('nonexistent.file')
        assert False, "Expected FileLoadError"
    except FileLoadError:
        assert True
