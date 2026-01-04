from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from .forms import CommentForm, MessageForm, PostForm, ProfileForm, SignUpForm
from .models import Conversation, FriendRequest, Like, Message, Post, Profile


def get_friend_ids(user):
    """Return a set of user IDs the given user is friends with."""

    sent = FriendRequest.objects.filter(
        sender=user, status=FriendRequest.ACCEPTED
    ).values_list('receiver', flat=True)
    received = FriendRequest.objects.filter(
        receiver=user, status=FriendRequest.ACCEPTED
    ).values_list('sender', flat=True)
    return set(sent).union(received)


def is_friend(user, other_user):
    """Check if two users have an accepted friendship connection."""

    return other_user.id in get_friend_ids(user)


def annotate_like_state(queryset, user):
    """Attach an is_liked flag for the given user onto each post."""

    like_exists = Like.objects.filter(user=user, post=OuterRef('pk'))
    return queryset.annotate(is_liked=Exists(like_exists))


class SignUpView(View):
    template_name = 'registration/signup.html'

    def get(self, request):
        return render(request, self.template_name, {'form': SignUpForm()})

    def post(self, request):
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome to Developer Portfolio Network!')
            return redirect('feed')
        return render(request, self.template_name, {'form': form})


class FeedView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'social/feed.html'
    context_object_name = 'posts'

    def get_queryset(self):
        friends = get_friend_ids(self.request.user)
        posts = Post.objects.filter(
            Q(visibility='public') | Q(visibility='friends', author_id__in=friends)
        ).select_related('author').prefetch_related('comments__author', 'likes')
        return annotate_like_state(posts, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post_form'] = PostForm()
        context['comment_form'] = CommentForm()
        context['friend_requests'] = FriendRequest.objects.filter(
            receiver=self.request.user, status=FriendRequest.PENDING
        )
        return context


@login_required
def create_post(request):
    if request.method != 'POST':
        return HttpResponseForbidden()
    form = PostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, 'Post shared successfully!')
    return redirect('feed')


@login_required
def toggle_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    post.is_liked = post.likes.filter(user=request.user).exists()
    if request.htmx:
        return render(
            request,
            'social/components/like_button.html',
            {'post': post, 'user': request.user},
        )
    return redirect('feed')


@login_required
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method != 'POST':
        return HttpResponseForbidden()
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    if request.htmx:
        return render(request, 'social/components/comments.html', {'post': post})
    return redirect('feed')


class ProfileView(LoginRequiredMixin, DetailView):
    model = Profile
    template_name = 'social/profile.html'
    slug_field = 'user__username'
    slug_url_kwarg = 'username'

    def get_object(self):
        return get_object_or_404(Profile, user__username=self.kwargs['username'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = Post.objects.filter(author=self.object.user)
        context['posts'] = annotate_like_state(posts, self.request.user)
        context['profile_form'] = ProfileForm(instance=self.object)
        friend_ids = get_friend_ids(self.request.user)
        context['is_friend'] = self.object.user.id in friend_ids
        context['has_pending_request'] = FriendRequest.objects.filter(
            sender=self.request.user,
            receiver=self.object.user,
            status=FriendRequest.PENDING,
        ).exists()
        context['incoming_request'] = FriendRequest.objects.filter(
            sender=self.object.user,
            receiver=self.request.user,
            status=FriendRequest.PENDING,
        ).exists()
        return context


@login_required
def update_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
    return redirect('profile', username=request.user.username)


@login_required
def send_friend_request(request, username):
    receiver = get_object_or_404(Profile, user__username=username).user
    if receiver == request.user:
        messages.error(request, 'You cannot befriend yourself.')
        return redirect('profile', username=username)

    # Avoid noisy duplicates by telling users when they are already connected
    if is_friend(request.user, receiver):
        messages.info(request, 'You are already friends!')
        return redirect('profile', username=username)

    pending_request, created = FriendRequest.objects.get_or_create(
        sender=request.user, receiver=receiver
    )
    if created:
        messages.info(request, 'Friend request sent.')
    elif pending_request.status == FriendRequest.PENDING:
        messages.info(request, 'Friend request already sent.')
    else:
        messages.info(request, 'Previous request handled; feel free to try again later.')
    return redirect('profile', username=username)


@login_required
def respond_friend_request(request, pk, decision):
    friend_request = get_object_or_404(FriendRequest, pk=pk, receiver=request.user)
    if decision == 'accept':
        friend_request.accept()
        messages.success(request, 'Friend request accepted.')
    else:
        friend_request.decline()
        messages.info(request, 'Friend request declined.')
    return redirect('feed')


class ChatListView(LoginRequiredMixin, ListView):
    model = Conversation
    template_name = 'social/chat_list.html'
    context_object_name = 'conversations'

    def get_queryset(self):
        return (
            Conversation.objects.filter(participants=self.request.user)
            .prefetch_related('participants', 'messages__sender')
            .order_by('-created_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        friends = get_friend_ids(self.request.user)
        context['friends'] = get_user_model().objects.filter(id__in=friends)
        conversations = list(context['conversations'])
        for convo in conversations:
            convo.other = convo.participants.exclude(pk=self.request.user.pk).first()
        context['conversations'] = conversations
        return context


class ChatThreadView(LoginRequiredMixin, View):
    template_name = 'social/chat_thread.html'

    def get_target_user(self, username):
        return get_object_or_404(get_user_model(), username=username)

    def _validate_chat_partner(self, request, username):
        """Make sure a chat can start and return the other user or a redirect."""

        target_user = self.get_target_user(username)
        if target_user == request.user:
            messages.error(request, 'Messaging yourself is not supported.')
            return None, redirect('chat_list')
        if not is_friend(request.user, target_user):
            messages.error(request, 'You can only chat with accepted connections.')
            return None, redirect('profile', username=target_user.username)
        return target_user, None

    def get(self, request, username):
        target_user, redirect_response = self._validate_chat_partner(request, username)
        if redirect_response:
            return redirect_response

        conversation, _ = Conversation.between(request.user, target_user)
        messages_qs = conversation.messages.select_related('sender')
        return render(
            request,
            self.template_name,
            {
                'conversation': conversation,
                'messages': messages_qs,
                'form': MessageForm(),
                'other_user': target_user,
            },
        )

    def post(self, request, username):
        target_user, redirect_response = self._validate_chat_partner(request, username)
        if redirect_response:
            return redirect_response

        conversation, _ = Conversation.between(request.user, target_user)
        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=form.cleaned_data['body'],
            )
            messages.success(request, 'Message sent.')
            return redirect('chat_thread', username=target_user.username)
        messages_qs = conversation.messages.select_related('sender')
        return render(
            request,
            self.template_name,
            {
                'conversation': conversation,
                'messages': messages_qs,
                'form': form,
                'other_user': target_user,
            },
        )
