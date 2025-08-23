from pyplecs.utils import dict_to_plecs_opts, model_vars_validator


def test_model_vars_validator_basic():
    provided = {'A': 1, 'B': 2}
    allowed = {'A', 'B', 'C'}
    filtered, unknown = model_vars_validator(provided, allowed=allowed)
    assert filtered == provided
    assert unknown == []


def test_model_vars_validator_unknown_non_strict():
    provided = {'A': 1, 'X': 9}
    allowed = {'A', 'B'}
    filtered, unknown = model_vars_validator(provided, allowed=allowed)
    assert filtered == {'A': 1}
    assert unknown == ['X'] or unknown == ['X']


def test_model_vars_validator_strict_raises():
    provided = {'A': 1, 'X': 9}
    allowed = {'A', 'B'}
    try:
        model_vars_validator(provided, allowed=allowed, strict=True)
    except ValueError:
        return
    assert False, 'Expected ValueError for strict unknown variables'


def test_dict_to_plecs_opts_with_validation():
    provided = {'A': '10', 'B': 2}
    allowed = {'A', 'B'}
    out = dict_to_plecs_opts(
        provided, coerce=True, allowed=allowed, strict=True
    )
    assert out['ModelVars']['A'] == 10.0
    assert out['ModelVars']['B'] == 2.0
