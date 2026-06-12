from django.contrib.auth.models import AbstractUser
from django.db import models

from datetime import timedelta
from django.utils import timezone

from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    pass


class Auctions(models.Model):
    CATEGORY_CHOICES = [
        ('tech', 'Техніка та електроніка'),
        ('art', 'Мистецтво та антикваріат'),
        ('fashion', 'Одяг та стиль'),
        ('home', 'Дім та сад'),
        ('other', 'Інше'),
    ]
    name = models.CharField(max_length=64)
    description = models.TextField()
    start_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="auction_images/", blank=True, null=True)
    active = models.BooleanField(default=True)
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='other'
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="my_auctions", null=True, blank=True)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="won_auctions")
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}: {self.start_price} ({self.description})"
    
    def current_price(self):
        max_bid = self.bids.aggregate(models.Max("amount"))["amount__max"]
        return max_bid if max_bid else self.start_price

class Bid(models.Model):
    auction = models.ForeignKey(Auctions, on_delete=models.CASCADE, related_name="bids")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True) # дата/время создания ставки — автоматически заполняется при создании


class Rates(models.Model):
    auction = models.ForeignKey(Auctions, on_delete=models.CASCADE, related_name="amount")
    value = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rates")
    def __str__(self):
        return f"{self.auction.name}: {self.value} by {self.user.username}"
    

class Comments(models.Model):
    auction = models.ForeignKey(Auctions, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.user.username} on {self.auction.name}: {self.text}"


class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist")
    auction = models.ForeignKey(Auctions, on_delete=models.CASCADE, related_name="watchlisted_by")

    class Meta:
        unique_together = ("user", "auction")  # один аукціон не можна додати двічі

    def __str__(self):
        return f"{self.user.username} -> {self.auction.name}"
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    credits = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)

    def __str__(self):
        return f"Профиль пользователя {self.user.username}"

# Сигнал: автоматически создаем профиль с кредитами при создании пользователя
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            Profile.objects.create(user=instance)