from rest_framework.views import APIView
from rest_framework.response import Response
from .models import ChatUser

class UserListAPIView(APIView):
    def get(self, request):
        users = ChatUser.objects.values_list('name', flat=True)
        return Response(list(users))
