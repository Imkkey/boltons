import importlib.util

import pytest

from boltons import urlutils
from boltons.dictutils import FastIterOrderedMultiDict, OrderedMultiDict
from boltons.urlutils import URL, QueryParamDict


@pytest.fixture(scope='module')
def standalone_urlutils():
    # Without a package, the relative dictutils import falls back to the
    # embedded implementation used when urlutils is copied into a project.
    spec = importlib.util.spec_from_file_location('standalone_urlutils', urlutils.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.OrderedMultiDict is not OrderedMultiDict
    return module


@pytest.fixture(params=['omd', 'fast_omd', 'query_params',
                       'standalone_omd', 'standalone_query_params'])
def omd_type(request, standalone_urlutils):
    return {
        'omd': OrderedMultiDict,
        'fast_omd': FastIterOrderedMultiDict,
        'query_params': QueryParamDict,
        'standalone_omd': standalone_urlutils.OrderedMultiDict,
        'standalone_query_params': standalone_urlutils.QueryParamDict,
    }[request.param]


def test_popitem_removes_all_values(omd_type):
    omd = omd_type([('a', 1), ('b', 2), ('a', 3), ('b', 4)])

    assert omd.popitem() == ('b', 4)
    assert len(omd) == 1
    assert 'b' not in omd
    assert omd.getlist('b') == []
    assert list(omd) == ['a']
    assert omd.items(multi=True) == [('a', 1), ('a', 3)]
    assert omd.getlist('a') == [1, 3]

    assert omd.popitem() == ('a', 3)
    assert len(omd) == 0
    assert list(omd) == []
    assert omd.items(multi=True) == []
    with pytest.raises(KeyError):
        omd.popitem()


def test_popitem_preserves_dict_key_selection(omd_type):
    omd = omd_type([('a', 1), ('b', 2), ('a', 3)])
    reference = {'a': 3, 'b': 2}
    omd['a'] = reference['a'] = 4

    while reference:
        assert omd.popitem() == reference.popitem()
    assert omd.items(multi=True) == []


def test_popitem_reinsert_removed_key(omd_type):
    omd = omd_type([('a', 1), ('b', 2), ('a', 3)])
    omd.popitem()
    omd.add('b', 4)

    assert omd.items(multi=True) == [('a', 1), ('a', 3), ('b', 4)]
    assert omd.getlist('b') == [4]
    assert omd.poplast() == 4
    assert list(omd) == ['a']
    assert omd.pop('a') == 3
    assert omd.items(multi=True) == []


def test_popitem_preserves_value_identity(omd_type):
    value = []
    omd = omd_type([('a', None), ('a', value)])

    key, result = omd.popitem()
    assert key == 'a'
    assert result is value
    assert not omd
    assert omd.items(multi=True) == []


def test_popitem_empty(omd_type):
    omd = omd_type()
    with pytest.raises(KeyError):
        omd.popitem()
    assert not omd
    assert omd.items(multi=True) == []


def test_popitem_updates_url_serialization():
    url = URL('https://example.com/?tag=python&page=1&tag=testing')

    assert url.query_params.popitem() == ('page', '1')
    assert url.to_text() == 'https://example.com/?tag=python&tag=testing'
    assert url.query_params.items() == [('tag', 'testing')]

    assert url.query_params.popitem() == ('tag', 'testing')
    assert url.to_text() == 'https://example.com/'
