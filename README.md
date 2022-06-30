# django-mysql-compressed-fields

This package provides [CompressedTextField], a MySQL-specific
Django model field similar to [TextField] or [CharField] that stores its
value in compressed form via [zlib].

In particular you can replace a TextField or CharField like:

```python
from django.db import models

class ProjectTextFile(models.Model):
    content = models.TextField(blank=True)
```

with:

```python
from django.db import models
from mysql_compressed_fields import CompressedTextField

class ProjectTextFile(models.Model):
    content = CompressedTextField(blank=True)
```

such that the text value of the field is actually compressed in the database.

String-based lookups are supported:

```python
html_files = ProjectTextFile.objects.filter(content__contains='<html')
html_files = ProjectTextFile.objects.filter(content__startswith='<!DOCTYPE')
html_files = ProjectTextFile.objects.filter(content__endswith='</html>')
empty_html_files = ProjectTextFile.objects.filter(content__in=['', '<html></html>'])
```

Advanced manipulations with MySQL's [COMPRESS()], [UNCOMPRESS()], and 
[UNCOMPRESSED_LENGTH()] functions are also supported:

```python
from django.db.models import F
from mysql_compressed_fields import UncompressedLength

files = ProjectTextFile.objects.only('id').annotate(
    content_length=UncompressedLength(F('content'))
)
```

[TextField]: https://docs.djangoproject.com/en/3.2/ref/models/fields/#textfield
[BinaryField]: https://docs.djangoproject.com/en/3.2/ref/models/fields/#binaryfield
[CharField]: https://docs.djangoproject.com/en/3.2/ref/models/fields/#charfield
[CompressedTextField]: #CompressedTextField
[zlib]: https://docs.python.org/3/library/zlib.html

### Dependencies

* [Django] 3.2 or later required
* [MySQL] 5.7 or later required
* ...and nothing else 🎉

[Django]: https://www.djangoproject.com/
[MySQL]: https://www.mysql.com/

### License

[MIT](LICENSE)

### Migration Steps

To migrate an existing TextField or CharField to be a CompressedTextField:

* Install this package:
    * `pip3 install django-mysql-compressed-fields`
* Find an existing Django model with an uncompressed [TextField] or [CharField]
  that you want to compress. For example:

```python
from django.db import models

class ProjectTextFile(models.Model):
    content = models.TextField(blank=True)
```

* Add a `*_compressed` sibling field that will be used to hold the compressed
  version of the original field. Mark it as `default=''`. Include an explicit
  `db_column=...` value:

```python
from django.db import models
from mysql_compressed_fields import CompressedTextField

class ProjectTextFile(models.Model):
    content = models.TextField(blank=True)
    content_compressed = CompressedTextField(
        blank=True,
        default='',  # needed by Django when adding a field
        db_column='content_compressed',  # pin column name
    )
```

* Generate a migration to add the compressed field:
    * `python3 manage.py makemigrations`
* Generate a new empty migration in the same app where the field is defined,
  which we will use to populate the compressed field:
    * `python3 manage.py makemigrations --empty __APP_NAME__`
* Open the empty migration file. It should look something like:

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('ide', '0002_projecttextfile_content_compressed'),
    ]

    operations = [
    ]
```

* Edit the `operations` field to use a RunPython step to populate
  the compressed field from the uncompressed field:

```python
from django.db import migrations
from django.db.models import F
from mysql_compressed_fields import Compress

def _populate_content_compressed(apps, schema_editor):
    ProjectTextFile = apps.get_model('ide', 'ProjectTextFile')
    # NOTE: Assumes "content" field is already UTF-8 encoded,
    #       because CompressedTextField assumes UTF-8 encoding.
    ProjectTextFile.objects.update(content_compressed=Compress(F('content')))

class Migration(migrations.Migration):
    dependencies = [
        ('ide', '0002_projecttextfile_content_compressed'),
    ]

    operations = [
        migrations.RunPython(
            code=_populate_content_compressed,
            reverse_code=migrations.RunPython.noop,
            atomic=False,
        )
    ]
```

* Remove the original uncompressed field from the model,
  leaving only the compressed field remaining:
  

```python
from django.db import models
from mysql_compressed_fields import CompressedTextField

class ProjectTextFile(models.Model):
    content_compressed = CompressedTextField(
        blank=True,
        default='',  # needed by Django when adding a field
        db_column='content_compressed',  # pin column name
    )
```

* Generate a migration to remove the uncompressed field:
    * `python3 manage.py makemigrations`
* Rename the compressed field without the `*_compressed` suffix
  so that it now has the name of the original uncompressed field:

```python
from django.db import models
from mysql_compressed_fields import CompressedTextField

