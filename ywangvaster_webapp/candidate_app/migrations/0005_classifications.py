import uuid
from django.db import migrations

"""Populate the Classification table with a few entries on first start of the webapp."""


def create_classification_entries(apps, schema_editor):

    Classification = apps.get_model("candidate_app", "Classification")

    initial_data = [
        {
            "hash_id": uuid.uuid4(),
            "name": "Noise",
            "description": "Random noise and not a possible object",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Aeroplane",
            "description": "Aeroplane flying in way of beam during observation",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "FRB",
            "description": "Possible FRB detection",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Pulsar - Uncatalogued",
            "description": "Possible new pulsar detected",
        },
        {
            "hash_id": uuid.uuid4(),
            "name": "Pulsar - Catalogued",
            "description": "Already known and catalogued pulsar in exsiting DB",
        },
    ]

    for data in initial_data:
        Classification.objects.create(**data)


class Migration(migrations.Migration):

    dependencies = [("candidate_app", "0004_candidate_material_views")]

    operations = [
        migrations.RunPython(create_classification_entries),
    ]
