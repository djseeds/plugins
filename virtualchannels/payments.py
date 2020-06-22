import messages

from pyln.client import RpcError, Plugin
from pyln.client.plugin import Request, LightningRpc

from dataclasses import dataclass
from typing import Dict, List

import inspect

pending_payments : Dict[str, 'Payment'] = dict()

@dataclass
class Payment:
  # Request that initiated this payment, so we can respond later
  request: Request
  rpc: LightningRpc
  virtualchannels: List[str]
  plugin: Plugin

  errors = []

  # Payment arguments
  bolt11: str
  msatoshi: int = None
  label: str = None
  riskfactor: int = None
  maxfeepercent: float = None
  retry_for: int = None
  maxdelay: int = None
  exemptfee: int = None

  def start(self):
    """ Starts a payment, first trying a concrete payment, followed by virtual payment attempts as necessary. """
    try:
      # Currently we implement this naively -- first try a concrete send
      res = self.rpc.pay(**self.get_payment_kwargs())
      self.send_success(res)
    except RpcError as error:
      # If fails, we try with each of our virtual channel partners sequentially.
      self.errors.append(error)
      self.attempt_virtual_send()
  
  def get_payment_kwargs(self):
    (args, _, _, _) = inspect.getargspec(self.rpc.pay)
    return {k:v for k,v in self.__dict__.items() if k in args}
    

  def attempt_virtual_send(self):
    if self.virtualchannels:
      node = self.virtualchannels.pop(0)

      try:
        self.rpc.call("dev-sendcustommsg", {
          "node_id": node,
          "msg": messages.InitVirtualSend(**self.get_payment_kwargs()).to_hex()
        })
      except RpcError as error:
        self.errors.append(error)
        # Try the next node.
        self.attempt_virtual_send()

    else:
      # Out of virtual channels to try
      self.send_failure()
  
  def on_virtual_send_failure(self):
    self.send_failure()

  def on_virtual_send_success(self):
    self.send_success({"result": "success!"})

  def send_failure(self):
    self.request.set_exception({"errors": self.errors})
    self.remove_from_pending()

  def send_success(self, details):
    self.request.set_result({"result": details})
    self.remove_from_pending()

  def remove_from_pending(self):
    pending_payments.pop(self.bolt11, None)

