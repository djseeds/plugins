#!/usr/bin/env python3
from random import SystemRandom
from string import hexdigits
from enum import Enum
import re
from pyln.client import Plugin
from hashlib import sha256
from bitstring import BitArray

trusted_nodes = []
invoices = dict()

class MessageType(Enum):
  PROPOSE_VIRTUAL_RECEIVE= 0xFFA9
  ACCEPT_VIRTUAL_RECEIVE= 0xFFAB
  FAIL_VIRTUAL_RECEIVE= 0xFFAD
  PROPOSE_VIRTUAL_SEND= 0xFFAF
  VIRTUAL_SEND_COMPLETE= 0xFFB1
  FAIL_VIRTUAL_SEND= 0xFFB3

plugin = Plugin()

@plugin.init()
def init(options, configuration, plugin: Plugin):
  global trusted_nodes
  opt = plugin.get_option("trust_node")
  trusted_nodes = opt.split(",") if opt != "null" else []

@plugin.hook("htlc_accepted")
def on_htlc_accepted(plugin: Plugin, **kwargs):
  """ Main method for receiving on behalf of trusted node.
  """
  plugin.log("htlc accepted")
  plugin.log("htlc accepted" + str(kwargs))
  # This is how the plugin expects a failure to look -- indeed the payment will fail.
  return {
  "result": "resolve",
  "payment_key": 'C65f6F857D0EeDecd1CbdCb44fEf8DFC637FBBBE73bB3AEDcE71B2FFf7A3a638'
  }
  return {
    "result": "fail",
    "failure_message": "2002"
  }
  return {"result": "continue"}


#@plugin.hook("rpc_command")
#def on_rpc_command(plugin: Plugin, rpc_command, **kwargs):
#  """ Routes RPC commands to handlers or allows clightning to continue.
#  """
#  method = rpc_command["method"]
#  plugin.log("Got an incoming RPC command method={}".format(method))
#  handlers = {
#    'pay': on_pay,
#    'invoice': on_invoice,
#  }
#
#  handler = handlers.get(method, lambda a, **kwargs: {"result": "continue"})
#  return handler(plugin, **(rpc_command["params"]))

def on_pay(plugin: Plugin, **kwargs):
  # Send invoice to trusted nodes, aggregate the result.
  return {"result": "continue"}


@plugin.method("vcinvoice")
def on_vcinvoice(plugin: Plugin, preimage=None, **kwargs):
  routes = [[{
    "id": node,
    # short_channel_id ... is constructed as follows:
    # 1. the most significant 3 bytes: indicating the block height
    # 2. the next 3 bytes: indicating the transaction index within the block
    # 3. the least significant 2 bytes: indicating the output index that pays to the channel.

    # For now this will not be used, as we'll just be checking the preimage hash directly.
    "short_channel_id": "000000" + "x" + "000000" + "x" + "0000",
    "fee_base_msat": 0,
    "fee_proportional_millionths": 0,
    "cltv_expiry_delta": 0,
  }] for node in trusted_nodes]

  def generate_preimage():
    return ''.join([SystemRandom().choice(hexdigits) for _ in range(64)])

  kwargs['preimage'] = generate_preimage() if preimage is None else preimage
  if routes:
    kwargs['dev-routes'] = routes

  # Get invoice
  return plugin.rpc.call('invoice', kwargs)


@plugin.hook("custommsg")
def on_custommsg(plugin: Plugin, peer_id, message, **kwargs):
  # Split message into type and contents
  # Dispatch to handler if one exists
  (type, value) = parse_message(message)
  handlers = {
    MessageType.PROPOSE_VIRTUAL_RECEIVE: on_propose_virtual_receive,
    MessageType.ACCEPT_VIRTUAL_RECEIVE: on_accept_virtual_receive,
    MessageType.FAIL_VIRTUAL_RECEIVE: on_fail_virtual_receive,
    MessageType.PROPOSE_VIRTUAL_SEND: on_propose_virtual_send,
    MessageType.VIRTUAL_SEND_COMPLETE: on_virtual_send_complete,
    MessageType.FAIL_VIRTUAL_SEND: on_fail_virtual_send,
  }

  handler = handlers.get(type, lambda: None)
  handler(value)
  return {"result": "continue"}

def parse_message(message):
  try:
    type = int(message[0:4], 16)
    return (type, message[4:])
  except ValueError:
    return (None, None)

def on_propose_virtual_receive(message):
  """ Contents: payment_hash amount
  """
  pass

def on_accept_virtual_receive(message):
  """ Contents: preimage
  """
  pass

def on_fail_virtual_receive(message):
  """ Contents: reason?
  """
  pass

def on_propose_virtual_send(message):
  """ Contents: route payment_hash [label] [msatoshi] [bolt11] [partid]
  """
  pass

def on_virtual_send_complete(message):
  """ Contents: payment_preimage
  """
  pass

def on_fail_virtual_send(message):
  """ Contents: reason?
  """
  pass

plugin.add_option('trust_node', None, "Fully trust a lightning node, creating an infinite-balance bidirectional virtual channel.")
plugin.run()
