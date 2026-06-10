from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Auctions, Bid
from .forms import BidForm, CommentForm

User = get_user_model()

class AuctionArchitectureTestCase(TestCase):
    
    def setUp(self):
        """ Настройка окружения перед каждым тестом """
        # Создаем тестовых пользователей
        self.owner = User.objects.create_user(username="owner", password="password123")
        self.bidder1 = User.objects.create_user(username="bidder1", password="password123")
        self.bidder2 = User.objects.create_user(username="bidder2", password="password123")
        
        # Создаем тестовый аукцион (базовая цена $100.00)
        self.auction = Auctions.objects.create(
            name="Ретро Автомобиль",
            description="Прекрасный коллекционный лот",
            start_price=100.00,
            owner=self.owner,
            end_time=timezone.now() + timedelta(days=1)
        )

    def test_bid_form_with_valid_amount(self):
        """ Тест: Корректная ставка должна успешно проходить валидацию """
        form_data = {'amount': 150.00}
        form = BidForm(data=form_data, auction=self.auction)
        
        self.assertTrue(form.is_valid())

    def test_bid_form_below_start_price(self):
        """ Тест: Ставка ниже начальной цены лота должна вызывать ошибку """
        form_data = {'amount': 50.00}  # Начальная цена 100, ставим 50
        form = BidForm(data=form_data, auction=self.auction)
        
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        self.assertEqual(form.errors['amount'][0], "Ставка має бути не меншою за початкову ціну.")

    def test_bid_form_below_highest_bid(self):
        """ Тест: Ставка ниже или равная текущему максимуму должна блокироваться """
        # Имитируем, что bidder1 уже поставил $120.00
        Bid.objects.create(auction=self.auction, user=self.bidder1, amount=120.00)
        
        # Передаем форму от bidder2, который пытается поставить $115.00
        form_data = {'amount': 115.00}
        form = BidForm(data=form_data, auction=self.auction)
        
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        self.assertEqual(form.errors['amount'][0], "Ставка має бути більшою за поточную найвищу ($120.00).")

    def test_comment_form_blank_text(self):
        """ Тест: Пустой комментарий или состоящий из пробелов не должен сохраняться """
        form_data = {'text': '      '}
        form = CommentForm(data=form_data)
        
        self.assertFalse(form.is_valid())
        self.assertIn('text', form.errors)
    
    def test_automatic_auction_closure_and_winner(self):
        """ Тест: Аукцион с истекшим временем должен автоматически закрываться, 
        а победителем должен становиться пользователь с максимальной ставкой """
        
        # Импортируем функцию закрытия прямо внутри теста
        from .views import close_expired_auctions

        # 1. Делаем две разные ставки от разных пользователей
        Bid.objects.create(auction=self.auction, user=self.bidder1, amount=120.00)
        Bid.objects.create(auction=self.auction, user=self.bidder2, amount=150.00) # Это максимальная ставка

        # 2. Искусственно переносим время завершения аукциона в прошлое (как будто время истекло)
        self.auction.end_time = timezone.now() - timedelta(hours=2)
        self.auction.save()

        # 3. Вызываем функцию проверки и закрытия просроченных аукционов
        close_expired_auctions()

        # 4. Перезагружаем объект аукциона из базы данных, чтобы увидеть изменения
        self.auction.refresh_from_db()

        # 5. Проверяем утверждения (Asserts)
        self.assertFalse(self.auction.active)  # Статус должен стать Неактивным (False)
        self.assertEqual(self.auction.winner, self.bidder2)  # Победителем должен стать bidder2 ($150)