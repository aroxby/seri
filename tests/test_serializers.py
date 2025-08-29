import unittest
from seri import fields
from seri.serializers import Serializer, SerializerMeta


class TestSerializerMeta(unittest.TestCase):
    def test_field_collection_basic(self):
        """Test that SerializerMeta correctly collects BaseField instances from class attributes."""
        class TestSerializer(Serializer):
            field1 = fields.UInt8()
            field2 = fields.UInt16()
            non_field = "not a field"
            another_non_field = 42
        
        # Check that only BaseField instances are collected
        expected_fields = ['field1', 'field2']
        self.assertEqual(list(TestSerializer.fields.keys()), expected_fields)
        self.assertIsInstance(TestSerializer.fields['field1'], fields.UInt8)
        self.assertIsInstance(TestSerializer.fields['field2'], fields.UInt16)
    
    def test_field_collection_empty(self):
        """Test that SerializerMeta works with no fields."""
        class EmptySerializer(Serializer):
            non_field = "not a field"
        
        self.assertEqual(EmptySerializer.fields, {})
    
    def test_field_collection_order_preservation(self):
        """Test that field order is preserved (insertion order)."""
        class OrderedSerializer(Serializer):
            third = fields.UInt32()
            first = fields.UInt8()
            second = fields.UInt16()
        
        field_names = list(OrderedSerializer.fields.keys())
        self.assertEqual(field_names, ['third', 'first', 'second'])
    
    def test_inheritance_field_collection(self):
        """Test that inherited serializers correctly collect fields from base classes."""
        class BaseSerializer(Serializer):
            base_field = fields.UInt8()
        
        class DerivedSerializer(BaseSerializer):
            derived_field = fields.UInt16()
        
        # Base serializer should only have its own field
        self.assertEqual(list(BaseSerializer.fields.keys()), ['base_field'])
        
        # Derived serializer should have its own field (base class fields handled by inheritance)
        self.assertEqual(list(DerivedSerializer.fields.keys()), ['derived_field'])


