from django import forms
from django.core.exceptions import ValidationError
from .models import Auctions, Bid, Comments

class AuctionForm(forms.ModelForm):
    """ Форма для створення нового аукціонного лоту """
    class Meta:
        model = Auctions
        fields = ['name', 'description', 'start_price', 'image', 'end_time']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'new-auction_input'}),
            'description': forms.Textarea(attrs={'class': 'new-auction_textarea', 'rows': 8}),
            'start_price': forms.NumberInput(attrs={'class': 'new-auction_input', 'step': '0.01', 'min': '0'}),
            'image': forms.FileInput(attrs={'class': 'new-auction_file'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'new-auction_input', 'type': 'datetime-local'}),
        }


class BidForm(forms.ModelForm):
    """ Форма для розміщення ставок із розширеною валідацією """
    class Meta:
        model = Bid
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'auction-page_input', 'step': '0.01', 'placeholder': 'Ваша ставка...'}),
        }

    def __init__(self, *args, **kwargs):
        # Отримуємо об'єкт аукціону, який передається з view
        self.auction = kwargs.pop('auction', None)
        super().__init__(*args, **kwargs)

    # РОЗШИРЕНА ВАЛІДАЦІЯ КОНКРЕТНОГО ПОЛЯ
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount is None:
            raise ValidationError("Некоректна сума ставки.")

        # 1. Перевірка: ставка не повинна бути меншою за початкову ціну лоту
        if amount < self.auction.start_price:
            raise ValidationError("Ставка має бути не меншою за початкову ціну.")

        # 2. Перевірка: ставка повинна бути строго більшою за поточну найвищу ставку
        highest_bid = self.auction.bids.order_by("-amount").first()
        if highest_bid and amount <= highest_bid.amount:
            raise ValidationError(f"Ставка має бути більшою за поточную найвищу (${highest_bid.amount}).")

        return amount


class CommentForm(forms.ModelForm):
    """ Форма для додавання коментарів """
    class Meta:
        model = Comments
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'auction-page_textarea', 'rows': 3, 'placeholder': 'Ваш коментар...'}),
        }

    # РОЗШИРЕНА ВАЛІДАЦІЯ ПОЛЯ
    def clean_text(self):
        text = self.cleaned_data.get('text')
        if not text or not text.strip():
            raise ValidationError("Коментар не може бути порожнім.")
        return text