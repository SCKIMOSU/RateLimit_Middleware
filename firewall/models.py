from django.db import models

class AllowedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.ip_address} - {self.description}"


class BlockedIPLog(models.Model):
    ip_address = models.GenericIPAddressField()
    accessed_path = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

