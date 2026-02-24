from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from django.contrib.auth.decorators import login_required

from .models import User, Auctions, Bid, Comments, Watchlist

from django.contrib import messages


def index(request):
    return render(request, "auctions/index.html", {
        "auctions": Auctions.objects.all()
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
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

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
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
        title = request.POST.get("title")
        description = request.POST.get("content")
        start_price = request.POST.get("start_price")
        image = request.FILES.get("image")

        auction = Auctions(
            name = title,
            description = description,
            start_price = start_price,
            image = image,
            owner = request.user
        )
        auction.save()

        return redirect("index")

    return render(request, "auctions/new_auction.html")


@login_required
def auction(request, auction_id):
    auction = Auctions.objects.get(pk=auction_id)
    bids = auction.bids.all().order_by("-amount")  # всі ставки
    highest_bid = bids.first().amount if bids.exists() else None
    comments = auction.comments.all().order_by("-created_at")
    in_watchlist = Watchlist.objects.filter(user=request.user, auction=auction).exists() if request.user.is_authenticated else False

    if request.method == "POST":
        # Якщо прийшла форма з коментарем
        if "comment" in request.POST:
            if request.user.is_authenticated:
                text = request.POST.get("comment")
                if text.strip():
                    Comments.objects.create(
                        auction=auction,
                        user=request.user,
                        text=text
                    )
                    messages.success(request, "Коментар додано!")
                else:
                    messages.error(request, "Коментар не може бути порожнім.")
            else:
                messages.error(request, "Увійдіть у систему, щоб залишати коментарі.")
            return redirect("auction", auction_id=auction.id)

        # Якщо прийшла форма зі ставкою
        elif "bid" in request.POST:
            bid_amount = request.POST.get("bid")
            try:
                bid_amount = float(bid_amount)
            except (TypeError, ValueError):
                messages.error(request, "Некоректна сума ставки.")
                return redirect("auction", auction_id=auction.id)

            if bid_amount < float(auction.start_price):
                messages.error(request, "Ставка має бути не меншою за початкову ціну.")
            elif highest_bid and bid_amount <= float(highest_bid):
                messages.error(request, f"Ставка має бути більшою за поточну найвищу ({highest_bid}).")
            else:
                Bid.objects.create(
                    auction=auction,
                    user=request.user,
                    amount=bid_amount
                )
                messages.success(request, "Ставка успішно розміщена!")
            return redirect("auction", auction_id=auction.id)

    return render(request, "auctions/auction.html", {
        "auction": auction,
        "bids": bids,
        "highest_bid": highest_bid,
        "comments": comments,
        "in_watchlist": in_watchlist
    })


@login_required
def close_auction(request, auction_id):
    auction = get_object_or_404(Auctions, pk=auction_id)

    # лише автор може закрити
    if request.user != auction.owner:
        messages.error(request, "Ви не можете закрити цей аукціон.")
        return redirect("auction", auction_id=auction.id)

    # якщо вже закритий
    if not auction.active:
        messages.info(request, "Аукціон вже закритий.")
        return redirect("auction", auction_id=auction.id)

    # шукаємо найбільшу ставку
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
        # Якщо вже є в списку — видаляємо
        watch_item.delete()
        messages.info(request, f"Аукціон '{auction.name}' видалено зі списку відстеження.")
    else:
        messages.success(request, f"Аукціон '{auction.name}' додано до списку відстеження.")

    return redirect("auction", auction_id=auction.id)


@login_required
def watchlist(request):
    auctions = Auctions.objects.filter(watchlisted_by__user=request.user)
    return render(request, "auctions/watchlist.html", {
        "auctions": auctions
    })