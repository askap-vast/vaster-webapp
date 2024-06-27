# This is to create a materialised view for the min and max aggregates for the candidate table, used by
# the filtering in candidate_table page.

# Only possible when using a Postgres 16 backend.

# need to have these three RunSQL lines for each table that needs to be updated.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = False

    dependencies = [("candidate_app", "0002_q3c")]

    operations = [
        # Create the materialised view for the candidate min and max stats.
        migrations.RunSQL(
            """
            CREATE MATERIALIZED VIEW candidate_min_max_stats AS
            SELECT 
                ROW_NUMBER() OVER () AS id,

                -- chi_square
                ROUND(CAST(MIN(CASE WHEN chi_square IS NOT NULL AND chi_square NOT IN ('NaN', 'Infinity', '-Infinity') THEN chi_square END) AS numeric), 2) AS min_chi_square,
                ROUND(CAST(MAX(CASE WHEN chi_square IS NOT NULL AND chi_square NOT IN ('NaN', 'Infinity', '-Infinity') THEN chi_square END) AS numeric), 2) AS max_chi_square,

                -- chi_square_sigma
                ROUND(CAST(MIN(CASE WHEN chi_square_sigma IS NOT NULL AND chi_square_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN chi_square_sigma END) AS numeric), 2) AS min_chi_square_sigma,
                ROUND(CAST(MAX(CASE WHEN chi_square_sigma IS NOT NULL AND chi_square_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN chi_square_sigma END) AS numeric), 2) AS max_chi_square_sigma,

                -- chi_square_log_sigma
                ROUND(CAST(MIN(CASE WHEN chi_square_log_sigma IS NOT NULL AND chi_square_log_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN chi_square_log_sigma END) AS numeric), 2) AS min_chi_square_log_sigma,
                ROUND(CAST(MAX(CASE WHEN chi_square_log_sigma IS NOT NULL AND chi_square_log_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN chi_square_log_sigma END) AS numeric), 2) AS max_chi_square_log_sigma,

                -- peak_map
                ROUND(CAST(MIN(CASE WHEN peak_map IS NOT NULL AND peak_map NOT IN ('NaN', 'Infinity', '-Infinity') THEN peak_map END) AS numeric), 2) AS min_peak_map,
                ROUND(CAST(MAX(CASE WHEN peak_map IS NOT NULL AND peak_map NOT IN ('NaN', 'Infinity', '-Infinity') THEN peak_map END) AS numeric), 2) AS max_peak_map,

                -- peak_map_sigma
                ROUND(CAST(MIN(CASE WHEN peak_map_sigma IS NOT NULL AND peak_map_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN peak_map_sigma END) AS numeric), 2) AS min_peak_map_sigma,
                ROUND(CAST(MAX(CASE WHEN peak_map_sigma IS NOT NULL AND peak_map_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN peak_map_sigma END) AS numeric), 2) AS max_peak_map_sigma,

                -- peak_map_log_sigma
                ROUND(CAST(MIN(CASE WHEN peak_map_log_sigma IS NOT NULL AND peak_map_log_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN peak_map_log_sigma END) AS numeric), 2) AS min_peak_map_log_sigma,
                ROUND(CAST(MAX(CASE WHEN peak_map_log_sigma IS NOT NULL AND peak_map_log_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN peak_map_log_sigma END) AS numeric), 2) AS max_peak_map_log_sigma,

                -- gaussian_map
                ROUND(CAST(MIN(CASE WHEN gaussian_map IS NOT NULL AND gaussian_map NOT IN ('NaN', 'Infinity', '-Infinity') THEN gaussian_map END) AS numeric), 2) AS min_gaussian_map,
                ROUND(CAST(MAX(CASE WHEN gaussian_map IS NOT NULL AND gaussian_map NOT IN ('NaN', 'Infinity', '-Infinity') THEN gaussian_map END) AS numeric), 2) AS max_gaussian_map,

                -- gaussian_map_sigma
                ROUND(CAST(MIN(CASE WHEN gaussian_map_sigma IS NOT NULL AND gaussian_map_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN gaussian_map_sigma END) AS numeric), 2) AS min_gaussian_map_sigma,
                ROUND(CAST(MAX(CASE WHEN gaussian_map_sigma IS NOT NULL AND gaussian_map_sigma NOT IN ('NaN', 'Infinity', '-Infinity') THEN gaussian_map_sigma END) AS numeric), 2) AS max_gaussian_map_sigma,

                -- std_map
                ROUND(CAST(MIN(CASE WHEN std_map IS NOT NULL AND std_map NOT IN ('NaN', 'Infinity', '-Infinity') THEN std_map END) AS numeric), 2) AS min_std_map,
                ROUND(CAST(MAX(CASE WHEN std_map IS NOT NULL AND std_map NOT IN ('NaN', 'Infinity', '-Infinity') THEN std_map END) AS numeric), 2) AS max_std_map,

                -- bright_sep_arcmin
                ROUND(CAST(MIN(CASE WHEN bright_sep_arcmin IS NOT NULL AND bright_sep_arcmin NOT IN ('NaN', 'Infinity', '-Infinity') THEN bright_sep_arcmin END) AS numeric), 2) AS min_bright_sep_arcmin,
                ROUND(CAST(MAX(CASE WHEN bright_sep_arcmin IS NOT NULL AND bright_sep_arcmin NOT IN ('NaN', 'Infinity', '-Infinity') THEN bright_sep_arcmin END) AS numeric), 2) AS max_bright_sep_arcmin,

                -- beam_sep_deg
                ROUND(CAST(MIN(CASE WHEN beam_sep_deg IS NOT NULL AND beam_sep_deg NOT IN ('NaN', 'Infinity', '-Infinity') THEN beam_sep_deg END) AS numeric), 2) AS min_beam_sep_deg,
                ROUND(CAST(MAX(CASE WHEN beam_sep_deg IS NOT NULL AND beam_sep_deg NOT IN ('NaN', 'Infinity', '-Infinity') THEN beam_sep_deg END) AS numeric), 2) AS max_beam_sep_deg,

                -- deep_int_flux
                ROUND(CAST(MIN(CASE WHEN deep_int_flux IS NOT NULL AND deep_int_flux NOT IN ('NaN', 'Infinity', '-Infinity') THEN deep_int_flux END) AS numeric), 2) AS min_deep_int_flux,
                ROUND(CAST(MAX(CASE WHEN deep_int_flux IS NOT NULL AND deep_int_flux NOT IN ('NaN', 'Infinity', '-Infinity') THEN deep_int_flux END) AS numeric), 2) AS max_deep_int_flux,

                -- deep_peak_flux
                ROUND(CAST(MIN(CASE WHEN deep_peak_flux IS NOT NULL AND deep_peak_flux NOT IN ('NaN', 'Infinity', '-Infinity') THEN deep_peak_flux END) AS numeric), 2) AS min_deep_peak_flux,
                ROUND(CAST(MAX(CASE WHEN deep_peak_flux IS NOT NULL AND deep_peak_flux NOT IN ('NaN', 'Infinity', '-Infinity') THEN deep_peak_flux END) AS numeric), 2) AS max_deep_peak_flux,

                -- deep_sep_arcsec
                ROUND(CAST(MIN(CASE WHEN deep_sep_arcsec IS NOT NULL AND deep_sep_arcsec NOT IN ('NaN', 'Infinity', '-Infinity') THEN deep_sep_arcsec END) AS numeric), 2) AS min_deep_sep_arcsec,
                ROUND(CAST(MAX(CASE WHEN deep_sep_arcsec IS NOT NULL AND deep_sep_arcsec NOT IN ('NaN', 'Infinity', '-Infinity') THEN deep_sep_arcsec END) AS numeric), 2) AS max_deep_sep_arcsec,

                -- md_deep
                ROUND(CAST(MIN(CASE WHEN md_deep IS NOT NULL AND md_deep NOT IN ('NaN', 'Infinity', '-Infinity') THEN md_deep END) AS numeric), 2) AS min_md_deep,
                ROUND(CAST(MAX(CASE WHEN md_deep IS NOT NULL AND md_deep NOT IN ('NaN', 'Infinity', '-Infinity') THEN md_deep END) AS numeric), 2) AS max_md_deep

            FROM candidate_app_candidate;
            """,
            """
            DROP MATERIALIZED VIEW candidate_min_max_stats;
            """,
        ),
        # Create a function that will refresh the materialised view when triggered
        migrations.RunSQL(
            """
            CREATE FUNCTION refresh_candidate_min_max_stats() RETURNS trigger
            AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW candidate_min_max_stats;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
            """,
            """
            DROP FUNCTION refresh_candidate_min_max_stats;
            """,
        ),
        # Create the trigger to run the refresh function on every insert, update, or delete from the candidate table
        migrations.RunSQL(
            """
            CREATE TRIGGER refresh_candidate_min_max_stats_trigger
            AFTER INSERT OR UPDATE OR DELETE ON candidate_app_candidate
            FOR EACH STATEMENT EXECUTE FUNCTION refresh_candidate_min_max_stats();
            """,
            """
            DROP TRIGGER refresh_candidate_min_max_stats_trigger;
            """,
        ),
        migrations.CreateModel(
            name="CandidateMinMaxStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("min_chi_square", models.FloatField(blank=True, null=True)),
                ("max_chi_square", models.FloatField(blank=True, null=True)),
                ("min_chi_square_sigma", models.FloatField(blank=True, null=True)),
                ("max_chi_square_sigma", models.FloatField(blank=True, null=True)),
                ("min_chi_square_log_sigma", models.FloatField(blank=True, null=True)),
                ("max_chi_square_log_sigma", models.FloatField(blank=True, null=True)),
                ("min_peak_map", models.FloatField(blank=True, null=True)),
                ("max_peak_map", models.FloatField(blank=True, null=True)),
                ("min_peak_map_sigma", models.FloatField(blank=True, null=True)),
                ("max_peak_map_sigma", models.FloatField(blank=True, null=True)),
                ("min_peak_map_log_sigma", models.FloatField(blank=True, null=True)),
                ("max_peak_map_log_sigma", models.FloatField(blank=True, null=True)),
                ("min_gaussian_map", models.FloatField(blank=True, null=True)),
                ("max_gaussian_map", models.FloatField(blank=True, null=True)),
                ("min_gaussian_map_sigma", models.FloatField(blank=True, null=True)),
                ("max_gaussian_map_sigma", models.FloatField(blank=True, null=True)),
                ("min_std_map", models.FloatField(blank=True, null=True)),
                ("max_std_map", models.FloatField(blank=True, null=True)),
                ("min_bright_sep_arcmin", models.FloatField(blank=True, null=True)),
                ("max_bright_sep_arcmin", models.FloatField(blank=True, null=True)),
                ("min_beam_sep_deg", models.FloatField(blank=True, null=True)),
                ("max_beam_sep_deg", models.FloatField(blank=True, null=True)),
                ("min_deep_int_flux", models.FloatField(blank=True, null=True)),
                ("max_deep_int_flux", models.FloatField(blank=True, null=True)),
                ("min_deep_peak_flux", models.FloatField(blank=True, null=True)),
                ("max_deep_peak_flux", models.FloatField(blank=True, null=True)),
                ("min_deep_sep_arcsec", models.FloatField(blank=True, null=True)),
                ("max_deep_sep_arcsec", models.FloatField(blank=True, null=True)),
                ("min_md_deep", models.FloatField(blank=True, null=True)),
                ("max_md_deep", models.FloatField(blank=True, null=True)),
            ],
            options={
                "db_table": "candidate_min_max_stats",
                "managed": False,
            },
        ),
    ]
