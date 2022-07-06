from django import forms
from django.core import serializers
from django.db import connection
from django.db.models import F
from django.test import TestCase
from ide.models import ProjectTextFile
from mysql_compressed_fields import (
    Compress, Uncompress, UncompressedLength, compress, compressed_length
)


class CompressedTextFieldTests(TestCase):
    UNCOMPRESSED_PYTHON_VALUES = [
        '',         # empty strings are treated specially by COMPRESS()
        'hello',
        'hello  ',  # trailing spaces are treated specially by COMPRESS()
    ]
    
    def test_blank_field_initialized_to_empty_string(self):
        ptf = _create_project_text_file()
        self.assertEqual('', ptf.content)
        ptf.save()
        
        ptf = ProjectTextFile.objects.get(id=ptf.id)
        self.assertEqual('', ptf.content)
    
    def test_value_is_saved_as_compressed_and_loaded_as_uncompressed(self):
        for uncompressed_python_value in self.UNCOMPRESSED_PYTHON_VALUES:
            with self.subTest(uncompressed_python_value=uncompressed_python_value):
                ptf = _create_project_text_file()
                ptf.content = uncompressed_python_value
                ptf.save()
                
                uncompressed_database_value = self._get_uncompressed_database_value(ptf.id)
                self.assertEqual(
                    uncompressed_python_value, uncompressed_database_value,
                    'Expected saved value in database to be compressed')
                
                ptf = ProjectTextFile.objects.get(id=ptf.id)
                self.assertEqual(
                    uncompressed_python_value, ptf.content,
                    'Expected loaded value in model to be uncompressed')
    
    def test_value_is_updated_as_compressed(self):
        for uncompressed_python_value in self.UNCOMPRESSED_PYTHON_VALUES:
            with self.subTest(uncompressed_python_value=uncompressed_python_value):
                ptf = _create_project_text_file()
                ptf.save()
                
                ProjectTextFile.objects.filter(id=ptf.id).update(
                    content=uncompressed_python_value)
                
                uncompressed_database_value = self._get_uncompressed_database_value(ptf.id)
                self.assertEqual(
                    uncompressed_python_value, uncompressed_database_value,
                    'Expected updated value in database to be compressed')
    
    def test_value_can_be_serialized_and_deserialized(self):
        for uncompressed_python_value in self.UNCOMPRESSED_PYTHON_VALUES:
            with self.subTest(uncompressed_python_value=uncompressed_python_value):
                ptf = _create_project_text_file()
                ptf.content = uncompressed_python_value
                
                ptf_as_xml = serializers.serialize('xml', [ptf])
                self.assertIn(
                    uncompressed_python_value, ptf_as_xml,
                    'Expected serialized value to be uncompressed value')
                
                # NOTE: Comparing stripped values rather than the raw values
                #       because Django strips whitespace from serialized text fields.
                #       See: https://code.djangoproject.com/ticket/22088
                (ptf_do,) = serializers.deserialize('xml', ptf_as_xml)
                ptf = ptf_do.object
                self.assertEqual(
                    uncompressed_python_value.strip(), ptf.content.strip(),
                    'Expected stripped value in deserialized model to match original value')
    
    def test_default_form_field_is_text_area(self):
        field = ProjectTextFile._meta.get_field('content')
        form_field = field.formfield()
        self.assertTrue(isinstance(form_field, forms.CharField))
        self.assertTrue(isinstance(form_field.widget, forms.Textarea))
    
    # === Utility ===
    
    def _get_uncompressed_database_value(self, ptf_id):
        table = ProjectTextFile._meta.db_table
        field = ProjectTextFile._meta.get_field('content')
        column = field.get_attname_column()[1]
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT UNCOMPRESS(%s) FROM %s WHERE id = %%s' % (column, table),
                [ptf_id])
            uncompressed_database_value = cursor.fetchall()[0][0].decode('utf8')
        return uncompressed_database_value


class CompressedTextFieldLookupTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.ptf1 = _create_project_text_file()
            cls.ptf1.content = 'abc'
            cls.ptf1.save()
            
            cls.ptf2 = _create_project_text_file()
            cls.ptf2.content = 'def'
            cls.ptf2.save()
        except:
            super().tearDownClass()
            raise
    
    def test_contains_lookup_matches_uncompressed_value(self):
        matches = list(ProjectTextFile.objects.filter(
            id__in=[self.ptf1.id, self.ptf2.id],
            content__contains='b'))
        self.assertEqual([self.ptf1], matches)
    
    def test_startswith_lookup_matches_uncompressed_value(self):
        matches = list(ProjectTextFile.objects.filter(
            id__in=[self.ptf1.id, self.ptf2.id],
            content__startswith='a'))
        self.assertEqual([self.ptf1], matches)
    
    def test_endswith_lookup_matches_uncompressed_value(self):
        matches = list(ProjectTextFile.objects.filter(
            id__in=[self.ptf1.id, self.ptf2.id],
            content__endswith='c'))
        self.assertEqual([self.ptf1], matches)
    
    def test_in_lookup_matches_uncompressed_value(self):
        matches = list(ProjectTextFile.objects.filter(
            id__in=[self.ptf1.id, self.ptf2.id],
            content__in=['abc', '123']))
        self.assertEqual([self.ptf1], matches)


class CompressionFuncTests(TestCase):
    def setUp(self):
        self.ptf = _create_project_text_file()
        self.ptf.name = 'abc'
        self.ptf.content = 'def'
        self.ptf.save()
    
    def test_can_bulk_copy_compressed_field_to_uncompressed(self):
        ProjectTextFile.objects.filter(id=self.ptf.id).update(
            name=Uncompress(F('content')))
        self.ptf = ProjectTextFile.objects.get(id=self.ptf.id)
        self.assertEqual('def', self.ptf.name)
    
    def test_can_bulk_copy_uncompressed_field_to_compressed(self):
        ProjectTextFile.objects.filter(id=self.ptf.id).update(
            content=Compress(F('name')))
        self.ptf = ProjectTextFile.objects.get(id=self.ptf.id)
        self.assertEqual('abc', self.ptf.content)
    
    def test_can_bulk_copy_compressed_field_to_compressed(self):
        ProjectTextFile.objects.filter(id=self.ptf.id).update(
            content=F('content'))
        self.ptf = ProjectTextFile.objects.get(id=self.ptf.id)
        self.assertEqual('def', self.ptf.content)
    
    def test_can_get_uncompressed_length_of_field(self):
        ProjectTextFile.objects.filter(id=self.ptf.id).update(
            name=UncompressedLength(F('content')))
        self.ptf = ProjectTextFile.objects.get(id=self.ptf.id)
        self.assertEqual('3', self.ptf.name)
    
    def test_can_get_compressed_length_of_value(self):
        for uncompressed_python_value in CompressedTextFieldTests.UNCOMPRESSED_PYTHON_VALUES:
            with self.subTest(uncompressed_python_value=uncompressed_python_value):
                uncompressed_python_value_bytes = uncompressed_python_value.encode('utf8')
                self.assertEqual(
                    len(compress(uncompressed_python_value_bytes)),
                    compressed_length(uncompressed_python_value_bytes))


def _create_project_text_file():
    return ProjectTextFile(name='ignored')
