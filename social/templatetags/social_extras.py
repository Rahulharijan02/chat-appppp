"""Custom template helpers for friendly social UI rendering."""

from django import template


register = template.Library()


@register.filter
def liked_by(post, user):
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
