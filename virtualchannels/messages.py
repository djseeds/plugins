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
      raise NotImplementedError("TlvMessage is an abstract class.")

    def to_tlv_payload(self):
      raise NotImplementedError("TlvMessage is an abstract class.")


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


def split_message(message: bytes):
  t = int.from_bytes(message[0:2], byteorder='big')
  return (t, message[2:])

def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])
