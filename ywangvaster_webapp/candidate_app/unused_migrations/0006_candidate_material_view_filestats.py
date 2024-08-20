# This is to create a materialised view for the counts of the number of files and file sizes.
# Consider this when the load times of the "Site Admin" page is more than 20-30 seconds.

# The code currently does a simple count on each page load, instead of doing this. Unfortunately didn't
#  have time to implement this feature.

# Only possible when using a Postgres 16 backend.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = False

    dependencies = [("candidate_app", "0005_create_tags")]

    operations = [
        # Create the materialized view for candidate file stats
        migrations.RunSQL(
            """
            CREATE MATERIALIZED VIEW candidate_file_stats AS
            SELECT 

                -- Its ID
                ROW_NUMBER() OVER () AS id,

                -- One to one relationship to the candiate
                hash_id as candidate_id,
                
                -- Total File Count
                SUM(CASE WHEN lightcurve_png IS NOT NULL THEN 1 END
                    + CASE WHEN slices_gif IS NOT NULL THEN 1 END
                    + CASE WHEN slices_fits IS NOT NULL THEN 1 END
                    + CASE WHEN deepcutout_png IS NOT NULL THEN 1 END
                    + CASE WHEN deepcutout_fits IS NOT NULL THEN 1 END
                ) AS total_file_count,
                
                -- Total File Size in bytes
                SUM(
                    COALESCE(LENGTH(lightcurve_png::bytea), 0) +
                    COALESCE(LENGTH(slices_gif::bytea), 0) +
                    COALESCE(LENGTH(slices_fits::bytea), 0) +
                    COALESCE(LENGTH(deepcutout_png::bytea), 0) +
                    COALESCE(LENGTH(deepcutout_fits::bytea), 0)
                ) AS total_size_gb
            FROM candidate_app_candidate
            GROUP BY hash_id;
            """,
            """
            DROP MATERIALIZED VIEW candidate_file_stats;
            """,
        ),
        # Create a function that will refresh the materialized view when triggered
        migrations.RunSQL(
            """
            CREATE FUNCTION refresh_candidate_file_stats() RETURNS trigger
            AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW candidate_file_stats;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """,
            """
            DROP FUNCTION refresh_candidate_file_stats;
            """,
        ),
        # Create the trigger to run the refresh function on every insert, update, or delete from the candidate table
        migrations.RunSQL(
            """
            CREATE TRIGGER refresh_candidate_file_stats_trigger
            AFTER INSERT OR UPDATE OR DELETE ON candidate_app_candidate
            FOR EACH STATEMENT EXECUTE FUNCTION refresh_candidate_file_stats();
            """,
            """
            DROP TRIGGER refresh_candidate_file_stats_trigger;
            """,
        ),
        # Create the CandidateFileStats model
        migrations.CreateModel(
            name="CandidateFileStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_file_count", models.BigIntegerField(blank=True, null=True)),
                ("total_size_gb", models.FloatField(blank=True, null=True)),
                (
                    "candidate",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="file_stats",
                        to="candidate_app.Candidate",
                        to_field="hash_id",
                    ),
                ),
            ],
            options={
                "db_table": "candidate_file_stats",
                "managed": False,
            },
        ),
    ]
