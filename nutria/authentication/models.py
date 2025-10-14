from django.db import models

class GoogleUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    photo_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
