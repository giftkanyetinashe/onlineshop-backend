from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUserOrReadOnly(BasePermission):
    """
    Allows read-only access to everyone, but write access only to admin users.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True  # Allow GET, HEAD, OPTIONS requests for everyone
        return request.user and request.user.is_staff  # Only staff can POST, PUT, DELETE
