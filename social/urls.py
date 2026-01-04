from django.urls import path

from .views import (
    FeedView,
    ProfileView,
    SignUpView,
    add_comment,
    create_post,
    respond_friend_request,
    send_friend_request,
    toggle_like,
    update_profile,
)

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('feed/', FeedView.as_view(), name='feed'),
    path('posts/<int:pk>/like/', toggle_like, name='toggle_like'),
    path('posts/<int:pk>/comment/', add_comment, name='add_comment'),
    path('posts/create/', create_post, name='create_post'),
    path('profile/<str:username>/', ProfileView.as_view(), name='profile'),
    path('profile/update/', update_profile, name='update_profile'),
    path('profile/<str:username>/friend/', send_friend_request, name='send_friend_request'),
    path('friend-request/<int:pk>/<str:decision>/', respond_friend_request, name='respond_friend_request'),
]
