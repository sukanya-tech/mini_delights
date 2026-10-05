from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('app', '0007_item_menu_group'),
	]

	operations = [
		migrations.AddField(
			model_name='item',
			name='image',
			field=models.ImageField(blank=True, upload_to='items/'),
		),
	]
