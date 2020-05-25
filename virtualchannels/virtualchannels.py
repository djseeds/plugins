#!/usr/bin/env python3
from enum import Enum
from pyln.client import Plugin

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
  trusted = plugin.get_option("trust_node")
  pass

@plugin.method("test")
def send_message(plugin: Plugin, name="test"):
  pass
  
@plugin.hook("htlc_accepted")
def on_htlc_accepted(plugin, **kwargs):
  """ Main method for receiving on behalf of trusted node.
  """
  return {"result": "continue"}


@plugin.hook("rpc_command")
def on_rpc_command(plugin, rpc_command, **kwargs):
  """ Routes RPC commands to handlers or allows clightning to continue.
  """
  method = rpc_command["method"]
  plugin.log("Got an incoming RPC command method={}".format(method))
  handlers = {
    'pay': on_pay,
    'invoice': on_invoice,
  }

  handler = handlers.get(method, lambda a, b: {"result": "continue"})
  return handler(plugin, rpc_command)


def on_pay(plugin, rpc_command):
  # Send invoice to trusted nodes, aggregate the result.
  return {"result": "continue"}


def on_invoice(plugin, rpc_command):
  return {"result": "continue"}

@plugin.hook("custommsg")
def on_custommsg(plugin, peer_id, message, **kwargs):
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
