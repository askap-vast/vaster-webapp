from rest_framework import serializers
from . import models


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Observation
        fields = "__all__"


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Candidate
        fields = "__all__"
