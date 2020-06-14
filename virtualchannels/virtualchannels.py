#!/usr/bin/env python3
from random import SystemRandom
from string import hexdigits
from pyln.client import Plugin
import messages
from hashlib import sha256

trusted_nodes = []
preimages = dict()

plugin = Plugin()

@plugin.init()
def init(options, configuration, plugin: Plugin):
  global trusted_nodes
  opt = plugin.get_option("trust_node")
  trusted_nodes = opt.split(",") if opt != "null" else []

@plugin.hook("htlc_accepted")
def on_htlc_accepted(plugin: Plugin, htlc, **kwargs):
  """ Main method for receiving on behalf of trusted node.
  """

  # TODO: Need to receive an ack from source before sending response to support type 2 channels (finite capacity)
  if htlc["payment_hash"] in preimages:
    plugin.log("We have this preimage!: " + preimages[htlc["payment_hash"]])
    return {
      "result": "resolve",
      "payment_key": preimages[htlc['payment_hash']]
    }
  else:
    plugin.log("We don't have preimage for hash: " + htlc["payment_hash"] + " preimages: " + str(preimages))
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

  def generate_preimage() -> str:
    return ''.join([SystemRandom().choice(hexdigits) for _ in range(64)])

  kwargs['preimage'] = generate_preimage() if preimage is None else preimage
  if routes:
    kwargs['dev-routes'] = routes

  invoice = plugin.rpc.call('invoice', kwargs)

  msg = messages.InitVirtualReceive(kwargs['preimage'])
  # Notify trusted nodes of new invoice
  plugin.log("custommsg " + msg.to_hex())
  for node in trusted_nodes:
    plugin.rpc.call("dev-sendcustommsg", {
      "node_id": node,
      "msg": msg.to_hex()
    })

  return invoice

@plugin.hook("custommsg")
def on_custommsg(plugin: Plugin, peer_id, message, **kwargs):
  # TODO: Understand what the first 4 bytes mean. Doesn't seem to be length?
  # e.g. here: https://github.com/ElementsProject/lightning/blob/ce9e559aed5c491f09b570545aabedb2a2c64402/tests/test_misc.py#L2237
  msg = messages.Message.from_hex(message[8:])

  plugin.log("custommsg " + message)

  handler = message_handlers.get(msg.__class__, lambda *args, **kwargs: {"result": "continue"})
  return handler(plugin, peer_id, msg)

@plugin.method("openvirtualchannel")
def on_openvirtualchannel(plugin: Plugin, id):
  """ Open an infinite-capacity private virtual channel with `id`.
  Note: this fully trusts `id` to receive and send payments on your behalf.
  """
  if plugin.rpc.getpeer(id) is None:
    return {
      "error": {
        "message": "Failed to find peer with id {id}".format(id=id)
      }
    }
  # Only allow 1 virtual channel per peer
  if id in trusted_nodes:
    return {
      "error": {
        "message": "Multiple virtual channels to the same peer are not supported"
      }
    }
  # Create a virtual channel with a new short channel ID
  trusted_nodes.append(id)

  # TODO: Decide how to generate short channel IDs for these channels
  return {
    "result": {
      "short_channel_id": "0x0x0",
    }
  }
  

def on_init_virtual_receive(plugin: Plugin, peer_id, message: messages.InitVirtualReceive):
  """ Contents: preimage bolt11
  """
  h = sha256(bytes.fromhex(message.preimage)).hexdigest()
  preimages[h] = message.preimage
  return {"result": "continue"}


message_handlers = {
  messages.InitVirtualReceive: on_init_virtual_receive,
}

plugin.run()
