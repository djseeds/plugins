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
def init(options, configuration, plugin):
    plugin.log("Plugin helloworld.py initialized")


@plugin.hook("htlc_accepted")
def on_htlc_connected(plugin, onion, next_onion, shared_secret, htlc):
  """ Main method for receiving on behalf of trusted node.
  """
  plugin.log("Got an incoming HTLC htlc={}, onion={}".format(htlc, onion))
  return {"result": "continue"}


@plugin.hook("rpc_command")
def on_rpc_command(plugin, rpc_command):
  """ Routes RPC commands to handlers or allows clightning to continue.
  """
  plugin.log("Got an incoming RPC command method={}".format(rpc_command.method))
  handlers = {
    'sendpay': on_sendpay,
    'invoice': on_invoice,
  }

  handler = handlers.get(rpc_command.method, lambda: {"result": "continue"})
  return handler(plugin, rpc_command)


def on_sendpay(plugin, rpc_command):
  return {"result": "continue"}


def on_invoice(plugin, rpc_command):
  return {"result": "continue"}

@plugin.hook("custommsg")
def on_custommsg(plugin, peer_id, message):
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

plugin.add_option('greeting', 'Hello', 'The greeting I should use.')
plugin.run()
