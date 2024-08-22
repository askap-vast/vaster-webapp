import uuid
from rest_framework import serializers

from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile

from . import models


def remove_leading_zero(coord_str: str):

    if coord_str.startswith("0"):
        return coord_str[1:]
    elif coord_str.startswith("-0"):
        return f"-{coord_str[2:]}"
    return coord_str


class ObservationSerializer(serializers.ModelSerializer):

    hash_id = serializers.UUIDField(required=False)

    class Meta:
        model = models.Observation
        fields = "__all__"

    def create(self, validated_data):
        # Check if 'hash_id' is present; if not, generate a new UUID
        if "hash_id" not in validated_data:
            validated_data["hash_id"] = uuid.uuid4()

        # Create the Upload metadata
        upload = models.Upload.objects.create(
            user=self.context["user"],
            date=timezone.now(),
        )

        project = models.Project.objects.get(id=validated_data["proj_id"])

        assert project is not None, f"Failed to find project {validated_data['proj_id']} DB."

        return models.Observation.objects.create(upload=upload, project=project, **validated_data)


BEAM_FILE_FIELDS = [
    "final_cand_csv",
    "std_fits",
    "chisquare_map1_png",
    "chisquare_map2_png",
    "chisquare_fits",
    "peak_map1_png",
    "peak_map2_png",
    "peak_fits",
]


class BeamSerializer(serializers.ModelSerializer):
    hash_id = serializers.UUIDField(required=False)
    obs_id = serializers.CharField(write_only=True)

    # total_file_count = serializers.IntegerField(write_only=True)
    # total_file_size_bytes = serializers.IntegerField(write_only=True)

    class Meta:
        model = models.Beam
        fields = "__all__"

    # def validate(self, data):
    #     """Trim the unnecessary leading zero from the coordinate string."""
    #     data["ra_str"] = remove_leading_zero(data.get("ra_str", ""))
    #     data["dec_str"] = remove_leading_zero(data.get("dec_str", ""))
    #     return data

    def create(self, validated_data):
        # Check if 'hash_id' is present; if not, generate a new UUID
        if "hash_id" not in validated_data:
            validated_data["hash_id"] = uuid.uuid4()

        proj = models.Project.objects.get(id=validated_data["proj_id"])

        assert proj is not None, f"Failed to find project {validated_data['proj_id']} DB."

        obs_id = validated_data.pop("obs_id")
        observation = models.Observation.objects.get(project=proj, id=obs_id)

        assert observation is not None, f"Failed to find observation {obs_id} in DB."

        # Make counts for uploaded files and file sizes.
        total_file_count = 0
        total_file_size_bytes = 0
        for file in BEAM_FILE_FIELDS:
            uploaded_file: InMemoryUploadedFile = validated_data.get(file)
            if uploaded_file is not None:
                total_file_count += 1
                total_file_size_bytes += uploaded_file.size
        validated_data["total_file_count"] = total_file_count
        validated_data["total_file_size_bytes"] = total_file_size_bytes

        print(
            f" ---- Number of files in beam: {total_file_count}. Number of bytes for beam files: {total_file_size_bytes} ---- "
        )

        # Create the Upload metadata
        upload = models.Upload.objects.create(
            user=self.context["user"],
            date=timezone.now(),
        )

        return models.Beam.objects.create(observation=observation, project=proj, upload=upload, **validated_data)


CANDIDATE_FILE_FIELDS = [
    "lightcurve_png",
    "slices_gif",
    "slices_fits",
    "deepcutout_png",
    "deepcutout_fits",
]


class CandidateSerializer(serializers.ModelSerializer):

    hash_id = serializers.UUIDField(required=False)

    class Meta:
        model = models.Candidate
        fields = "__all__"

    # Keep leading zero on coordinates
    # def validate(self, data):
    #     """Trim the unnecessary leading zero from the coordinate string."""
    #     data["ra_str"] = remove_leading_zero(data.get("ra_str", ""))
    #     data["dec_str"] = remove_leading_zero(data.get("dec_str", ""))
    #     return data

    def create(self, validated_data):
        # Check if 'hash_id' is present; if not, generate a new UUID
        if "hash_id" not in validated_data:
            validated_data["hash_id"] = uuid.uuid4()

        proj = models.Project.objects.get(id=validated_data["proj_id"])
        assert proj is not None, f"Failed to find project {validated_data['proj_id']} DB."

        obs_id = validated_data.get("obs_id")
        print(f"+++++++++++++++ candidate serializer: OBS ID {obs_id} +++++++++++++++")
        obs = models.Observation.objects.get(id=obs_id, project=proj)
        assert obs is not None, f"Failed to find observation {obs_id} in DB."

        beam_index = validated_data.get("beam_index")
        beam = models.Beam.objects.get(index=beam_index, observation=obs, project=proj)
        print(f"+++++++++++++++ candidate serializer: BEAM INDEX {beam_index} +++++++++++++++")
        assert beam is not None, f"Failed to find beam {beam_index} for {obs_id} in DB."
        # validated_data["cand_obj_id"] = f"{proj.id}_{obs.id}_{beam.index}_{validated_data['name']}"

        # Make counts for uploaded files and file sizes.
        total_file_count = 0
        total_file_size_bytes = 0
        for file in CANDIDATE_FILE_FIELDS:
            uploaded_file: InMemoryUploadedFile = validated_data.get(file)
            if uploaded_file is not None:
                total_file_count += 1
                total_file_size_bytes += uploaded_file.size
        validated_data["total_file_count"] = total_file_count
        validated_data["total_file_size_bytes"] = total_file_size_bytes

        # Create the Upload metadata
        upload = models.Upload.objects.create(
            user=self.context["user"],
            date=timezone.now(),
        )

        return models.Candidate.objects.create(
            project=proj,
            observation=obs,
            beam=beam,
            upload=upload,
            **validated_data,
        )
