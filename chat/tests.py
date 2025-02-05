from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Message, Media
import uuid


# Create your tests here.

User = get_user_model()

class MessageViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('message-list')

    def test_post_message(self):
        data = {
            'iv': 'test_iv',
            'key': 'test_key',
            'file': 'test_file',
            'data': 'test_data'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.get().sender, self.user)


class MediaUploadViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('media-upload')

    def test_post_media(self):
        with open('testfile.txt', 'w') as f:
            f.write('test content')
        with open('testfile.txt', 'rb') as f:
            data = {
                'file': f,
                'metadata': {'recipients': [self.user.id]}
            }
            response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(Media.objects.get().access_ids.count(), 1)