from pyln.testing.fixtures import *
from pyln.client import RpcError

pluginopts = {'plugin': os.path.join(os.path.dirname(__file__), "virtualchannels.py")}

def test_summary_start(node_factory: NodeFactory):
    #assert(True)
    l1: LightningNode = node_factory.get_node(options=pluginopts)
    l2: LightningNode = node_factory.get_node(options=pluginopts)
    msg = r'ff' * 32
    node_id = '02df5ffe895c778e10f7742a6c5b8a0cefbe9465df58b92fadeb883752c8107c8f'
    with pytest.raises(RpcError, match=r'No such peer'):
        l1.rpc.dev_sendcustommsg(node_id, msg)
    #assert(s['network'] == 'REGTEST')  # or whatever you want to test
