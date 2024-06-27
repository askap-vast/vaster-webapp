from rest_framework import serializers
from . import models
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timezone
import uuid


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
            date=datetime.now(timezone.utc),
        )

        project = models.Project.objects.get(id=validated_data["proj_id"])

        return models.Observation.objects.create(upload=upload, project=project, **validated_data)


class BeamSerializer(serializers.ModelSerializer):
    hash_id = serializers.UUIDField(required=False)
    obs_id = serializers.CharField(write_only=True)

    class Meta:
        model = models.Beam
        fields = "__all__"

    def create(self, validated_data):
        # Check if 'hash_id' is present; if not, generate a new UUID
        if "hash_id" not in validated_data:
            validated_data["hash_id"] = uuid.uuid4()

        obs_id = validated_data.pop("obs_id")
        observation = models.Observation.objects.get(id=obs_id)

        assert observation is not None, f"Failed to find observation {obs_id} in DB."

        # Create the Upload metadata
        upload = models.Upload.objects.create(
            user=self.context["user"],
            date=datetime.now(timezone.utc),
        )

        project = models.Project.objects.get(id=validated_data["proj_id"])

        return models.Beam.objects.create(observation=observation, project=project, upload=upload, **validated_data)


class CandidateSerializer(serializers.ModelSerializer):

    hash_id = serializers.UUIDField(required=False)

    class Meta:
        model = models.Candidate
        fields = "__all__"

    def create(self, validated_data):
        # Check if 'hash_id' is present; if not, generate a new UUID
        if "hash_id" not in validated_data:
            validated_data["hash_id"] = uuid.uuid4()

        obs_id = validated_data.get("obs_id")

        print(f"+++++++++++++++ serializer: OBS ID {obs_id} +++++++++++++++")
        obs = models.Observation.objects.get(id=obs_id)

        assert obs is not None, f"Failed to find observation {obs_id} in DB."

        beam_index = validated_data.get("beam_index")
        beam = models.Beam.objects.get(index=beam_index, observation=obs)

        print(f"+++++++++++++++ serializer: BEAM INDEX {beam_index} +++++++++++++++")

        assert beam is not None, f"Failed to find beam {beam_index} for {obs_id} in DB."

        # Create the Upload metadata
        upload = models.Upload.objects.create(
            user=self.context["user"],
            date=datetime.now(timezone.utc),
        )

        project = models.Project.objects.get(id=validated_data["proj_id"])

        return models.Candidate.objects.create(
            project=project,
            observation=obs,
            beam=beam,
            upload=upload,
            **validated_data,
        )
