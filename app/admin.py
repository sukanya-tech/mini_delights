from django.contrib import admin

from .models import AdminLog, Cart, CartItem, Item, Offer, Order, OrderItem, PasskeyCredential, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'phone_number')
	search_fields = ('user__username', 'user__email', 'phone_number')


@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
	list_display = ('user', 'credential_id', 'created_at', 'last_used_at')
	search_fields = ('user__username', 'user__email', 'credential_id')
	readonly_fields = ('created_at', 'last_used_at')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'menu_group', 'price', 'discount', 'count', 'is_available')
	list_filter = ('category', 'menu_group', 'is_available')
	search_fields = ('name', 'category')


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
	list_display = ('item', 'discount', 'is_active', 'sort_order')
	list_filter = ('is_active',)
	search_fields = ('item__name', 'label', 'description')


class CartItemInline(admin.TabularInline):
	model = CartItem
	extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
	list_display = ('user', 'updated_at')
	search_fields = ('user__username', 'user__email')
	inlines = (CartItemInline,)


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	readonly_fields = ('unit_price',)


@admin.action(description='Accept selected orders')
def accept_orders(modeladmin, request, queryset):
	queryset.exclude(status=Order.Status.CANCELLED).update(status=Order.Status.ACCEPTED)


@admin.action(description='Cancel selected orders')
def cancel_orders(modeladmin, request, queryset):
	queryset.exclude(status=Order.Status.DELIVERED).update(status=Order.Status.CANCELLED)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('tracking_id', 'user', 'status', 'payment_method', 'payment_status', 'total_price', 'order_date')
	list_filter = ('status', 'payment_method', 'payment_status', 'order_date')
	search_fields = ('tracking_id', 'user__username', 'user__email')
	readonly_fields = ('tracking_id', 'order_date', 'delivered_at')
	inlines = (OrderItemInline,)
	actions = (accept_orders, cancel_orders)


@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
	list_display = ('created_at', 'actor', 'action', 'target_type', 'target_id')
	list_filter = ('action', 'target_type', 'created_at')
	search_fields = ('actor__username', 'action', 'target_type', 'target_id')
	readonly_fields = ('actor', 'action', 'target_type', 'target_id', 'details', 'created_at')
