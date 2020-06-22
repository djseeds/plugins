import struct
from enum import Enum
from string import hexdigits
from io import BytesIO
from pyln.proto.onion import TlvPayload, TlvField
from pyln.proto.primitives import varint_decode
from pyln.proto.invoice import Invoice

class Message():
  typeNum: int = None

  @classmethod
  def from_bytes(cls: type, b: bytes):
    """ Deserializes a message """
    (t, msg) = split_message(b)
    # Create dict: message type -> Message class's from_bytes method
    messages = { message.typeNum: message.from_bytes for message in all_subclasses(cls) if message.typeNum is not None}

    return messages.get(t, lambda *args, **kwargs: None)(msg)

  @classmethod
  def from_hex(cls, message: str) -> 'Message':
    """ Parses a message """
    return cls.from_bytes(bytes.fromhex(message))

  def to_bytes(self) -> bytes:
    """ Serializes this message """
    raise NotImplementedError("Message is an abstract class.")

  def to_hex(self) -> str:
    """ Serializes this message """
    return self.to_bytes().hex()

class TlvMessage(Message):
  @classmethod
  def from_bytes(cls, b):
    return cls.from_tlv_payload(TlvPayload.from_bytes(b, skip_length=True))

  def to_bytes(self) -> bytes:
    # Since c-lightning adds the length, we need to remove it here.
    with_len = self.to_tlv_payload().to_bytes()
    b = BytesIO(with_len)
    varint_decode(b)
    return self.typeNum.to_bytes(2, 'big') + b.read()

  @classmethod
  def from_tlv_payload(cls, payload: TlvPayload):
    return cls()

  def to_tlv_payload(self) -> TlvPayload:
    return TlvPayload([
    ])


class InitVirtualChannel(TlvMessage):
  typeNum: int = 0xFFA7

class InitVirtualReceive(TlvMessage):
  typeNum: int = 0xFFA9
  PREIMAGE_TYPE_NUM: int = 623058254
  BOLT11_TYPE_NUM: int = 3682297234
  
  def __init__(self, preimage: str, bolt11: str):
    self.preimage = preimage
    self.bolt11  = bolt11

  @classmethod
  def from_tlv_payload(cls, payload: TlvPayload):
    preimage = payload.get(cls.PREIMAGE_TYPE_NUM).value.hex()
    bolt11 = payload.get(cls.BOLT11_TYPE_NUM).value.decode('ASCII')
    return cls(preimage, bolt11)

  def to_tlv_payload(self) -> TlvPayload:
    return TlvPayload([
      TlvField(self.PREIMAGE_TYPE_NUM, bytes.fromhex(self.preimage)),
      TlvField(self.BOLT11_TYPE_NUM, self.bolt11.encode('ASCII'))
    ])

  @property
  def invoice(self) -> Invoice:
    return Invoice.decode(self.bolt11)

