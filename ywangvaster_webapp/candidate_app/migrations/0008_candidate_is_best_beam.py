from django.db import migrations, models


def compute_is_best_beam(apps, schema_editor):
    # Import the live model so we can use the rerank_best_beam_group() instance
    # method. This is safe because this RunPython step runs after the AddField
    # above, so is_best_beam already exists on the table.
    from candidate_app.models import Candidate

    for candidate in Candidate.objects.all():
        candidate.rerank_best_beam_group()


def reverse_compute_is_best_beam(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("candidate_app", "0007_alter_candidate_options_alter_rating_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="is_best_beam",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            compute_is_best_beam,
            reverse_compute_is_best_beam,
        ),
    ]
