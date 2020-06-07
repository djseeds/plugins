from pyln.testing.fixtures import *
from pyln.client import RpcError
from pyln.testing.utils import wait_for
from time import sleep
import unittest

pluginopts = {'plugin': os.path.join(os.path.dirname(__file__), "virtualchannels.py")}

def test_vcinvoice(node_factory: NodeFactory):
    id1 = node_factory.get_node_id()
    id2 = node_factory.get_node_id()
    l2: LightningNode = node_factory.get_node(id2, options=pluginopts, **{'trust_node': id1})
    id2 = l2.rpc.getinfo()["id"]
    l1: LightningNode = node_factory.get_node(id1, options={**pluginopts, **{'trust_node': id2}})
    l3: LightningNode = node_factory.get_node(options=pluginopts)

    l1.connect(l3)
    l3.openchannel(l1, 1_000_000)

    payload = {
        "msatoshi": 9000000,
        "label": "test",
        "description": "test",
    }


    res = l1.rpc.call("vcinvoice", payload)
    invoice_details = l1.rpc.decodepay(res["bolt11"])
    info = l1.rpc.getinfo()
    assert(invoice_details["payee"] == info["id"])
    assert(len(invoice_details["routes"]) == 1)
    assert(len(invoice_details["routes"][0]) == 1)
    assert(invoice_details["routes"][0][0]["pubkey"] == id2)
    

def test_concrete_send(node_factory: NodeFactory):
    """ Ensure concrete send still works with plugin activated
    """
    id1 = node_factory.get_node_id()
    id2 = node_factory.get_node_id()
    l1: LightningNode = node_factory.get_node(id1, options={**pluginopts, **{'trust_node': id2}})
    l2: LightningNode = node_factory.get_node(id2, options=pluginopts, **{'trust_node': id1})
    l3: LightningNode = node_factory.get_node(options=pluginopts)

    l1.connect(l3)
    l1.openchannel(l3, 1_000_000)
    # l1 should be able to pay l3 directly
    invoice = l3.rpc.invoice(9000000, "test", "test")
    sleep(1)
    l1.rpc.pay(invoice["bolt11"])
    #l1.pay(l3, 100000)

def test_virtual_send(node_factory: NodeFactory):
    id1 = node_factory.get_node_id()
    id2 = node_factory.get_node_id()
    l1: LightningNode = node_factory.get_node(id1, options={**pluginopts, **{'trust_node': id2}})
    l2: LightningNode = node_factory.get_node(id2, options=pluginopts, **{'trust_node': id1})
    l3: LightningNode = node_factory.get_node(options=pluginopts)

    l1.connect(l3)
    l1.fund_channel(l3, 1_000_000)
    # l2 should be able to send to l3 through l1
    invoice = l3.rpc.invoice(100000, "test", "Test Invoice")
    l2.rpc.pay(invoice["bolt11"])

def test_concrete_receive(node_factory: NodeFactory):
    """ Ensure concrete receive still works with plugin activated
    """
    id1 = node_factory.get_node_id()
    id2 = node_factory.get_node_id()
    l1: LightningNode = node_factory.get_node(id1, options={**pluginopts, **{'trust_node': id2}})
    l2: LightningNode = node_factory.get_node(id2, options=pluginopts, **{'trust_node': id1})
    l3: LightningNode = node_factory.get_node(options=pluginopts)

    l3.connect(l1)
    l3.fund_channel(l1, 1_000_000)
    # l3 should be able to pay l3 directly
    invoice = l1.rpc.invoice(100000, "test", "Test Invoice")
    print(len(l3.rpc.listchannels()['channels']))
    print(len(l1.rpc.listchannels()['channels']))
    sleep(10)
    l3.pay(l1, 100000)
    #l3.rpc.pay(invoice["bolt11"])

def test_virtual_receive(node_factory: NodeFactory):
    id1 = node_factory.get_node_id()
    id2 = node_factory.get_node_id()
    l1: LightningNode = node_factory.get_node(id1, options={**pluginopts, **{'trust_node': id2}})
    l2: LightningNode = node_factory.get_node(id2, options=pluginopts, **{'trust_node': id1})
    l3: LightningNode = node_factory.get_node(options=pluginopts)

    l3.connect(l1)
    l3.fund_channel(l1, 1_000_000)
    # l3 should be able to pay l2 through l1
    invoice = l2.rpc.invoice(100000, "test", "Test Invoice")
    l3.rpc.pay(invoice["bolt11"])
