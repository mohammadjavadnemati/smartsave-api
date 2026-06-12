from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    فقط صاحب آبجکت می‌تونه بهش دسترسی داشته باشه
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user