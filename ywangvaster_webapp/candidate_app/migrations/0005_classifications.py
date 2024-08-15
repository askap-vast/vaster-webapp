import uuid
from django.db import migrations

"""Populate the Classification table with a few entries on first start of the webapp."""


def create_classification_entries(apps, schema_editor):

    Classification = apps.get_model("candidate_app", "Classification")

    initial = [
        {
            "hash_id": uuid.uuid4(),
            "name": "Flaring star",
            "description": "Radio flaring stars",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Unknown",
            "description": "Unknown objects, not in any catalogues",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "AGN",
            "description": "Active Galactic Nuclei",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "IDV",
            "description": "Intra-day variability, extreme scintillating AGN",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Noise",
            "description": "Random noise and not a possible object",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Sidelobes",
            "description": "Sidelobes of a bright source",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Artefacts",
            "description": "Artefacts in the image, not a real object",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Aeroplane or Satellite",
            "description": "Aeroplane or Satellite flying in way of beam during observation",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "FRB",
            "description": "Possible FRB detection",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "New pulsar",
            "description": "Possible new pulsar detected",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Known pulsar",
            "description": "Already known and catalogued pulsar in existing DB",
        },
    ]

    for data in initial:
        Classification.objects.create(**data)


class Migration(migrations.Migration):

    dependencies = [("candidate_app", "0004_candidate_material_views")]

    operations = [
        migrations.RunPython(create_classification_entries),
    ]
