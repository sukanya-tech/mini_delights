from decimal import Decimal

from django.db import migrations


CATALOG = {
    'home': [
        ('Walnut Brownie', '129'),
        ('Chocolate Mousse Cake', '249'),
        ('Brownie Bowls', '299'),
        ('Veg Classic Pizza', '149'),
    ],
    'freshly-baked': [
        ('Fudgy Brownie', '99'),
        ('Cakey Brownie', '89'),
        ('Chewy Brownie', '109'),
        ('Walnut Brownie', '129'),
        ('Chocolate Cupcakes', '79'),
        ('Vanilla Cupcake', '69'),
        ('Strawberry Cupcakes', '89'),
        ('Customize Cupcakes', '119'),
        ('Veg Classic Pizza', '149'),
        ('Corn Cheese Pizza', '169'),
        ('Chicken Pizza', '199'),
        ('Onion Pizza', '139'),
    ],
    'desserts': [
        ('Chocolate BowlCake', '299'),
        ('Velvet BowlCake', '349'),
        ('Midnight BowlCake', '329'),
        ('Classic BowlCake', '289'),
        ('Rose Truffle Box', '259'),
        ('Luxury Truffle Box', '349'),
        ('Chocolate Truffle', '239'),
        ('Assorted Mini Box', '279'),
        ('Classic Mousse', '219'),
        ('Dark Cocoa Mousse', '249'),
        ('Milk Mousse Box', '229'),
        ('Berry Mousse Box', '269'),
        ('Fudgy Brownie Box', '199'),
        ('Cakey Brownie Box', '189'),
        ('Chocolate Mix Box', '239'),
        ('Walnut Brownie Box', '259'),
    ],
    'offers': [
        ('Fudgy Brownie Box', '199'),
        ('Veg Classic Pizza', '199'),
        ('Chocolate BowlCake', '224'),
    ],
}


def seed_catalog(apps, schema_editor):
    Item = apps.get_model('app', 'Item')
    for category, products in CATALOG.items():
        for name, price in products:
            Item.objects.get_or_create(
                name=name,
                category=category,
                defaults={'price': Decimal(price), 'is_available': True},
            )


class Migration(migrations.Migration):
    dependencies = [('app', '0002_cart_cartitem')]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]