"""User API input and output serializers."""

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    id_user = serializers.IntegerField(source="id", read_only=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = [
            "id_user",
            "role",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
            "password",
        ]

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()
        users = User.objects.filter(email__iexact=email)
        if self.instance is not None:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs):
        attrs = super().validate(attrs)
        password = attrs.get("password")
        if password is None:
            return attrs

        password_user = self.instance or User()
        for field in ("email", "first_name", "last_name"):
            if field in attrs:
                setattr(password_user, field, attrs[field])

        try:
            password_validation.validate_password(password, password_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)
        if password is not None:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields["password"].required = False
        return fields