class TestSerializer(unittest.TestCase):
    def test_empty_serializer(self):
        """Test serializer with no fields."""
        class EmptySerializer(Serializer):
            pass
        
        serializer = EmptySerializer()
        
        # Serialize empty data
        result = serializer.serialize({})
        self.assertEqual(result, b'')
        
        # Deserialize empty data
        attrs, offset = serializer.deserialize(b'')
        self.assertEqual(attrs, {})
        self.assertEqual(offset, 0)
    
    def test_single_field_serializer(self):
        """Test serializer with a single field."""
        class SingleFieldSerializer(Serializer):
            value = fields.UInt8()
        
        serializer = SingleFieldSerializer()
        
        # Test serialization
        data = serializer.serialize({'value': 42})
        self.assertEqual(data, b'\x2a')  # 42 in hex
        
        # Test deserialization
        attrs, offset = serializer.deserialize(b'\x2a\xff')  # Extra data should be ignored
        self.assertEqual(attrs, {'value': 42})
        self.assertEqual(offset, 1)
    
    def test_multiple_fields_serializer(self):
        """Test serializer with multiple fields of different types."""
        class MultiFieldSerializer(Serializer):
            byte_val = fields.UInt8()
            short_val = fields.UInt16()
            int_val = fields.UInt32()
        
        serializer = MultiFieldSerializer()
        
        # Test serialization
        data = serializer.serialize({
            'byte_val': 0x12,
            'short_val': 0x3456,
            'int_val': 0x789ABCDE
        })
        expected = b'\x12\x56\x34\xde\xbc\x9a\x78'  # Little endian
        self.assertEqual(data, expected)
        
        # Test deserialization
        attrs, offset = serializer.deserialize(expected + b'\xff\xff')  # Extra data
        self.assertEqual(attrs, {
            'byte_val': 0x12,
            'short_val': 0x3456,
            'int_val': 0x789ABCDE
        })
        self.assertEqual(offset, 7)
    
    def test_string_fields(self):
        """Test serializer with string fields."""
        class StringSerializer(Serializer):
            zstring = fields.ZString()
            fixed_string = fields.FixedString(5)
        
        serializer = StringSerializer()
        
        # Test serialization
        data = serializer.serialize({
            'zstring': 'hello',
            'fixed_string': 'world'
        })
        expected = b'hello\x00world'
        self.assertEqual(data, expected)
        
        # Test deserialization
        attrs, offset = serializer.deserialize(expected)
        self.assertEqual(attrs, {
            'zstring': 'hello',
            'fixed_string': 'world'
        })
        self.assertEqual(offset, 11)
    
    def test_byte_array_field(self):
        """Test serializer with byte array field."""
        class ByteArraySerializer(Serializer):
            header = fields.ByteArray(4)
            data = fields.UInt16()
        
        serializer = ByteArraySerializer()
        
        # Test serialization
        result = serializer.serialize({
            'header': b'\x01\x02\x03\x04',
            'data': 0x1234
        })
        expected = b'\x01\x02\x03\x04\x34\x12'
        self.assertEqual(result, expected)
        
        # Test deserialization
        attrs, offset = serializer.deserialize(expected)
        self.assertEqual(attrs, {
            'header': b'\x01\x02\x03\x04',
            'data': 0x1234
        })
        self.assertEqual(offset, 6)
    
    def test_encoded_length_field(self):
        """Test serializer with encoded length field."""
        class EncodedLengthSerializer(Serializer):
            name = fields.EncodedLength(fields.UInt8(), fields.DynamicString())
        
        serializer = EncodedLengthSerializer()
        
        # Test serialization
        data = serializer.serialize({'name': 'test'})
        expected = b'\x04test'  # Length (4) + string data
        self.assertEqual(data, expected)
        
        # Test deserialization
        attrs, offset = serializer.deserialize(expected)
        self.assertEqual(attrs, {'name': 'test'})
        self.assertEqual(offset, 5)
    
    def test_nested_serializer(self):
        """Test serializer with nested serializer field."""
        class InnerSerializer(Serializer):
            x = fields.UInt16()
            y = fields.UInt16()
        
        class OuterSerializer(Serializer):
            id = fields.UInt8()
            point = fields.NestedSerializer(InnerSerializer())
            name = fields.ZString()
        
        serializer = OuterSerializer()
        
        # Test serialization
        data = serializer.serialize({
            'id': 42,
            'point': {'x': 100, 'y': 200},
            'name': 'test'
        })
        expected = b'\x2a\x64\x00\xc8\x00test\x00'  # id + x + y + name + null
        self.assertEqual(data, expected)
        
        # Test deserialization
        attrs, offset = serializer.deserialize(expected)
        self.assertEqual(attrs, {
            'id': 42,
            'point': {'x': 100, 'y': 200},
            'name': 'test'
        })
        self.assertEqual(offset, 10)
    
    def test_complex_serializer(self):
        """Test a more complex serializer combining multiple field types."""
        class ComplexSerializer(Serializer):
            magic = fields.ByteArray(4)
            version = fields.UInt16()
            name = fields.EncodedLength(fields.UInt8(), fields.DynamicString())
            flags = fields.UInt32()
            description = fields.ZString()
        
        serializer = ComplexSerializer()
        
        test_data = {
            'magic': b'TEST',
            'version': 256,
            'name': 'example',
            'flags': 0x12345678,
            'description': 'A test serializer'
        }
        
        # Test serialization
        data = serializer.serialize(test_data)
        
        # Test deserialization
        attrs, offset = serializer.deserialize(data)
        self.assertEqual(attrs, test_data)
        
        # Verify the data structure
        expected_parts = [
            b'TEST',  # magic
            b'\x00\x01',  # version (256 in little endian)
            b'\x07example',  # name length + name
            b'\x78\x56\x34\x12',  # flags (little endian)
            b'A test serializer\x00'  # description + null terminator
        ]
        expected_data = b''.join(expected_parts)
        self.assertEqual(data, expected_data)
    
    def test_serializer_field_order_matters(self):
        """Test that field order in serializer definition matters for serialization."""
        class OrderedSerializer(Serializer):
            second = fields.UInt8()  # Defined first but named 'second'
            first = fields.UInt8()   # Defined second but named 'first'
        
        serializer = OrderedSerializer()
        
        # The serialization should follow definition order, not alphabetical
        data = serializer.serialize({'second': 1, 'first': 2})
        self.assertEqual(data, b'\x01\x02')  # second (1) then first (2)
        
        attrs, offset = serializer.deserialize(b'\x01\x02')
        self.assertEqual(attrs, {'second': 1, 'first': 2})
    
    def test_partial_deserialization(self):
        """Test that deserialization works with exact amount of data."""
        class TestSerializer(Serializer):
            a = fields.UInt8()
            b = fields.UInt16()
        
        serializer = TestSerializer()
        
        # Test with exact data length
        data = b'\x01\x02\x03'
        attrs, offset = serializer.deserialize(data)
        self.assertEqual(attrs, {'a': 1, 'b': 0x0302})
        self.assertEqual(offset, 3)
    
    def test_serializer_with_validators(self):
        """Test serializer with fields that have validators."""
        def positive_validator(value):
            if value <= 0:
                raise fields.ValidationError("Value must be positive")
        
        class ValidatedSerializer(Serializer):
            positive_int = fields.UInt32(validator=positive_validator)
        
        serializer = ValidatedSerializer()
        
        # Test normal serialization/deserialization (validators aren't called automatically)
        data = serializer.serialize({'positive_int': 42})
        attrs, offset = serializer.deserialize(data)
        self.assertEqual(attrs, {'positive_int': 42})
        
        # Note: The current implementation doesn't automatically call validators
        # during serialize/deserialize, so we test that the field has the validator
        field = serializer.fields['positive_int']
        self.assertIsNotNone(field.validator)
        
        # Test validator manually
        with self.assertRaises(fields.ValidationError):
            field.validate(-1)


if __name__ == '__main__':
    unittest.main()