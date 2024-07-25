from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("candidate_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ATNFPulsar",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=32, unique=True, verbose_name="Pulsar Name")),
                ("ra_str", models.CharField()),
                ("dec_str", models.CharField()),
                ("decj", models.FloatField(verbose_name="Declination epoch (J2000, deg)")),
                ("raj", models.FloatField(verbose_name="Right Ascension epoch (J2000, deg)")),
                ("DM", models.FloatField(verbose_name="Dispersion Measure (cm^-3 pc)", blank=True, null=True)),
                ("p0", models.FloatField(verbose_name="Barycentric period of the pulsar (s)", blank=True, null=True)),
                ("s400", models.FloatField(verbose_name="Mean flux density at 400 MHz (mJy)", blank=True, null=True)),
            ],
        ),
    ]
