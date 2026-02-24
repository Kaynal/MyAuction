from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("new_auction", views.new_auction, name="new_auction"),
    path("auction/<int:auction_id>/", views.auction, name="auction"),
    path("auction/<int:auction_id>/close/", views.close_auction, name="close_auction"),
    path("auction/<int:auction_id>/watchlist/", views.toggle_watchlist, name="toggle_watchlist"),
    path("watchlist/", views.watchlist, name="watchlist")
]
