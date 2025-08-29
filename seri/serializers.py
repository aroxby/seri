from seri.fields import BaseField


class SerializerMeta(type):
    @staticmethod
    def _get_fields(attrs: dict) -> dict:
        # Note: Dictionaries preserve insertion order
        fields = {key: value for key, value in attrs.items() if isinstance(value, BaseField)}
        return fields

    def __new__(cls, name, bases, attrs, **kwds):
        attrs['fields'] = cls._get_fields(attrs)
        return super().__new__(cls, name, bases, attrs)


class Serializer(metaclass=SerializerMeta):
    fields = {}

    def deserialize(self, data: bytes) -> (dict, int):
        attrs = {}
        offset = 0
        for name, field in self.fields.items():
            if field.deserialize_predicate is None or field.deserialize_predicate(
                self, name, field, attrs, data, offset
            ):
                attrs[name], field_length = field.deserialize(data[offset:])
                field.validate(attrs[name])
                offset += field_length
        return attrs, offset

    def serialize(self, attrs: dict) -> bytes:
        data = b''
        for name, field in self.fields.items():
            if field.serialize_predicate is None or field.serialize_predicate(self, name, field, attrs, data):
                data += field.serialize(attrs[name])
        return data
