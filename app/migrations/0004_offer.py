from decimal import Decimal

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


OFFERS = [
	('Fudgy Brownie Box', '199', '399', '50', "Rich chocolate flavor with warm, gooey texture.", "Brownie's", 0),
	('Veg Classic Pizza', '199', '249', '20', 'Fresh toppings, melted cheese, and golden crust.', "Pizza's", 1),
	('Chocolate BowlCake', '224', '299', '25', 'Silky chocolate layers topped with a dreamy finish.', "Dessert's", 2),
]


def seed_offers(apps, schema_editor):
	Item = apps.get_model('app', 'Item')
	Offer = apps.get_model('app', 'Offer')
	for name, sale_price, original_price, discount, description, label, sort_order in OFFERS:
		item, _ = Item.objects.get_or_create(
			name=name,
			category='offers',
			defaults={'price': Decimal(original_price), 'is_available': True},
		)
		if item.price == Decimal(sale_price):
			item.price = Decimal(original_price)
			item.save(update_fields=['price'])
		Offer.objects.update_or_create(
			item=item,
			defaults={
				'discount': Decimal(discount),
				'description': description,
				'label': label,
				'is_active': True,
				'sort_order': sort_order,
			},
		)


class Migration(migrations.Migration):
	dependencies = [('app', '0003_seed_catalog_items')]

	operations = [
		migrations.CreateModel(
			name='Offer',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('label', models.CharField(blank=True, max_length=80)),
				('description', models.TextField(blank=True)),
				('discount', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], help_text='Discount percentage, from 0 to 100.')),
				('is_active', models.BooleanField(default=True)),
				('sort_order', models.PositiveSmallIntegerField(default=0)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='offer', to='app.item')),
			],
			options={'ordering': ['sort_order', 'item__name']},
		),
		migrations.AddConstraint(
			model_name='offer',
			constraint=models.CheckConstraint(condition=models.Q(('discount__gte', 0), ('discount__lte', 100)), name='offer_discount_between_0_and_100'),
		),
		migrations.RunPython(seed_offers, migrations.RunPython.noop),
	]