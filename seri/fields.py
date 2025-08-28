from abc import ABC, abstractmethod

STRING_CODEC = 'cp437'


class BaseField(ABC):
    def __init__(self, validator=None):
        self.validator = validator

    def validate(self, value):
        return self.validator(value) if self.validator else None

    @abstractmethod
    def deserialize(self, data: bytes):
        raise NotImplementedError

    @abstractmethod
    def serialize(self, obj) -> bytes:
        raise NotImplementedError


class ByteArray(BaseField):
    def __init__(self, length: int, validator=None):
        super().__init__(validator)
        self.length = length

    def deserialize(self, data: bytes) -> (bytes, int):
        return data[:self.length], self.length

    def serialize(self, obj: bytes) -> bytes:
        # TODO: Throw an error here if we don't have enough data (also in FixedString)
        return obj[:self.length]


class UInt8(BaseField):
    length = 1

    def deserialize(self, data: bytes) -> (int, int):
        return int.from_bytes(data[:self.length], byteorder='little', signed=False), self.length

    def serialize(self, obj) -> bytes:
        return obj.to_bytes(length=self.length, byteorder='little', signed=False)

class UInt16(UInt8):
    length = 2

class UInt32(UInt8):
    length = 4


class UInt64(UInt8):
    length = 8


class ZString(BaseField):
    def deserialize(self, data: bytes) -> (str, int):
        mbs, _ = data.split(b'\0', 1)
        return mbs.decode(STRING_CODEC), len(mbs) + 1

    def serialize(self, obj) -> bytes:
        return obj.encode(STRING_CODEC) + b'\0'


class DynamicString(BaseField):
    length = 0  # Length isn't known until other fields are deserialized

    def deserialize(self, data: bytes) -> (str, int):
        mbs = data[:self.length]
        return mbs.decode(STRING_CODEC), len(mbs)

    def serialize(self, obj) -> bytes:
        return obj.encode(STRING_CODEC)


class FixedString(DynamicString):
    def __init__(self, length: int, validator=None):
        super().__init__(validator)
        self.length = length


class ReverseFixedString(FixedString):
    def deserialize(self, data: bytes) -> (str, int):
        value, length = super().deserialize(data)
        value = value[::-1]
        return value, length

    def serialize(self, obj) -> bytes:
        return super().serialize(obj[::-1])


class DynamicList(BaseField):
    length = 0  # Length isn't known until other fields are deserialized

    def __init__(self, element_field: BaseField, validator=None):
        super().__init__(validator)
        self.element_field = element_field

    def deserialize(self, data: bytes) -> (list, int):
        offset = 0
        elements = []

        for _ in range(self.length):
            element, element_length = self.element_field.deserialize(data[offset:])
            elements.append(element)
            offset += element_length

        return elements, offset

    def serialize(self, obj) -> bytes:
        data = b''
        for element in obj:
            data += self.element_field.serialize(element)
        return data


class EncodedLength(BaseField):
    def __init__(self, length_field: BaseField, element_field: BaseField, validator=None):
        super().__init__(validator)
        self.length_field = length_field
        self.element_field = element_field

    def deserialize(self, data: bytes):
        length, offset = self.length_field.deserialize(data)
        self.element_field.length = length
        element, element_length = self.element_field.deserialize(data[offset:])
        return element, offset + element_length

    def serialize(self, obj) -> bytes:
        data = self.length_field.serialize(len(obj))
        data += self.element_field.serialize(obj)
        return data


class NestedSerializer(BaseField):
    def __init__(self, serializer: 'Serializer', validator=None):
        super().__init__(validator)
        self.serializer = serializer

    def deserialize(self, data: bytes) -> (dict, int):
        return self.serializer.deserialize(data)

    def serialize(self, obj) -> bytes:
        return self.serializer.serialize(obj)


class ValidationError(Exception):
    pass


def file_magic_validator(magic: bytes):
    def validator(value: bytes):
        if value != magic:
            raise ValidationError
    return validator
