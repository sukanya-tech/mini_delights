import uuid
from decimal import Decimal, ROUND_DOWN

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserProfile(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='profile',
	)
	profile_picture = models.ImageField(upload_to='profiles/', blank=True)
	phone_number = models.CharField(max_length=20, blank=True)
	address = models.TextField(blank=True)

	def __str__(self):
		return self.user.get_username()


class PasskeyCredential(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='passkey_credentials',
	)
	credential_id = models.CharField(max_length=1024, unique=True)
	public_key = models.TextField()
	sign_count = models.PositiveBigIntegerField(default=0)
	transports = models.JSONField(default=list, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	last_used_at = models.DateTimeField(null=True, blank=True)

	def __str__(self):
		return f'Passkey for {self.user.get_username()}'


class Item(models.Model):
	class MenuGroup(models.TextChoices):
		BROWNIES = 'brownie-menu', "Brownie's"
		CUPCAKES = 'cupcake-menu', "Cupcake's"
		PIZZAS = 'pizza-menu', "Pizza's"
		OTHER = 'other-menu', 'Other'

	name = models.CharField(max_length=160)
	description = models.TextField(blank=True)
	image = models.ImageField(upload_to='items/', blank=True)
	image_url = models.URLField(max_length=500, blank=True)
	menu_group = models.CharField(max_length=20, choices=MenuGroup.choices, blank=True, default='')
	price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
	discount = models.DecimalField(
		max_digits=5,
		decimal_places=2,
		default=0,
		validators=[MinValueValidator(0), MaxValueValidator(100)],
		help_text='Discount percentage, from 0 to 100.',
	)
	count = models.PositiveIntegerField(default=0, help_text='Available stock quantity.')
	category = models.CharField(max_length=80, db_index=True)
	tags = models.JSONField(default=list, blank=True)
	is_available = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class Offer(models.Model):
	item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='offer')
	label = models.CharField(max_length=80, blank=True)
	description = models.TextField(blank=True)
	discount = models.DecimalField(
		max_digits=5,
		decimal_places=2,
		validators=[MinValueValidator(0), MaxValueValidator(100)],
		help_text='Discount percentage, from 0 to 100.',
	)
	is_active = models.BooleanField(default=True)
	sort_order = models.PositiveSmallIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['sort_order', 'item__name']
		constraints = [
			models.CheckConstraint(
				condition=models.Q(discount__gte=0, discount__lte=100),
				name='offer_discount_between_0_and_100',
			),
		]

	@property
	def discounted_price(self):
		price = self.item.price * (Decimal('100') - self.discount) / Decimal('100')
		return price.quantize(Decimal('1'), rounding=ROUND_DOWN).quantize(Decimal('0.01'))

	def __str__(self):
		return f'{self.item.name} ({self.discount}% off)'


class Cart(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='cart',
	)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def item_count(self):
		return sum(line.quantity for line in self.cart_lines.all())

	def __str__(self):
		return f'Cart for {self.user.get_username()}'


class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_lines')
	item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='cart_lines')
	quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['cart', 'item'], name='unique_item_per_cart'),
		]

	def __str__(self):
		return f'{self.quantity} x {self.item.name}'


class Order(models.Model):
	class Status(models.TextChoices):
		PLACED = 'placed', 'Placed'
		ACCEPTED = 'accepted', 'Accepted'
		PREPARING = 'preparing', 'Preparing'
		OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for delivery'
		DELIVERED = 'delivered', 'Delivered'
		CANCELLED = 'cancelled', 'Cancelled'

	class PaymentMethod(models.TextChoices):
		CASH_ON_DELIVERY = 'cash_on_delivery', 'Cash on delivery'
		UPI = 'upi', 'UPI'
		ONLINE_BANKING = 'online_banking', 'Online banking'

	class PaymentStatus(models.TextChoices):
		PENDING = 'pending', 'Pending'
		PAID = 'paid', 'Paid'
		FAILED = 'failed', 'Failed'
		REFUNDED = 'refunded', 'Refunded'

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.PROTECT,
		related_name='orders',
	)
	address = models.TextField()
	tracking_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	items = models.ManyToManyField(Item, through='OrderItem', related_name='orders')
	total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
	payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
	payment_status = models.CharField(
		max_length=10,
		choices=PaymentStatus.choices,
		default=PaymentStatus.PENDING,
	)
	order_date = models.DateTimeField(auto_now_add=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
	notes = models.TextField(blank=True)

	class Meta:
		ordering = ['-order_date']

	@property
	def item_count(self):
		return sum(line.quantity for line in self.order_lines.all())

	@property
	def delivered(self):
		return self.status == self.Status.DELIVERED

	def __str__(self):
		return f'Order {self.tracking_id}'


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_lines')
	item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name='order_lines')
	quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['order', 'item'], name='unique_item_per_order'),
		]

	@property
	def line_total(self):
		return self.unit_price * self.quantity

	def __str__(self):
		return f'{self.quantity} x {self.item.name}'


class AdminLog(models.Model):
	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='admin_logs',
	)
	action = models.CharField(max_length=120)
	target_type = models.CharField(max_length=80, blank=True)
	target_id = models.CharField(max_length=80, blank=True)
	details = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		ordering = ['-created_at']
		verbose_name = 'admin log entry'
		verbose_name_plural = 'admin log entries'

	def __str__(self):
		return f'{self.action} ({self.created_at:%Y-%m-%d %H:%M})'
