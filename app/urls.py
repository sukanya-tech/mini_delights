from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('freshly-baked/', views.freshly_baked, name='freshly-baked'),
    path('desserts/', views.desserts, name='desserts'),
    path('offers/', views.offers, name='offers'),
    path('contact/', views.contact, name='contact'),
    path('brownies/', views.brownies, name='brownies'),
    path('cupcakes/', views.cupcakes, name='cupcakes'),
    path('pizzas/', views.pizzas, name='pizzas'),
    path('login/', views.login_page, name='login-page'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('cart/items/', views.cart_items, name='cart-items'),
    path('admin-dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('management/', views.management_dashboard, name='management-dashboard'),
    path('management/items/', views.management_items, name='management-items'),
    path('management/orders/', views.management_orders, name='management-orders'),
    path('management/users/', views.management_users, name='management-users'),
]
