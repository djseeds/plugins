from pyln.testing.fixtures import *
from pyln.client import RpcError
from pyln.testing.utils import wait_for
from time import sleep
import json
import unittest


pluginopts = {'plugin': os.path.join(os.path.dirname(__file__), "virtualchannels.py")}

def open_virtual_channel(src: LightningNode, dst: LightningNode):
    src.rpc.call("openvirtualchannel", {"id": dst.info["id"]})

def test_vcinvoice(node_factory: NodeFactory):
    l1, l2, l3 = node_factory.get_nodes(3, pluginopts) # type: LightningNode, LightningNode, LightningNode

    # Open virtual channel from l1 to l2.
    l1.connect(l2)
    open_virtual_channel(l1, l2)

    l3: LightningNode = node_factory.get_node(options=pluginopts)

    l1.connect(l3)
    l3.openchannel(l1, 1_000_000)

    payload = {
        "msatoshi": 9000000,
        "label": "test",
        "description": "test",
    }

    # l1 should create a valid invoice with a routing hint pointing to l2
    res = l1.rpc.call("vcinvoice", payload)
    invoice_details = l1.rpc.decodepay(res["bolt11"])
    info = l1.rpc.getinfo()
    assert(invoice_details["payee"] == info["id"])
    assert(len(invoice_details["routes"]) == 1)
    assert(len(invoice_details["routes"][0]) == 1)
    assert(invoice_details["routes"][0][0]["pubkey"] == l2.info["id"])

    # l2 should create a valid invoice with no routing hints
    res = l2.rpc.call("vcinvoice", payload)
    invoice_details = l2.rpc.decodepay(res["bolt11"])
    assert(invoice_details["payee"] == l2.info["id"])
    assert(invoice_details.get("routes", None) is None)
    

def test_concrete_send(node_factory: NodeFactory):
    """ Ensure concrete send still works with plugin activated
    """
    l1, l2, l3 = node_factory.get_nodes(3, pluginopts) # type: LightningNode, LightningNode, LightningNode

    l1.connect(l3)
    l1.openchannel(l3, 1_000_000)
    # l1 should be able to pay l3 directly
    invoice = l3.rpc.invoice(9000000, "test", "test")
    sleep(1)
    l1.rpc.pay(invoice["bolt11"])
    #l1.pay(l3, 100000)

def test_virtual_send(node_factory: NodeFactory):
    l1, l2, l3 = node_factory.get_nodes(3, pluginopts) # type: LightningNode, LightningNode, LightningNode

    l1.connect(l3)
    l1.fund_channel(l3, 1_000_000)

    l2.connect(l1)
    # l1 trusts l2
    open_virtual_channel(l1, l2)

    sleep(1)

    amt = 9000000

    # l2 should be able to send to l3 through l1
    invoice = l3.rpc.invoice(amt, "test", "Test Invoice")
    l2.rpc.call('vcpay', {"bolt11": invoice["bolt11"]})

    # Payment has already succeeded from l2's point of view. Ensure l3 actually got the money.
    wait_for(lambda : int(l3.rpc.listfunds()['channels'][0]['our_amount_msat']) == amt)

def test_concrete_receive(node_factory: NodeFactory):
    """ Ensure concrete receive still works with plugin activated
    """
    l1, l2, l3 = node_factory.get_nodes(3, pluginopts) # type: LightningNode, LightningNode, LightningNode

    l3.connect(l1)
    l3.fund_channel(l1, 1_000_000)
    # l3 should be able to pay l3 directly
    invoice = l1.rpc.invoice(100000, "test", "Test Invoice")

    sleep(10)
    l3.pay(l1, 100000)

def test_virtual_receive(node_factory: NodeFactory):
    l1, l2, l3 = node_factory.get_nodes(3, pluginopts) # type: LightningNode, LightningNode, LightningNode
    l2.connect(l1)
    open_virtual_channel(l2, l1)

    l3.connect(l1)
    l3.fund_channel(l1, 1_000_000)
    amt = 9000000
    payload = {
        "msatoshi": amt,
        "label": "test",
        "description": "test",
    }
    # TODO: connect when opening virtual channel
    l2.connect(l1)
    invoice = l2.rpc.call('vcinvoice', payload)
    # l3 should be able to pay l2 through virtual channel with l1 
    l3.rpc.pay(invoice["bolt11"])

    # Payment has already succeeded from l3's point of view. Ensure l1 actually got the money.
    wait_for(lambda : int(l1.rpc.listfunds()['channels'][0]['our_amount_msat']) == amt)
