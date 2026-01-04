from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Conversation, FriendRequest, Message, Post
from .templatetags.social_extras import liked_by


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


class PluginSmokeTests(TestCase):
    """Lightweight checks that the key views and HTMX snippets work together."""

    def setUp(self):
        self.User = get_user_model()
        self.alice = self.User.objects.create_user(username='alice', password='pass123')
        self.bob = self.User.objects.create_user(username='bob', password='pass123')
        self.client.force_login(self.alice)

    def _befriend(self, sender, receiver):
        FriendRequest.objects.create(
            sender=sender,
            receiver=receiver,
            status=FriendRequest.ACCEPTED,
        )

    def test_feed_renders_with_like_button(self):
        """Make sure feed loads and the like snippet honors is_liked."""

        post = Post.objects.create(author=self.bob, body='Test post', visibility='public')
        url = reverse('feed')
        response = self.client.get(url)
        self.assertContains(response, post.body)
        # Simulate HTMX like toggle and ensure the button reflects the liked state
        like_url = reverse('toggle_like', args=[post.pk])
        like_response = self.client.post(
            like_url,
            HTTP_HX_REQUEST='true',
        )
        self.assertContains(like_response, 'btn-primary')

    def test_like_button_template_compiles(self):
        """The like button partial should render without template syntax errors."""

        post = Post.objects.create(author=self.bob, body='Hello', visibility='public')
        template = self.client.get(reverse('feed')).templates[0].engine.get_template(
            'social/components/like_button.html'
        )
        rendered = template.render({'post': post, 'user': self.alice})
        self.assertIn('Like', rendered)

    def test_profile_update_accepts_post(self):
        """Profile updates should respond with a redirect instead of 405 errors."""

        self._befriend(self.alice, self.bob)
        url = reverse('update_profile')
        response = self.client.post(
            url,
            {
                'bio': 'Hello there',
                'location': 'Wonderland',
                'website': 'https://example.com',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.profile.bio, 'Hello there')

    def test_chat_list_and_thread_load(self):
        """Conversations and chat list should render without template errors."""

        self._befriend(self.alice, self.bob)
        convo, _ = Conversation.between(self.alice, self.bob)
        Message.objects.create(conversation=convo, sender=self.alice, body='Ping')

        list_response = self.client.get(reverse('chat_list'))
        self.assertContains(list_response, 'Messenger')

        thread_response = self.client.get(reverse('chat_thread', args=[self.bob.username]))
        self.assertContains(thread_response, 'Ping')

    def test_liked_by_honors_prefetched_flag(self):
        """The helper should trust an annotated is_liked flag to keep templates simple."""

        post = Post.objects.create(author=self.bob, body='Flag check', visibility='public')
        post.is_liked = True

        self.assertTrue(liked_by(post, self.alice))

        post.is_liked = False
        self.assertFalse(liked_by(post, self.alice))
