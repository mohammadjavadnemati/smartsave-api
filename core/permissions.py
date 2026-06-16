from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Only the owner of the object can access it"""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user