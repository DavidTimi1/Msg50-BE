from rest_framework import serializers
from .models import Feedback

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'

    
    def to_internal_value(self, data):
        # Filter add unknown fields to extra data
        known_fields = set(self.fields)
        extra_data = {key: data[key] for key in data if key not in known_fields}
        updated_data = {**data, 'extraData': extra_data }
        return super().to_internal_value(updated_data)