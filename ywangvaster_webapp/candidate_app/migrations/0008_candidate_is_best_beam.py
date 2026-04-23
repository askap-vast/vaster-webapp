from django.db import migrations, models
from django.db.models import Q
from django_q3c.expressions import Q3CRadialQuery

# 5 arcsec in degrees — matches BEST_BEAM_RADIUS_DEG in models.py
_BEST_BEAM_RADIUS_DEG = 5 / 3600.0


def compute_is_best_beam(apps, schema_editor):
    # Use the historical model snapshot rather than importing the live
    # Candidate class. Importing the live class would pull in columns added by
    # later migrations (e.g. dynamic_spectra_png from 0009) and break on any
    # database that hasn't reached those migrations yet. The historical model
    # only knows about columns that exist at this point in migration history,
    # so ORM queries against it are safe. Q3CRadialQuery is a plain SQL
    # expression and works with any model.
    Candidate = apps.get_model("candidate_app", "Candidate")

    for candidate in Candidate.objects.all():
        group = (
            Candidate.objects.filter(observation_id=candidate.observation_id)
            .filter(
                Q(
                    Q3CRadialQuery(
                        center_ra=candidate.ra,
                        center_dec=candidate.dec,
                        ra_col="ra",
                        dec_col="dec",
                        radius=_BEST_BEAM_RADIUS_DEG,
                    )
                )
            )
            .order_by("beam_sep_deg", "hash_id")
        )
        best = group.first()
        if best is not None:
            group.filter(hash_id=best.hash_id).update(is_best_beam=True)
            group.exclude(hash_id=best.hash_id).update(is_best_beam=False)


def reverse_compute_is_best_beam(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("candidate_app", "0007_alter_candidate_options_alter_rating_options"),
    ]

    operations = [
        # Drop trigger BEFORE AddField to prevent materialized view refresh
        # on every row update during the bulk operations
        migrations.RunSQL(
            "DROP TRIGGER refresh_candidate_min_max_stats_trigger ON candidate_app_candidate;",
            reverse_sql="""
                CREATE TRIGGER refresh_candidate_min_max_stats_trigger
                AFTER INSERT OR UPDATE OR DELETE ON candidate_app_candidate
                FOR EACH STATEMENT EXECUTE FUNCTION refresh_candidate_min_max_stats();
            """,
        ),
        migrations.AddField(
            model_name="candidate",
            name="is_best_beam",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            compute_is_best_beam,
            reverse_compute_is_best_beam,
        ),
        # Recreate trigger after all updates complete
        migrations.RunSQL(
            """
                CREATE TRIGGER refresh_candidate_min_max_stats_trigger
                AFTER INSERT OR UPDATE OR DELETE ON candidate_app_candidate
                FOR EACH STATEMENT EXECUTE FUNCTION refresh_candidate_min_max_stats();
            """,
            reverse_sql="DROP TRIGGER refresh_candidate_min_max_stats_trigger ON candidate_app_candidate;",
        ),
    ]
