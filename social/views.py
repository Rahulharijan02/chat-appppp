from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from .forms import CommentForm, PostForm, ProfileForm, SignUpForm
from .models import FriendRequest, Like, Post, Profile


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
        friends = FriendRequest.objects.filter(
            status=FriendRequest.ACCEPTED, sender=self.request.user
        ).values_list('receiver', flat=True)
        return (
            Post.objects.filter(
                Q(visibility='public') | Q(visibility='friends', author_id__in=friends)
            )
            .select_related('author')
            .prefetch_related('comments__author', 'likes')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post_form'] = PostForm()
        context['comment_form'] = CommentForm()
        context['friend_requests'] = FriendRequest.objects.filter(receiver=self.request.user, status=FriendRequest.PENDING)
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
        context['posts'] = Post.objects.filter(author=self.object.user)
        context['profile_form'] = ProfileForm(instance=self.object)
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
    FriendRequest.objects.get_or_create(sender=request.user, receiver=receiver)
    messages.info(request, 'Friend request sent.')
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
