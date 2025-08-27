import unittest
from seri import fields
from seri.fields import ValidationError
from seri.serializers import Serializer


class TestByteArray(unittest.TestCase):
    def test_deserialize(self):
        field = fields.ByteArray(length=4)
        data = b'\x01\x02\x03\x04\x05\x06'
        value, length = field.deserialize(data)
        self.assertEqual(value, b'\x01\x02\x03\x04')
        self.assertEqual(length, 4)

    def test_serialize(self):
        field = fields.ByteArray(length=4)
        obj = b'\x01\x02\x03\x04'
        data = field.serialize(obj)
        self.assertEqual(data, b'\x01\x02\x03\x04')

    def test_serialize_too_long(self):
        field = fields.ByteArray(length=4)
        obj = b'\x01\x02\x03\x04\x05\x06'
        data = field.serialize(obj)
        self.assertEqual(data, b'\x01\x02\x03\x04')

    def test_serialize_too_short_pads_with_nulls(self):
        field = fields.ByteArray(length=4)
        obj = b'\x01\x02'
        data = field.serialize(obj)
        self.assertEqual(b'\x01\x02\x00\x00', data)


class TestUIntFields(unittest.TestCase):
    def test_uint8(self):
        field = fields.UInt8()
        # deserialize
        value, length = field.deserialize(b'\xff\x00')
        self.assertEqual(value, 255)
        self.assertEqual(length, 1)
        # serialize
        data = field.serialize(255)
        self.assertEqual(data, b'\xff')

    def test_uint16(self):
        field = fields.UInt16()
        # deserialize
        value, length = field.deserialize(b'\xff\xff\x00')
        self.assertEqual(value, 65535)
        self.assertEqual(length, 2)
        # serialize
        data = field.serialize(65535)
        self.assertEqual(data, b'\xff\xff')

    def test_uint32(self):
        field = fields.UInt32()
        # deserialize
        value, length = field.deserialize(b'\xff\xff\xff\xff\x00')
        self.assertEqual(value, 4294967295)
        self.assertEqual(length, 4)
        # serialize
        data = field.serialize(4294967295)
        self.assertEqual(data, b'\xff\xff\xff\xff')

    def test_uint64(self):
        field = fields.UInt64()
        # deserialize
        value, length = field.deserialize(b'\xff\xff\xff\xff\xff\xff\xff\xff\x00')
        self.assertEqual(value, 18446744073709551615)
        self.assertEqual(length, 8)
        # serialize
        data = field.serialize(18446744073709551615)
        self.assertEqual(data, b'\xff\xff\xff\xff\xff\xff\xff\xff')


class TestZString(unittest.TestCase):
    def test_deserialize(self):
        field = fields.ZString()
        data = b'hello\0world'
        value, length = field.deserialize(data)
        self.assertEqual(value, 'hello')
        self.assertEqual(length, 6)

    def test_serialize(self):
        field = fields.ZString()
        obj = 'hello'
        data = field.serialize(obj)
        self.assertEqual(data, b'hello\0')


class TestFixedString(unittest.TestCase):
    def test_deserialize(self):
        field = fields.FixedString(length=5)
        data = b'hello world'
        value, length = field.deserialize(data)
        self.assertEqual(value, 'hello')
        self.assertEqual(length, 5)

    def test_serialize(self):
        field = fields.FixedString(length=5)
        obj = 'hello'
        data = field.serialize(obj)
        self.assertEqual(data, b'hello')


class TestDynamicList(unittest.TestCase):
    def test_deserialize(self):
        field = fields.DynamicList(element_field=fields.UInt8())
        field.length = 3
        data = b'\x01\x02\x03\x04'
        value, length = field.deserialize(data)
        self.assertEqual(value, [1, 2, 3])
        self.assertEqual(length, 3)

    def test_serialize(self):
        field = fields.DynamicList(element_field=fields.UInt8())
        obj = [1, 2, 3]
        data = field.serialize(obj)
        self.assertEqual(data, b'\x01\x02\x03')


class TestEncodedLength(unittest.TestCase):
    def test_deserialize(self):
        field = fields.EncodedLength(
            length_field=fields.UInt8(),
            element_field=fields.DynamicString()
        )
        data = b'\x05hello world'
        value, length = field.deserialize(data)
        self.assertEqual(value, 'hello')
        self.assertEqual(length, 6)

    def test_serialize(self):
        field = fields.EncodedLength(
            length_field=fields.UInt8(),
            element_field=fields.DynamicString()
        )
        obj = 'hello'
        data = field.serialize(obj)
        self.assertEqual(data, b'\x05hello')

    def test_deserialize_with_list(self):
        field = fields.EncodedLength(
            length_field=fields.UInt8(),
            element_field=fields.DynamicList(element_field=fields.UInt8())
        )
        data = b'\x03\x01\x02\x03'
        value, length = field.deserialize(data)
        self.assertEqual(value, [1, 2, 3])
        self.assertEqual(length, 4)


class TestNestedSerializer(unittest.TestCase):
    def test_deserialize(self):
        class TestSerializer(Serializer):
            a = fields.UInt8()
            b = fields.UInt8()

        field = fields.NestedSerializer(serializer=TestSerializer())
        data = b'\x01\x02'
        value, length = field.deserialize(data)
        self.assertEqual(value, {'a': 1, 'b': 2})
        self.assertEqual(length, 2)

    def test_serialize(self):
        class TestSerializer(Serializer):
            a = fields.UInt8()
            b = fields.UInt8()

        field = fields.NestedSerializer(serializer=TestSerializer())
        obj = {'a': 1, 'b': 2}
        data = field.serialize(obj)
        self.assertEqual(data, b'\x01\x02')


class TestValidation(unittest.TestCase):
    def test_validator(self):
        validator = lambda v: self.assertEqual(v, 'hello')
        field = fields.FixedString(length=5, validator=validator)
        field.validate('hello')

    def test_file_magic_validator(self):
        validator = fields.file_magic_validator(b'MAG')
        field = fields.ByteArray(length=3, validator=validator)
        field.validate(b'MAG')
        with self.assertRaises(ValidationError):
            field.validate(b'BAD')

class TestReverseFixedString(unittest.TestCase):
    def test_deserialize(self):
        field = fields.ReverseFixedString(length=5)
        data = b'olleh world'
        value, length = field.deserialize(data)
        self.assertEqual(value, 'hello')
        self.assertEqual(length, 5)

    def test_serialize(self):
        field = fields.ReverseFixedString(length=5)
        obj = 'hello'
        data = field.serialize(obj)
        self.assertEqual(data, b'olleh')


class TestDynamicString(unittest.TestCase):
    def test_deserialize(self):
        field = fields.DynamicString()
        field.length = 5
        data = b'hello world'
        value, length = field.deserialize(data)
        self.assertEqual(value, 'hello')
        self.assertEqual(length, 5)

    def test_serialize(self):
        field = fields.DynamicString()
        obj = 'hello'
        data = field.serialize(obj)
        self.assertEqual(data, b'hello')
