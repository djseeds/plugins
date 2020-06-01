#!/usr/bin/env python3
from random import SystemRandom
from string import hexdigits
from enum import Enum
import re
from pyln.client import Plugin
from lnaddr import  LnAddr, lnencode_unsigned, bitarray_to_u5
from bech32 import bech32_encode
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
  trusted_nodes = plugin.get_option("trust_node")
  pass

@plugin.method("test")
def send_message(plugin: Plugin, name="test"):
  pass
  
@plugin.hook("htlc_accepted")
def on_htlc_accepted(plugin: Plugin, **kwargs):
  """ Main method for receiving on behalf of trusted node.
  """
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
def on_invoice(plugin: Plugin, msatoshi, label, description, expiry=None, fallbacks=None, preimage=None, exposeprivatechannels=None):
  def generate_preimage():
    return ''.join([SystemRandom().choice(hexdigits) for _ in range(64)])

  if preimage is None:
    preimage = generate_preimage()
  elif len(preimage) != 64 and all(c in hexdigits for c in preimage):
    # Preimage is a 64-digit hex string
    raise ValueError("Bad Preimage")

  # TODO: The msatoshi parameter can be the string "any", which creates an invoice that can be paid with any amount
  def parse_msatoshi(msatoshi: str):
    """ Parse msatoshi field in invoice.
    The msatoshi parameter can be the string “any”, which creates an invoice that can be paid with any amount.
    Otherwise it is in millisatoshi precision;
    it can be
    - a whole number
    - or a whole number ending in msat or sat,
    - or a number with three decimal places ending in sat
    - or a number with 1 to 11 decimal places ending in btc.
    """
    if msatoshi == "Any":
      raise NotImplementedError("Still not sure how to handle the Any case")
    if msatoshi.isdigit():
      return int(msatoshi)
    elif msatoshi.endswith("msat"):
      msat = msatoshi[:-4]
      if msat.isdigit:
        return int(msat)
      else:
        raise ValueError("msatoshi ends in msat but is not a whole number.")
    elif msatoshi.endswith("sat"):
      sat = msatoshi[:-3]
      if sat.isdigit():
        return int(msat) * 1000
      elif re.match(r"\d+\.\d{3}$", sat):
        return int(float(msat) * 1000)
      else:
        raise ValueError("msatoshi ends in sat but is not a whole number or a number with three decimal places.")
    elif msatoshi.endswith("btc"):
      btc = msatoshi[:-3]
      if re.match(r"\d+\.\d{1,11}$", btc):
        return int(float(btc) * 100_000_000_000)
      else:
        raise ValueError("msatoshi ends in btc but is not a number with 1 to 11 decimal places")
    else:
      raise NotImplementedError("Parsing not implemented yet")

  #amount = parse_msatoshi(msatoshi)
  amount = msatoshi

  # TODO: Store preimage

  def sign_invoice(plugin: Plugin, hrp: str, data: BitArray):
    message = (bytearray([ord(c) for c in hrp]) + data.tobytes()).hex()
    res = plugin.rpc.signmessage(message)
    return res["signature"], res["recid"]
    
  tags = []
  # Add description field
  tags.append(('d', description))

  # Add pubkey
  info = plugin.rpc.getinfo()
  tags.append(('n', bytearray.fromhex(info["id"])))


  # Get invoice
  addr = LnAddr(sha256(bytearray.fromhex(preimage)).digest(), amount, currency='bcrt', tags=tags)
  hrp, data = lnencode_unsigned(addr)
  sig, recid = sign_invoice(plugin, hrp, data)
  data += bytes.fromhex(sig) + bytes.fromhex(recid)
  invoice = bech32_encode(hrp, bitarray_to_u5(data))
  return {"bolt11": invoice}



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
