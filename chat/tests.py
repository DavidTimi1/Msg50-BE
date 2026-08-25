import json
import os
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Media, Message

User = get_user_model()


class E2EETests(APITestCase):
    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(username='alice', password='password123', email='alice@example.com')
        self.user2 = User.objects.create_user(username='bob', password='password123', email='bob@example.com')
        
        self.client1 = APIClient()
        self.client2 = APIClient()
        
        # Authenticate using force_authenticate (simulating cookie authentication)
        self.client1.force_authenticate(user=self.user1)
        self.client2.force_authenticate(user=self.user2)

    def test_user_profile_view_authenticated(self):
        """Authenticated users should see full profile fields (email, profile_data)."""
        url = reverse('user-details', kwargs={'username': 'alice'})
        response = self.client2.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email', response.data)
        self.assertIn('profile_data', response.data)
        self.assertEqual(response.data['email'], 'alice@example.com')

    def test_user_profile_view_unauthenticated(self):
        """Unauthenticated requests should return only public fields (no email or profile_data)."""
        url = reverse('user-details', kwargs={'username': 'alice'})
        anon_client = APIClient()
        response = anon_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('email', response.data)
        self.assertNotIn('profile_data', response.data)
        self.assertEqual(response.data['username'], 'alice')

    def test_user_search_authenticated(self):
        """Authenticated search excludes current user, shows full details of matching users."""
        url = reverse('user-search')
        response = self.client1.get(url, {'q': 'bob'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'bob')
        self.assertIn('email', response.data[0])

    def test_user_search_unauthenticated(self):
        """Unauthenticated search is allowed but returns public fields only."""
        url = reverse('user-search')
        anon_client = APIClient()
        response = anon_client.get(url, {'q': 'bob'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'bob')
        self.assertNotIn('email', response.data[0])

    def test_user_public_key_get_and_post(self):
        """Users can post their E2EE public key and fetch other users' public keys."""
        # Set public key
        post_url = reverse('user-public-key')
        pubkey_data = {'publicKey': 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA'}
        response = self.client1.post(post_url, pubkey_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify it saved
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.public_key, pubkey_data['publicKey'])

        # Get public key
        get_url = reverse('user-public-key')
        response = self.client2.get(get_url, {'username': ['alice']})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(str(self.user1.id), response.data)
        self.assertEqual(response.data[str(self.user1.id)], pubkey_data['publicKey'])

    def test_user_settings_get_and_post(self):
        """Users can manage their custom JSON E2EE profile preferences."""
        url = reverse('user-settings')
        
        # Fetch empty settings
        response = self.client1.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['profile_data'], {})

        # Update settings
        settings_payload = {'profile_data': {'theme': 'dark', 'notifications': False}}
        response = self.client1.post(url, settings_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['profile_data'], settings_payload['profile_data'])
        
        # Verify db persistence
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.profile_data['theme'], 'dark')


class MediaUploadViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse('media-upload')

    def test_post_media(self):
        """Users can upload encrypted binary files with metadata."""
        filename = 'testfile.txt'
        with open(filename, 'w') as f:
            f.write('encrypted media content')
            
        try:
            with open(filename, 'rb') as f:
                data = {
                    'file': f,
                    'metadata': json.dumps({'recipients': [self.user.username]})
                }
                response = self.client.post(self.url, data, format='multipart')
                
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('src', response.data)
            self.assertEqual(Media.objects.count(), 1)
            self.assertEqual(Media.objects.get().access_ids.count(), 1)
        finally:
            if os.path.exists(filename):
                os.remove(filename)