from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Media

# Create your tests here.

User = get_user_model()


class MediaUploadViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('media-upload')

    def test_post_media(self):
        import json
        import os
        
        with open('testfile.txt', 'w') as f:
            f.write('test content')
        try:
            with open('testfile.txt', 'rb') as f:
                data = {
                    'file': f,
                    'metadata': json.dumps({'recipients': [self.user.username]})
                }
                response = self.client.post(self.url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(Media.objects.count(), 1)
            self.assertEqual(Media.objects.get().access_ids.count(), 1)
        finally:
            if os.path.exists('testfile.txt'):
                os.remove('testfile.txt')