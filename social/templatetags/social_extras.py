"""Custom template helpers for friendly social UI rendering."""

from django import template


register = template.Library()


def _liked_state(post, user):
    """Return True when the given user liked the post.

    Falls back to a lightweight database check if a pre-computed
    ``is_liked`` flag is not already present on the post instance.
    """

    if not user or not getattr(user, "is_authenticated", False):
        return False
    if hasattr(post, "is_liked"):
        return bool(post.is_liked)
    likes = getattr(post, "likes", None)
    if likes is not None:
        return likes.filter(user=user).exists()
    return False


@register.filter
def liked_by(post, user):
    """Legacy filter to check whether ``user`` liked ``post``."""

    return _liked_state(post, user)


@register.simple_tag
def user_liked(post, user):
    """Template tag variant used by HTMX like button partials."""

    return _liked_state(post, user)
