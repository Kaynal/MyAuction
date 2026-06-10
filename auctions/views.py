# auctions/views.py
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import User, Auctions, Bid, Comments, Watchlist
from .forms import AuctionForm, BidForm, CommentForm  # Імпортуємо наші форми
from django.contrib import messages


def close_expired_auctions():
    """ Допоміжна функція для автоматичного закриття просрочених лотів """
    now = timezone.now()
    expired_auctions = Auctions.objects.filter(active=True, end_time__isnull=False, end_time__lte=now)
    for auction in expired_auctions:
        highest_bid = auction.bids.order_by("-amount").first()
        if highest_bid:
            auction.winner = highest_bid.user
        auction.active = False
        auction.save()


def index(request):
    close_expired_auctions()
    return render(request, "auctions/index.html", {
        "auctions": Auctions.objects.all()
    })


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]

        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


@login_required
def new_auction(request):
    if request.method == "POST":
        # Передаємо в форму сирі дані та файли
        form = AuctionForm(request.POST, request.FILES)
        if form.is_valid():
            # commit=False створює об'єкт моделі, але не зберігає його в БД одразу
            auction = form.save(commit=False)
            auction.owner = request.user  # Додаємо власника лоту вручну
            auction.save()                # Тепер зберігаємо в базу даних
            messages.success(request, "Аукціон успішно створено!")
            return redirect("index")
    else:
        form = AuctionForm()

    return render(request, "auctions/new_auction.html", {"form": form})


@login_required
def auction(request, auction_id):
    close_expired_auctions()
    
    auction = get_object_or_404(Auctions, pk=auction_id)
    bids = auction.bids.all().order_by("-amount")
    highest_bid = bids.first().amount if bids.exists() else None
    comments = auction.comments.all().order_by("-created_at")
    in_watchlist = Watchlist.objects.filter(user=request.user, auction=auction).exists() if request.user.is_authenticated else False

    # Створюємо порожні форми для відображення на сторінці (GET-запит)
    bid_form = BidForm(auction=auction)
    comment_form = CommentForm()

    if request.method == "POST":
        # Перевіряємо, яка саме з двох форм на сторінці була відправлена
        if "text" in request.POST:  # Відправлено форму коментаря (поле моделі 'text')
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.auction = auction
                comment.user = request.user
                comment.save()
                messages.success(request, "Коментар додано!")
                return redirect("auction", auction_id=auction.id)
            else:
                # Якщо валідація форми не пройшла, збираємо помилки
                for error in comment_form.errors.values():
                    messages.error(request, error.as_text())

        elif "amount" in request.POST:  # Відправлено форму ставки (поле моделі 'amount')
            bid_form = BidForm(request.POST, auction=auction)
            if bid_form.is_valid():
                bid = bid_form.save(commit=False)
                bid.auction = auction
                bid.user = request.user
                bid.save()
                messages.success(request, "Ставка успішно розміщена!")
                return redirect("auction", auction_id=auction.id)
            else:
                # Перехоплюємо помилки розширеної валідації з clean_amount()
                for field, errors in bid_form.errors.items():
                    for error in errors:
                        messages.error(request, error)

    return render(request, "auctions/auction.html", {
        "auction": auction,
        "bids": bids,
        "highest_bid": highest_bid,
        "comments": comments,
        "in_watchlist": in_watchlist,
        "bid_form": bid_form,
        "comment_form": comment_form
    })


@login_required
def close_auction(request, auction_id):
    auction = get_object_or_404(Auctions, pk=auction_id)

    if request.user != auction.owner:
        messages.error(request, "Ви не можете закрити цей аукціон.")
        return redirect("auction", auction_id=auction.id)

    if not auction.active:
        messages.info(request, "Аукціон вже закритий.")
        return redirect("auction", auction_id=auction.id)

    highest_bid = auction.bids.order_by("-amount").first()

    if highest_bid:
        auction.winner = highest_bid.user
        messages.success(request, f"Аукціон закрито! Переможець: {highest_bid.user.username} з ставкою {highest_bid.amount}.")
    else:
        messages.info(request, "Аукціон закрито без переможця (не було ставок).")

    auction.active = False
    auction.save()

    return redirect("auction", auction_id=auction.id)


@login_required
def toggle_watchlist(request, auction_id):
    auction = get_object_or_404(Auctions, pk=auction_id)
    watch_item, created = Watchlist.objects.get_or_create(user=request.user, auction=auction)

    if not created:
        watch_item.delete()
        messages.info(request, f"Аукціон '{auction.name}' видалено зі списку відстеження.")
    else:
        messages.success(request, f"Аукціон '{auction.name}' додано до списку відстеження.")

    return redirect("auction", auction_id=auction.id)


@login_required
def watchlist(request):
    close_expired_auctions()
    auctions = Auctions.objects.filter(watchlisted_by__user=request.user)
    return render(request, "auctions/watchlist.html", {
        "auctions": auctions
    })


@login_required
def dashboard(request):
    close_expired_auctions()
    my_auctions = Auctions.objects.filter(owner=request.user)

    my_bids = Bid.objects.filter(
        user=request.user
    ).select_related("auction").order_by("-created_at")[:5]

    favorites = Auctions.objects.filter(
        watchlisted_by__user=request.user
    )[:6]

    won_auctions = Auctions.objects.filter(
        winner=request.user
    )

    comments_count = Comments.objects.filter(
        user=request.user
    ).count()

    context = {
        "my_auctions": my_auctions,
        "my_bids": my_bids,
        "favorites": favorites,
        "won_auctions": won_auctions,

        "total_auctions": my_auctions.count(),
        "active_auctions": my_auctions.filter(active=True).count(),
        "won_count": won_auctions.count(),
        "comments_count": comments_count,
    }
    return render(request, "auctions/dashboard.html", context)