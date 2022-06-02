# django-mysql-compressed-fields

This package provides [CompressedTextField](#CompressedTextField), a
MySQL-specific Django model field similar to [TextField] that stores its
value in compressed form.

Compression and decompression of field values is performed by Django rather
than the database whenever possible, to conserve centralized 
database CPU resources.

[TextField]: https://docs.djangoproject.com/en/1.8/ref/models/fields/#textfield
[BinaryField]: https://docs.djangoproject.com/en/1.8/ref/models/fields/#binaryfield

### Dependencies

* [Django] 3.2 or later required
* [MySQL] 5.7 or later required

[Django]: https://www.djangoproject.com/
[MySQL]: https://www.mysql.com/

### License

[MIT](LICENSE)

### Sponsor

This project is brought to you by [TechSmart], which seeks to inspire the
next generation of K-12 teachers and students to learn to code and create
amazing things with computers. We use [Django] heavily.

[TechSmart]: https://www.techsmart.codes/

## API Reference

### Fields (`mysql_compressed_fields.fields`)

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

    xml_files = TextFile.objects.filter(content__contains='<xml>')
    xml_files = TextFile.objects.filter(content__startswith='<xml>')
    xml_files = TextFile.objects.filter(content__endswith='</xml>')
    empty_xml_files = TextFile.objects.filter(content__in=['', '<xml></xml>'])

Note that F-expressions that reference this field type will always refer to
the compressed value rather than the uncompressed value. So you may need to
use the Compress() and Uncompress() database functions manually when working
with F-expressions.

    # Copy a TextField value (in utf8 collation) to a CompressedTextField
    TextFile.objects.filter(...).update(content=Compress(F('name')))
    
    # Copy a CompressedTextField value to a TextField (in utf8 collation)
    TextFile.objects.filter(...).update(name=Uncompress(F('content')))
    
    # Copy a CompressedTextField value to a CompressedTextField
    TextFile.objects.filter(...).update(content=F('content'))


### Database functions (`mysql_compressed_fields.functions`)

[F() expressions]: https://docs.djangoproject.com/en/4.0/ref/models/expressions/#f-expressions

#### `Compress`

The MySQL COMPRESS() function, usable in [F() expressions].
See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_compress

#### `Uncompress`

The MySQL UNCOMPRESS() function, usable in [F() expressions].
See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompress

#### `UncompressedLength`

The MySQL UNCOMPRESSED_LENGTH() function, usable in [F() expressions].
See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompressed-length

#### `compress`

```python
def compress(uncompressed_bytes: bytes) -> bytes:
```

The MySQL COMPRESS() function.
See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_compress

#### `uncompress`

```python
def uncompress(compressed_bytes: bytes) -> bytes:
```

The MySQL UNCOMPRESS() function.
See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompress

#### `uncompressed_length`

```python
def uncompressed_length(compressed_bytes: bytes) -> int:
```

The MySQL UNCOMPRESSED_LENGTH() function.
See: https://dev.mysql.com/doc/refman/5.7/en/encryption-functions.html#function_uncompressed-length

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
    * `docker run --name ide_db_server -e MYSQL_DATABASE=ide_db -e MYSQL_ROOT_PASSWORD=root -p 127.0.0.1:3306:3306 -d mysql:5.7`
* Run tests:
    * `cd tests/test_data/mysite`
    * `poetry install`
    * `poetry run python3 manage.py test`

[Docker]: https://www.docker.com/
