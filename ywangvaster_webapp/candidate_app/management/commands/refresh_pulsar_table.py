#! /usr/bin/env python

from urllib import request
import tarfile
from io import BytesIO
from astropy.coordinates import SkyCoord
import astropy.units as u

from django.core.management.base import BaseCommand
from django.db import transaction
from candidate_app.models import ATNFPulsar

ATNF_LINK = (
    "https://www.atnf.csiro.au/research/pulsar/psrcat/downloads/psrcat_pkg.tar.gz"
)


class Command(BaseCommand):
    help = "Update the pulsar table based on the ATNF pulsar database"

    def handle(self, *args, **kwargs):
        with request.urlopen(request.Request(ATNF_LINK), timeout=15.0) as response:
            if response.status == 200:
                tar = tarfile.open(name=None, fileobj=BytesIO(response.read()))
                psrdb = tar.extractfile("psrcat_tar/psrcat.db")
                # unzip
            else:
                raise Exception("unable to download .tar file")

        dec, ra, lat, long, pos = None, None, None, None, None
        name = None
        db_dict = {}
        for ln in psrdb:
            line = ln.decode()
            if line.startswith("@-"):
                print(db_dict[name])
                dec, ra, lat, long, pos = None, None, None, None, None
                name = None
            elif "PSRJ" in line:
                name = line.split()[1]
                db_dict[name] = {}
            elif "DECJ" in line:
                dec = line.split()[1]
            elif "RAJ" in line:
                ra = line.split()[1]
            elif "ELAT" in line:
                lat = line.split()[1]
            elif "ELONG" in line:
                long = line.split()[1]
            elif "DM" in line:
                db_dict[name]["dm"] = float(line.split()[1])
            elif "P0" in line:
                db_dict[name]["p0"] = float(line.split()[1])
            elif "S400" in line:
                db_dict[name]["s400"] = float(line.split()[1])

            if (dec is not None) and (ra is not None):
                pos = SkyCoord(ra, dec, unit=(u.hour, u.degree), frame="fk5")
            if (lat is not None) and (long is not None):
                pos = SkyCoord(
                    l=long, b=lat, unit=(u.degree, u.degree), frame="galactic"
                ).transform_to("fk5")

            if pos is not None:
                db_dict[name]["raj"] = pos.ra.degree
                db_dict[name]["decj"] = pos.ra.degree

        with transaction.atomic():
            ATNFPulsar.objects.all().delete()
            for rec in db_dict.keys():
                psr = ATNFPulsar()
                psr.name = rec
                psr.raj = db_dict[rec]["raj"]
                psr.decj = db_dict[rec]["decj"]
                psr.DM = db_dict[rec].get("dm", None)
                psr.p0 = db_dict[rec].get("p0", None)
                psr.s400 = db_dict[rec].get("s400", None)
                psr.save()