class ProjectTextFile(models.Model):
    content = CompressedTextField(
        blank=True,
        default='',  # needed by Django when adding a field
        db_column='content_compressed',  # pin column name
    )
```

* Generate a migration to rename the field:
    * `python3 manage.py makemigrations`
    * When prompted whether the field was renamed, answer `y` (for yes).
* You now have a compressed version of the original field. All done! 🎉

### Sponsor

This project is brought to you by [TechSmart], which seeks to inspire the
next generation of K-12 teachers and students to learn coding and create
amazing things with computers. We use Django heavily.

[TechSmart]: https://www.techsmart.codes/

## API Reference

All classes and functions below should be imported directly from 
`mysql_compressed_fields`. For example:

```python
from mysql_compressed_fields import CompressedTextField
```

### Fields

#### `CompressedTextField`

A large text field, stored compressed in the database.

Generally behaves like [TextField]. Stores values in the database using the
same database column type as [BinaryField]. The value is compressed in the
same format that MySQL's COMPRESS() function uses. Compression and
decompression is performed by Django and not the database.

If you specify a max_length attribute, it will be reflected in the
Textarea widget of the auto-generated form field. However it is not
enforced at the model or database level. The max_length applies to the
length of the uncompressed text rather than the compressed text.

String-based lookups can be used with this field type.
Such lookups will transparently decompress the field on the database server.

```python
html_files = ProjectTextFile.objects.filter(content__contains='<html')
html_files = ProjectTextFile.objects.filter(content__startswith='<!DOCTYPE')
html_files = ProjectTextFile.objects.filter(content__endswith='</html>')
empty_html_files = ProjectTextFile.objects.filter(content__in=['', '<html></html>'])
```

Note that F-expressions that reference this field type will always refer to
the compressed value rather than the uncompressed value. So you may need to
use the Compress() and Uncompress() database functions manually when working
with F-expressions.

```python
# Copy a TextField value (in utf8 collation) to a CompressedTextField
ProjectTextFile.objects.filter(...).update(content=Compress(F('name')))

# Copy a CompressedTextField value to a TextField (in utf8 collation)
ProjectTextFile.objects.filter(...).update(name=Uncompress(F('content')))

# Copy a CompressedTextField value to a CompressedTextField
ProjectTextFile.objects.filter(...).update(content=F('content'))
```

The default form widget for this field is a 
`django.contrib.admin.widgets.AdminTextareaWidget` (a kind of [TextInput]).

[TextInput]: https://docs.djangoproject.com/en/3.2/ref/forms/widgets/#textinput


### Database functions

[F() expressions]: https://docs.djangoproject.com/en/4.0/ref/models/expressions/#f-expressions

#### `Compress`

The MySQL [COMPRESS()] function, usable in [F() expressions].

[COMPRESS()]: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_compress

#### `Uncompress`

The MySQL [UNCOMPRESS()] function, usable in [F() expressions].

[UNCOMPRESS()]: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompress

#### `UncompressedLength`

The MySQL [UNCOMPRESSED_LENGTH()] function, usable in [F() expressions].

[UNCOMPRESSED_LENGTH()]: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompressed-length

#### `compress`

```python
def compress(uncompressed_bytes: bytes) -> bytes:
```

The MySQL [COMPRESS()] function.

#### `uncompress`

```python
def uncompress(compressed_bytes: bytes) -> bytes:
```

The MySQL [UNCOMPRESS()] function.

#### `uncompressed_length`

```python
def uncompressed_length(compressed_bytes: bytes) -> int:
```

The MySQL [UNCOMPRESSED_LENGTH()] function.

#### `compressed_length`

```python
def compressed_length(
    uncompressed_bytes: bytes,
    *, chunk_size: int=64 * 1000,
    stop_if_greater_than: Optional[int]=None) -> int:
```

Returns the length of COMPRESS(uncompressed_bytes).

If `stop_if_greater_than` is specified and a result greater than
`stop_if_greater_than` is returned then the compressed length is
no less than the returned result.

## Running Tests

* Install [Docker].
* Install MySQL CLI tools:
    * If macOS, install using brew: `brew install mysql-client@5.7`
    * Otherwise install from source: https://downloads.mysql.com/archives/community/
* Add MySQL CLI tools to path:
    * `export PATH="/usr/local/opt/mysql-client@5.7/bin:$PATH"`
* Start MySQL server:
    * `docker run --name ide_db_server -e MYSQL_DATABASE=ide_db -e MYSQL_ROOT_PASSWORD=root -p 127.0.0.1:8889:3306 -d mysql:5.7`
* Run tests:
    * `cd tests/test_data/mysite`
    * `poetry install`
    * `poetry run python3 manage.py test`

[Docker]: https://www.docker.com/
