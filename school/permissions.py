from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):

        print request.method
        print obj.artist.user
        print request.user
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS or request.user.is_staff:
            return True

        # on UPDATE
        if (request.method == "POST" or request.method == "PATCH" or request.method == "PUT"):
            if (request.data.get('application_complete') or
                    request.data.get('selected_for_interview') or
                    request.data.get('selected') or
                    request.data.get('wait_listed') or
                    request.data.get('application_complete') or
                    request.data.get('physical_content_received')):
                return False

        # Write permissions are only allowed to the owner of the snippet.
        return obj.artist.user == request.user