class InitVirtualSend(TlvMessage):
  typeNum: int = 0xFFAB
  BOLT11_TYPE_NUM: int        = 3682297234
  MSATOSHI_TYPE_NUM: int      = 3572037896
  LABEL_TYPE_NUM: int         = 365787384
  RISKFACTOR_TYPENUM: int     = 3135098887
  MAXFEEPERCENT_TYPENUM: int  = 602977222
  RETRY_FOR_TYPENUM: int      = 3748374816
  MAXDELAY_TYPENUM: int       = 2204790513
  EXEMPTFEE_TYPENUM: int      = 2141027454
  
  def __init__(self, bolt11: str, msatoshi: int = None, label: str = None, riskfactor: int = None, maxfeepercent: float = None, retry_for: int = None, maxdelay: int = None, exemptfee: int = None):
    self.bolt11  = bolt11
    self.msatoshi = msatoshi
    self.label = label
    self.riskfactor = riskfactor
    self.maxfeepercent = maxfeepercent
    self.retry_for = retry_for
    self.maxdelay = maxdelay
    self.exemptfee = exemptfee

  @classmethod
  def from_tlv_payload(cls, payload: TlvPayload):
    bolt11 = payload.get(cls.BOLT11_TYPE_NUM).value.decode('ASCII')

    # Optional fields
    msatoshi = decode_tu64(payload.get(cls.MSATOSHI_TYPE_NUM, TlvField(None, None)).value)
    label = decode_ascii(payload.get(cls.LABEL_TYPE_NUM, TlvField(None, None)).value)
    riskfactor = decode_tu64(payload.get(cls.RISKFACTOR_TYPENUM, TlvField(None, None)).value)
    maxfeepercent = decode_tu64(payload.get(cls.MAXFEEPERCENT_TYPENUM, TlvField(None, None)).value)
    retry_for = decode_tu64(payload.get(cls.RETRY_FOR_TYPENUM, TlvField(None, None)).value)
    maxdelay = decode_tu64(payload.get(cls.MAXDELAY_TYPENUM, TlvField(None, None)).value)
    exemptfee = decode_tu64(payload.get(cls.EXEMPTFEE_TYPENUM, TlvField(None, None)).value)

    return cls(bolt11, msatoshi, label, riskfactor, maxfeepercent, retry_for, maxdelay, exemptfee)

  def to_tlv_payload(self) -> TlvPayload:
    return TlvPayload([x for x in
      [
        TlvField(self.BOLT11_TYPE_NUM, self.bolt11.encode('ASCII')),
        TlvField(self.MSATOSHI_TYPE_NUM, encode_tu64(self.msatoshi)),
        TlvField(self.LABEL_TYPE_NUM, encode_ascii(self.label)),
        TlvField(self.RISKFACTOR_TYPENUM, encode_tu64(self.riskfactor)),
        TlvField(self.MAXFEEPERCENT_TYPENUM, encode_tu64(self.maxfeepercent)),
        TlvField(self.RETRY_FOR_TYPENUM, encode_tu64(self.RETRY_FOR_TYPENUM)),
        TlvField(self.MAXDELAY_TYPENUM, encode_tu64(self.maxdelay)),
        TlvField(self.EXEMPTFEE_TYPENUM, encode_tu64(self.exemptfee))
      ] if x.value is not None])

  @property
  def invoice(self) -> Invoice:
    return Invoice.decode(self.bolt11)

class VirtualSendFailure(TlvMessage):
  typeNum: int = 0xFFAD

  BOLT11_TYPE_NUM: int = 3682297234

  def __init__(self, bolt11: str):
    self.bolt11  = bolt11

  @classmethod
  def from_tlv_payload(cls, payload: TlvPayload):
    bolt11 = payload.get(cls.BOLT11_TYPE_NUM).value.decode('ASCII')
    return cls(bolt11)

  @property
  def invoice(self) -> Invoice:
    return Invoice.decode(self.bolt11)

  def to_tlv_payload(self) -> TlvPayload:
    return TlvPayload([
      TlvField(self.BOLT11_TYPE_NUM, self.bolt11.encode('ASCII'))
    ])

class VirtualSendSuccess(TlvMessage):
  typeNum: int = 0xFFAF
  PREIMAGE_TYPE_NUM: int = 623058254
  BOLT11_TYPE_NUM: int = 3682297234
  
  def __init__(self, preimage: str, bolt11: str):
    self.preimage = preimage
    self.bolt11  = bolt11

  @classmethod
  def from_tlv_payload(cls, payload: TlvPayload):
    preimage = payload.get(cls.PREIMAGE_TYPE_NUM).value.hex()
    bolt11 = payload.get(cls.BOLT11_TYPE_NUM).value.decode('ASCII')
    return cls(preimage, bolt11)

  def to_tlv_payload(self) -> TlvPayload:
    return TlvPayload([
      TlvField(self.PREIMAGE_TYPE_NUM, bytes.fromhex(self.preimage)),
      TlvField(self.BOLT11_TYPE_NUM, self.bolt11.encode('ASCII'))
    ])

  @property
  def invoice(self) -> Invoice:
    return Invoice.decode(self.bolt11)

def split_message(message: bytes):
  t = int.from_bytes(message[0:2], byteorder='big')
  return (t, message[2:])

def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])

def decode_tu64(b: bytes):
  return int.from_bytes(b, 'big') if b is not None else None

def encode_tu64(i: int):
  return i.to_bytes(i.bit_length() // 8 + 1, 'big') if i is not None else None

def decode_ascii(b: bytes):
  return b.decode('ASCII') if b is not None else None

def encode_ascii(s: str):
  return s.encode('ASCII') if s is not None else None
