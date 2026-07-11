# auctions/views.py
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import User, Auctions, Bid, Comments, Watchlist
from .forms import AuctionForm, BidForm, CommentForm, UserUpdateForm
from django.contrib import messages
from django.db import transaction


def close_expired_auctions(request=None):
    now = timezone.now()
    with transaction.atomic():
        expired_auctions = Auctions.objects.select_for_update().filter(
            active=True, end_time__isnull=False, end_time__lte=now
        )
        for auction in expired_auctions:
            highest_bid = auction.bids.order_by("-amount").first()
            if highest_bid:
                auction.winner = highest_bid.user
                
                # НАРАХУВАННЯ КОШТІВ ВЛАСНИКУ АУКЦІОНУ
                if auction.owner and hasattr(auction.owner, 'profile'):
                    owner_profile = auction.owner.profile.__class__.objects.select_for_update().get(user=auction.owner)
                    owner_profile.credits += highest_bid.amount
                    owner_profile.save()
                
                if request and request.user.is_authenticated and auction.winner == request.user:
                    messages.success(
                        request, 
                        f"Вітаємо! Ви щойно виграли аукціон '{auction.name}' зі ставкою ₴{highest_bid.amount}!"
                    )
            auction.active = False
            auction.save()


def index(request):
    close_expired_auctions(request) 
  
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    auctions = Auctions.objects.filter(active=True).order_by('-id')

    if query:
        auctions = auctions.filter(name__icontains=query)

    if category_filter and category_filter != 'all':
        auctions = auctions.filter(category=category_filter)
        
    return render(request, "auctions/index.html", {
        "auctions": auctions,
        "query": query,
        "category_filter": category_filter,
        "categories": Auctions.CATEGORY_CHOICES
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
        form = AuctionForm(request.POST, request.FILES)
        if form.is_valid():
            auction = form.save(commit=False)
            auction.owner = request.user
            auction.save()
            messages.success(request, "Аукціон успішно створено!")
            return redirect("index")
    else:
        form = AuctionForm()

    return render(request, "auctions/new_auction.html", {"form": form})


@login_required
def auction(request, auction_id):
    close_expired_auctions(request)
    
    auction = get_object_or_404(Auctions, pk=auction_id)
    bids = auction.bids.all().order_by("-amount")
    highest_bid = bids.first().amount if bids.exists() else None
    comments = auction.comments.all().order_by("-created_at")
    in_watchlist = Watchlist.objects.filter(user=request.user, auction=auction).exists() if request.user.is_authenticated else False

    bid_form = BidForm(auction=auction)
    comment_form = CommentForm()

    if request.method == "POST":
        if "text" in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.auction = auction
                comment.user = request.user
                comment.save()
                messages.success(request, "Коментар додано!")
                return redirect("auction", auction_id=auction.id)
            else:
                for error in comment_form.errors.values():
                    messages.error(request, error.as_text())

        elif "amount" in request.POST:
            bid_form = BidForm(request.POST, auction=auction)
            
            if request.user == auction.owner:
                messages.error(request, "Ви не можете робити ставки на власний аукціон!")
                return redirect("auction", auction_id=auction.id)
            
            if bid_form.is_valid():
                with transaction.atomic():
                    auction = Auctions.objects.select_for_update().get(id=auction.id)
                    bid = bid_form.save(commit=False)
                    bid.auction = auction
                    bid.user = request.user
                    user_profile = request.user.profile.__class__.objects.select_for_update().get(user=request.user)
                    
                    if user_profile.credits < bid.amount:
                        messages.error(request, "На вашому балансі недостатньо кредитів для цієї ставки.")
                        return redirect("auction", auction_id=auction.id)
                    
                    previous_highest_bid = auction.bids.select_for_update().order_by("-amount").first()
                    if previous_highest_bid:
                        if previous_highest_bid.user == request.user:
                            user_profile.credits += previous_highest_bid.amount
                        else:
                            prev_user_profile = previous_highest_bid.user.profile.__class__.objects.select_for_update().get(user=previous_highest_bid.user)
                            prev_user_profile.credits += previous_highest_bid.amount
                            prev_user_profile.save()

                    user_profile.credits -= bid.amount
                    user_profile.save()

                    bid.save()
                    messages.success(request, "Ставка успішно розміщена!")
                    
                return redirect("auction", auction_id=auction.id)
            else:
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

    with transaction.atomic():
        auction = Auctions.objects.select_for_update().get(id=auction.id)
        highest_bid = auction.bids.order_by("-amount").first()

        if highest_bid:
            auction.winner = highest_bid.user
            
            # НАРАХУВАННЯ КОШТІВ ВЛАСНИКУ ПРИ РУЧНОМУ ЗАКРИТТІ
            if auction.owner and hasattr(auction.owner, 'profile'):
                owner_profile = auction.owner.profile.__class__.objects.select_for_update().get(user=auction.owner)
                owner_profile.credits += highest_bid.amount
                owner_profile.save()
                
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
    close_expired_auctions(request)
    auctions = Auctions.objects.filter(watchlisted_by__user=request.user)
    return render(request, "auctions/watchlist.html", {
        "auctions": auctions
    })


@login_required
def dashboard(request):
    close_expired_auctions(request)
    
    won_auctions_unnotified = Auctions.objects.filter(winner=request.user, active=False)
    if won_auctions_unnotified.exists():
        for act in won_auctions_unnotified:
            h_bid = act.bids.order_by("-amount").first()
            amt = h_bid.amount if h_bid else "0.00"
            messages.success(
                request, 
                f"Вітаємо! Ви виграли аукціон '{act.name}' зі ставкою ₴{amt}!"
            )
    
    user_form = UserUpdateForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)
    for field in password_form.fields.values():
        field.widget.attrs.update({'class': 'form-control', 'placeholder': '••••••••'})
        
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            user_form = UserUpdateForm(request.POST, instance=request.user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Профиль успешно обновлен!")
                return redirect('dashboard')
                
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Пароль успешно изменен!")
                return redirect('dashboard')
            else:
                messages.error(request, "Пожалуйста, исправьте ошибки в форме пароля.")

    my_auctions = Auctions.objects.filter(owner=request.user)
    my_bids = Bid.objects.filter(user=request.user).select_related("auction").order_by("-created_at")[:5]
    favorites = Auctions.objects.filter(watchlisted_by__user=request.user)[:6]
    won_auctions = Auctions.objects.filter(winner=request.user)
    total_auctions = my_auctions.count()
    active_auctions = my_auctions.filter(active=True).count()
    won_auctions_count = won_auctions.count()
    comments_count = Comments.objects.filter(user=request.user).count()
    
    context = {
        "user_form": user_form,
        "password_form": password_form,
        "my_auctions": my_auctions,
        "my_bids": my_bids,
        "favorites": favorites,
        "won_auctions": won_auctions,
        "total_auctions": total_auctions,
        "active_auctions": active_auctions,
        "won_auctions_count": won_auctions_count,
        "comments_count": comments_count,
    }
    return render(request, "auctions/dashboard.html", context)