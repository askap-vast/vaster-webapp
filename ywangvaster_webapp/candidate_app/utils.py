from django.http import HttpResponse
from astropy.io import fits
import numpy as np

from django import template

import os
import shutil


def FITSTableType(val):
    """
    Return the FITSTable type corresponding to each named parameter in obj
    """
    if isinstance(val, bool):
        types = "L"
    elif isinstance(val, (int, np.int64, np.int32)):
        types = "J"
    elif isinstance(val, (float, np.float64, np.float32)):
        types = "E"
    elif isinstance(val, str):
        types = "{0}A".format(len(val))
    else:
        types = "5A"
    return types


def download_fits(request, queryset, table):

    opts = queryset.model._meta

    response = HttpResponse(content_type="application/octet-stream")
    # force download.
    response["Content-Disposition"] = f'attachment; filename="{table}.fits"'

    cols = []
    for name in [field.name for field in opts.fields]:
        # Cause error columns to always be floats even when they are set to -1
        if name.startswith("err_"):
            fmt = "E"
        else:
            fmt = FITSTableType(getattr(queryset.first(), name))
        cols.append(
            fits.Column(
                name=name,
                format=fmt,
                array=[a[0] for a in queryset.all().values_list(name)],
            )
        )

    cols = fits.ColDefs(cols)
    tbhdu = fits.BinTableHDU.from_columns(cols)
    tbhdu.writeto(response)

    return response


def get_disk_space(path):
    """Get the total used space in gigabytes for a particular path."""

    total, used, free = shutil.disk_usage(path)

    # Convert to gb
    total_gb = total / (1024**3)
    used_gb = used / (1024**3)
    free_gb = free / (1024**3)

    return total_gb, used_gb, free_gb


def count_files(directory):
    """Recursively count the number of files in a directory.

    :param path: Path to the directory to count the files.
    :return: Number of files under the "path" directory."""

    file_count = 0
    for root, dirs, files in os.walk(directory):
        file_count += len(files)

    return file_count
