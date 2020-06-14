import struct
from enum import Enum
from string import hexdigits
from io import BytesIO

class MessageType(Enum):
  PROPOSE_VIRTUAL_RECEIVE= 0xFFA9
  ACCEPT_VIRTUAL_RECEIVE= 0xFFAB
  FAIL_VIRTUAL_RECEIVE= 0xFFAD
  PROPOSE_VIRTUAL_SEND= 0xFFAF
  VIRTUAL_SEND_COMPLETE= 0xFFB1
  FAIL_VIRTUAL_SEND= 0xFFB3

class Message():
  typeNum: int = None

  @classmethod
  def from_bytes(cls: type, b: bytes):
    """ Deserializes a message """
    (t, msg) = split_message(b)
    # Create dict: message type -> Message class's from_bytes method
    messages = { message.typeNum: message.from_bytes for message in cls.__subclasses__()}

    return messages.get(t, lambda *args, **kwargs: None)(msg)

  @classmethod
  def from_hex(cls, message: str) -> 'Message':
    """ Parses a message """
    return cls.from_bytes(bytes.fromhex(message))

  def to_bytes(self) -> bytes:
    """ Serializes this message """
    pass

  def to_hex(self) -> str:
    """ Serializes this message """
    return self.to_bytes().hex()
    pass


  def is_valid(self):
    """ Whether this message is valid, and can be serialized successfully """
    pass


class InitVirtualReceive(Message):
  typeNum: int = 0xFFA9

  # Message-specific data
  preimage: str

  def __init__(self, preimage: str = None):
    self.preimage = preimage

  def to_bytes(self) -> bytes:
    """ Serializes this message """
    b = BytesIO()
    b.write(self.typeNum.to_bytes(2, 'big'))
    b.write(bytes.fromhex(self.preimage))
    return b.getvalue()

  @classmethod
  def from_bytes(cls, message: bytes) -> 'InitVirtualReceive':
    """ Parses a message """
    if len(message) != 32:
      raise ValueError("Preimage must be exactly 32 bytes")
    return cls(preimage=message.hex())


def split_message(message: bytes):
  t = int.from_bytes(message[0:2], byteorder='big')
  return (t, message[2:])

def varint_encode(i, w):
    """Encode an integer `i` into the writer `w`
    """
    if i < 0xFD:
        w.write(struct.pack("!B", i))
    elif i <= 0xFFFF:
        w.write(struct.pack("!BH", 0xFD, i))
    elif i <= 0xFFFFFFFF:
        w.write(struct.pack("!BL", 0xFE, i))
    else:
        w.write(struct.pack("!BQ", 0xFF, i))


def varint_decode(r):
    """Decode an integer from reader `r`
    """
    raw = r.read(1)
    if len(raw) != 1:
        return None

    i, = struct.unpack("!B", raw)
    if i < 0xFD:
        return i
    elif i == 0xFD:
        return struct.unpack("!H", r.read(2))[0]
    elif i == 0xFE:
        return struct.unpack("!L", r.read(4))[0]
    else:
        return struct.unpack("!Q", r.read(8))[0]