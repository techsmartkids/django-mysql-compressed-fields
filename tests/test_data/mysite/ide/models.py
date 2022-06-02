from django.db import models
from mysql_compressed_fields.fields import CompressedTextField
from typing import cast


# TODO: Rename before release -> TextFile
class ProjectTextFile(models.Model):
    # TODO: Rename before release -> name
    relpath = cast(str, models.CharField(
        max_length=150,
        help_text='ex: program.py',
    ))
    content = cast(str, CompressedTextField(
        blank=True,
        # (Has no max_length)
        help_text="ex: print('Hello World!')",
        db_column='content_compressed',
    ))
