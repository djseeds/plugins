from pyln.testing.fixtures import *

def test_summary_start(node_factory):
    l1 = node_factory.get_node(options=pluginopt)
    s = l1.rpc.summary()
    assert(s['network'] == 'REGTEST')  # or whatever you want to test
