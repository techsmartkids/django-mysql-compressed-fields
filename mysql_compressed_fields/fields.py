import django
from django import forms
from django.contrib import admin
from django.db import IntegrityError, models
from django.db.models import Func, Lookup, lookups
from django.utils.encoding import smart_text, force_bytes
from django.utils.translation import ugettext_lazy as _
from mysql_compressed_fields.functions import compress, uncompress


# ------------------------------------------------------------------------------
# CompressedTextField

class CompressedTextField(models.Field):
    """
    A large text field, stored compressed in the database.
    
    Generally behaves like TextField. Stores values in the database using the
    same database column type as BinaryField. The value is compressed in the
    same format that MySQL's COMPRESS() function uses. Compression and
    decompression is performed by Django and not the database.
    
    If you specify a max_length attribute, it will be reflected in the
    Textarea widget of the auto-generated form field. However it is not
    enforced at the model or database level. The max_length applies to the
    length of the uncompressed text rather than the compressed text.
    
    String-based lookups can be used with this field type.
    Such lookups will transparently decompress the field on the database server.
    
        html_files = ProjectTextFile.objects.filter(content__contains='<html')
        html_files = ProjectTextFile.objects.filter(content__startswith='<!DOCTYPE')
        html_files = ProjectTextFile.objects.filter(content__endswith='</html>')
        empty_html_files = ProjectTextFile.objects.filter(content__in=['', '<html></html>'])
    
    Note that F-expressions that reference this field type will always refer to
    the compressed value rather than the uncompressed value. So you may need to
    use the Compress() and Uncompress() database functions manually when working
    with F-expressions.
    
        # Copy a TextField value (in utf8 collation) to a CompressedTextField
        ProjectTextFile.objects.filter(...).update(content=Compress(F('name')))
        
        # Copy a CompressedTextField value to a TextField (in utf8 collation)
        ProjectTextFile.objects.filter(...).update(name=Uncompress(F('content')))
        
        # Copy a CompressedTextField value to a CompressedTextField
        ProjectTextFile.objects.filter(...).update(content=F('content'))
    """
    description = _('Text')

    # Define database column type
    def get_internal_type(self):
        return 'BinaryField'  # currently maps to 'longblob'
    
    # Since the database column type is binary, must override get_placeholder
    # to return binary_placeholder_sql to support storing binary values that are
    # not UTF-8 decodable
    def get_placeholder(self, value, compiler, connection):
        # HACK: Backport fix for https://code.djangoproject.com/ticket/26140,
        #       committed Mar 14, 2016 for Django 1.10
        if django.VERSION[:2] < (1, 10):
            if connection.vendor == 'mysql':
                return '_binary %s' if value is not None else '%s'
            else:
                return '%s'
        else:
            return connection.ops.binary_placeholder_sql(value)
    
    # Convert Python value -> database value
    def get_db_prep_value(self, value, connection, prepared=False):
        value = super(CompressedTextField, self).get_db_prep_value(value, connection, prepared)
        if prepared:
            return value
        else:
            if value is None:
                return None
            else:
                if not isinstance(value, str):
                    value = smart_text(value)  # reinterpret
                database_value = compress(value.encode('utf8'))
                return connection.Database.Binary(database_value)
    
    # Convert database value -> Python value
    def from_db_value(self, database_value, expression, connection, context=None):
        if database_value is None:
            return None
        value_bytes = uncompress(database_value)
        value = value_bytes.decode('utf8')
        return value
    
    # Convert Python value of self -> serialized value
    def value_to_string(self, obj):
        return self.value_from_object(obj)
    
    # Convert {uncleaned form value, serialized value} -> Python value
    def to_python(self, form_or_serialized_value):
        return form_or_serialized_value
    
    # Define default form field
    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length, 'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(CompressedTextField, self).formfield(**defaults)


# Patch Django
from django.contrib.admin.options import FORMFIELD_FOR_DBFIELD_DEFAULTS
FORMFIELD_FOR_DBFIELD_DEFAULTS[CompressedTextField] = {'widget': admin.widgets.AdminTextareaWidget}


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
# CompressedTextField > Lookups

class _UncompressedLhsMixin(object):
    def process_lhs(self, compiler, connection, lhs=None):
        if connection.vendor != 'mysql':
            raise ValueError(
                ('String-based lookups for CompressedTextField such as %s can '
                 'only be used with a MySQL database') % type(self).__name__)
        lhs, params = super(_UncompressedLhsMixin, self).process_lhs(compiler, connection, lhs)
        return 'UNCOMPRESS(%s)' % lhs, []


class _Contains(_UncompressedLhsMixin, lookups.Contains):
    pass
CompressedTextField.register_lookup(_Contains)


class _StartsWith(_UncompressedLhsMixin, lookups.StartsWith):
    pass
CompressedTextField.register_lookup(_StartsWith)


class _EndsWith(_UncompressedLhsMixin, lookups.EndsWith):
    pass
CompressedTextField.register_lookup(_EndsWith)


class _In(_UncompressedLhsMixin, lookups.In):
    pass
CompressedTextField.register_lookup(_In)


class _UncompressedLength(Lookup):
    lookup_name = 'uncompressedlength'
    
    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return 'UNCOMPRESSED_LENGTH(%s) = %s' % (lhs, rhs), params
CompressedTextField.register_lookup(_UncompressedLength)


# ------------------------------------------------------------------------------
