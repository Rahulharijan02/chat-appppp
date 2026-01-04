from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Conversation, FriendRequest, Message


class ChatFlowTests(TestCase):
    """Cover simple chat flows with two demo users."""

    def setUp(self):
        self.User = get_user_model()
        self.alice = self.User.objects.create_user(username='alice', password='pass123')
        self.bob = self.User.objects.create_user(username='bob', password='pass123')
        FriendRequest.objects.create(
            sender=self.alice,
            receiver=self.bob,
            status=FriendRequest.ACCEPTED,
        )

    def test_conversation_between_friends_created_once(self):
        first, created = Conversation.between(self.alice, self.bob)
        self.assertTrue(created)
        again, created_again = Conversation.between(self.alice, self.bob)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, again.pk)
        self.assertSetEqual(
            set(first.participants.values_list('pk', flat=True)),
            {self.alice.pk, self.bob.pk},
        )

    def test_message_post_creates_chat_bubble(self):
        self.client.force_login(self.alice)
        url = reverse('chat_thread', args=[self.bob.username])
        response = self.client.post(url, {'body': 'Hello Bob!'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Message.objects.filter(body='Hello Bob!', sender=self.alice).exists())
        self.assertContains(response, 'Hello Bob!')

    def test_non_friend_cannot_open_thread(self):
        charlie = self.User.objects.create_user(username='charlie', password='pass123')
        self.client.force_login(self.alice)
        url = reverse('chat_thread', args=[charlie.username])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile', args=[charlie.username]))
