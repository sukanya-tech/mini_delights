from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.html import escape
from PIL import Image

from .models import CartItem, Item, Offer, Order, UserProfile


class AccountAndCartTests(TestCase):
	def setUp(self):
		self.product = Item.objects.get(name='Walnut Brownie', category='home')

	def test_homepage_renders_home_items_from_the_database(self):
		Item.objects.create(
			name='Database Strawberry Tart',
			price='85.00',
			category='home',
			image_url='https://example.com/strawberry-tart.jpg',
			description='Fresh strawberry tart with vanilla cream.',
		)
		Item.objects.create(
			name='Unavailable Tart',
			price='90.00',
			category='home',
			is_available=False,
		)

		response = self.client.get(reverse('home'))

		self.assertContains(response, 'Database Strawberry Tart')
		self.assertContains(response, 'https://example.com/strawberry-tart.jpg')
		self.assertContains(response, 'Fresh strawberry tart with vanilla cream.')
		self.assertContains(response, 'Walnut Brownie')
		self.assertNotContains(response, 'Unavailable Tart')
		self.assertNotContains(response, 'Freshly made in our kitchen')
		self.assertNotContains(response, 'images.unsplash.com')
		self.assertEqual(response.context['featured_items'].count(), 5)

	def test_explore_more_shows_unique_database_featured_items(self):
		response = self.client.get(reverse('home'))
		featured_items = list(Item.objects.filter(category='home', is_available=True))
		image_urls = [item.image_url for item in featured_items if item.image_url]

		self.assertContains(response, 'href="#special-items"')
		self.assertContains(response, 'id="special-items"')
		self.assertContains(response, '<article class="delivery-card">', count=len(featured_items))
		self.assertEqual(len(image_urls), len(set(image_urls)))
		self.assertNotContains(response, 'images.unsplash.com')
		self.assertNotContains(response, 'product-image-placeholder')
		for item in featured_items:
			if item.image_url:
				self.assertContains(response, escape(item.image_url), count=1)

	def test_homepage_shows_no_items_available_when_catalog_is_empty(self):
		Item.objects.filter(category='home').update(is_available=False)

		response = self.client.get(reverse('home'))

		self.assertContains(response, 'No items available')
		self.assertEqual(response.context['featured_items'].count(), 0)

	def test_freshly_baked_page_renders_database_items_without_demo_images(self):
		Item.objects.create(
			name='Database Cinnamon Roll',
			price='72.00',
			category='freshly-baked',
			description='Cinnamon roll added from the catalog.',
		)

		response = self.client.get(reverse('freshly-baked'))

		self.assertContains(response, 'Database Cinnamon Roll')
		self.assertContains(response, 'Cinnamon roll added from the catalog.')
		self.assertNotContains(response, 'images.unsplash.com')
		self.assertEqual(response.context['freshly_baked_items'].count(), 13)

	def test_freshly_baked_page_shows_empty_message_when_no_items_are_available(self):
		Item.objects.filter(category='freshly-baked').update(is_available=False)

		response = self.client.get(reverse('freshly-baked'))

		self.assertContains(response, 'No items available')
		self.assertEqual(response.context['freshly_baked_items'].count(), 0)

	def test_desserts_page_renders_available_database_items_without_demo_content(self):
		Item.objects.create(
			name='Database Chocolate Tart',
			price='85.00',
			category='desserts',
			image_url='https://example.com/chocolate-tart.jpg',
			description='Chocolate tart added from the catalog.',
		)
		Item.objects.create(
			name='Unavailable Dessert',
			price='90.00',
			category='desserts',
			is_available=False,
		)
		Item.objects.create(
			name='Different Category Dessert',
			price='75.00',
			category='home',
		)

		response = self.client.get(reverse('desserts'))

		self.assertContains(response, 'Database Chocolate Tart')
		self.assertContains(response, 'https://example.com/chocolate-tart.jpg')
		self.assertContains(response, 'Chocolate tart added from the catalog.')
		self.assertContains(response, '₹85.00')
		self.assertNotContains(response, 'Unavailable Dessert')
		self.assertNotContains(response, 'Different Category Dessert')
		self.assertNotContains(response, 'images.unsplash.com')
		self.assertEqual(response.context['dessert_items'].count(), 17)

	def test_desserts_page_shows_empty_message_when_no_items_are_available(self):
		Item.objects.filter(category='desserts').update(is_available=False)

		response = self.client.get(reverse('desserts'))

		self.assertContains(response, 'No items available')
		self.assertNotContains(response, 'images.unsplash.com')
		self.assertNotContains(response, '<article class="delivery-card">')
		self.assertEqual(response.context['dessert_items'].count(), 0)

	def test_registration_saves_account_then_requires_login(self):
		response = self.client.post(reverse('register'), {
			'username': 'sweetuser',
			'email': 'sweet@example.com',
			'password': 'M0reSecure!blue-sky2026',
			'confirm_password': 'M0reSecure!blue-sky2026',
		})

		self.assertRedirects(response, reverse('login-page'), fetch_redirect_response=False)
		user = User.objects.get(username='sweetuser')
		self.assertEqual(user.email, 'sweet@example.com')
		self.assertTrue(user.check_password('M0reSecure!blue-sky2026'))
		self.assertNotIn('_auth_user_id', self.client.session)
		self.assertEqual(user.profile.user_id, user.pk)
		login_page = self.client.get(reverse('login-page'))
		self.assertContains(login_page, 'Login')
		self.assertContains(login_page, 'Your account has been created. Please log in.')

		login_response = self.client.post(reverse('login-page'), {
			'username': 'sweetuser',
			'password': 'M0reSecure!blue-sky2026',
		})

		self.assertRedirects(login_response, reverse('home'))
		self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

	def test_existing_account_can_log_in_again_with_saved_cart(self):
		user = User.objects.create_user(
			username='returning',
			email='returning@example.com',
			password='M0reSecure!blue-sky2026',
		)
		self.client.force_login(user)
		self.client.post(reverse('cart-items'), {
			'name': self.product.name,
			'category': self.product.category,
		})
		self.client.get(reverse('logout'))

		response = self.client.post(reverse('login-page'), {
			'username': 'returning',
			'password': 'M0reSecure!blue-sky2026',
		})

		self.assertRedirects(response, reverse('home'))
		cart_response = self.client.get(reverse('cart-items'))
		self.assertEqual(cart_response.status_code, 200)
		self.assertEqual(cart_response.json()['item_count'], 1)
		self.assertEqual(CartItem.objects.get(cart__user=user).item, self.product)
		self.assertEqual(user.profile.user_id, user.pk)

	def test_profile_updates_are_saved_to_the_logged_in_users_profile(self):
		user = User.objects.create_user(
			username='profileuser',
			email='profile@example.com',
			password='M0reSecure!blue-sky2026',
		)
		self.client.force_login(user)

		response = self.client.post(reverse('profile'), {
			'name': 'Profile User',
			'email': 'profile@example.com',
			'phone': '555-0102',
		})

		self.assertRedirects(response, reverse('profile'))
		profile = UserProfile.objects.get(user_id=user.pk)
		self.assertEqual(profile.phone_number, '555-0102')
		self.assertEqual(user.pk, profile.user_id)
		self.assertContains(self.client.get(reverse('profile')), '555-0102')

	def test_cart_requires_login_and_uses_stored_price(self):
		guest_cart = self.client.get(reverse('cart-items'))
		self.assertEqual(guest_cart.status_code, 200)
		self.assertEqual(guest_cart.json()['item_count'], 0)

		response = self.client.post(reverse('cart-items'), {
			'name': self.product.name,
			'category': self.product.category,
			'price': '0.01',
		})
		self.assertEqual(response.status_code, 401)

		user = User.objects.create_user(username='buyer', password='M0reSecure!blue-sky2026')
		self.client.force_login(user)
		response = self.client.post(reverse('cart-items'), {
			'name': self.product.name,
			'category': self.product.category,
			'price': '0.01',
		})
		self.assertEqual(response.json()['items'][0]['price'], str(self.product.price))

	def test_cart_can_remove_item(self):
		user = User.objects.create_user(username='buyer', password='M0reSecure!blue-sky2026')
		self.client.force_login(user)
		added = self.client.post(reverse('cart-items'), {
			'name': self.product.name,
			'category': self.product.category,
		}).json()

		response = self.client.post(reverse('cart-items'), {
			'action': 'remove',
			'item_id': added['items'][0]['id'],
		})

		self.assertEqual(response.json()['item_count'], 0)

	def test_adding_same_product_increments_quantity(self):
		user = User.objects.create_user(username='buyer', password='M0reSecure!blue-sky2026')
		self.client.force_login(user)
		payload = {'name': self.product.name, 'category': self.product.category}

		self.client.post(reverse('cart-items'), payload)
		response = self.client.post(reverse('cart-items'), payload)

		self.assertEqual(response.json()['item_count'], 2)
		self.assertEqual(response.json()['items'][0]['quantity'], 2)

	def test_offer_page_uses_database_offer_records(self):
		response = self.client.get(reverse('offers'))
		self.assertContains(response, 'Fudgy Brownie Box')
		self.assertContains(response, '50% OFF')
		self.assertContains(response, 'Buy Now')
		self.assertEqual(response.context['offers'].count(), 3)

	def test_adding_offer_to_cart_uses_discounted_database_price(self):
		user = User.objects.create_user(username='offerbuyer', password='M0reSecure!blue-sky2026')
		self.client.force_login(user)
		offer = Offer.objects.get(item__name='Fudgy Brownie Box', item__category='offers')

		response = self.client.post(reverse('cart-items'), {
			'name': offer.item.name,
			'category': offer.item.category,
			'price': '0.01',
		})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['items'][0]['price'], '199.00')
		self.assertEqual(response.json()['total'], '199.00')

	def test_inactive_offer_cannot_be_added_to_cart(self):
		user = User.objects.create_user(username='offerbuyer', password='M0reSecure!blue-sky2026')
		self.client.force_login(user)
		offer = Offer.objects.get(item__name='Fudgy Brownie Box', item__category='offers')
		offer.is_active = False
		offer.save(update_fields=['is_active'])

		response = self.client.post(reverse('cart-items'), {
			'name': offer.item.name,
			'category': offer.item.category,
		})

		self.assertEqual(response.status_code, 404)

	def test_management_pages_are_role_protected_and_read_database_records(self):
		self.assertEqual(self.client.get(reverse('management-dashboard')).status_code, 302)

		staff_user = User.objects.create_user(
			username='staffmanager',
			password='M0reSecure!blue-sky2026',
		)
		staff_user.is_staff = True
		staff_user.save(update_fields=['is_staff'])
		self.client.force_login(staff_user)

		self.assertContains(self.client.get(reverse('management-items')), self.product.name)
		order = Order.objects.create(
			user=staff_user,
			address='123 Test Street',
			payment_method=Order.PaymentMethod.CASH_ON_DELIVERY,
		)
		self.assertContains(self.client.get(reverse('management-orders')), str(order.tracking_id))
		self.assertEqual(self.client.get(reverse('management-users')).status_code, 302)

		admin_user = User.objects.create_superuser(
			username='siteadmin',
			email='admin@example.com',
			password='M0reSecure!blue-sky2026',
		)
		self.client.force_login(admin_user)
		self.assertContains(self.client.get(reverse('management-users')), 'staffmanager')

	def test_admin_dashboard_is_limited_to_staff_and_shows_app_controls(self):
		url = reverse('admin-dashboard')
		self.assertEqual(self.client.get(url).status_code, 302)

		customer = User.objects.create_user(
			username='dashboardcustomer',
			password='M0reSecure!blue-sky2026',
		)
		self.client.force_login(customer)
		self.assertEqual(self.client.get(url).status_code, 302)
		self.assertNotContains(self.client.get(reverse('home')), 'Admin dashboard')

		staff_user = User.objects.create_user(
			username='dashboardadmin',
			password='M0reSecure!blue-sky2026',
			is_staff=True,
		)
		self.client.force_login(staff_user)
		response = self.client.get(url)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Admin control center')
		self.assertContains(response, 'Catalog items')
		self.assertContains(response, 'Total orders')
		self.assertContains(response, 'Manage items')
		self.assertContains(response, 'Manage orders')
		self.assertContains(response, 'background: #f1edff')
		self.assertEqual(response.context['item_count'], Item.objects.count())
		self.assertEqual(response.context['user_count'], User.objects.count())
		self.assertContains(self.client.get(reverse('home')), 'Admin dashboard')

	def test_staff_pages_use_consistent_navigation_without_exposing_admin_links_to_customers(self):
		staff_user = User.objects.create_user(
			username='navigationstaff',
			password='M0reSecure!blue-sky2026',
			is_staff=True,
		)
		self.client.force_login(staff_user)
		staff_page_names = (
			'home',
			'freshly-baked',
			'desserts',
			'offers',
			'contact',
			'brownies',
			'cupcakes',
			'pizzas',
			'profile',
			'management-dashboard',
			'management-items',
			'management-orders',
			'admin-dashboard',
		)
		for page_name in staff_page_names:
			with self.subTest(page=page_name):
				response = self.client.get(reverse(page_name))
				self.assertEqual(response.status_code, 200)
				navigation = response.content.decode().split('<nav class="home-nav"', 1)[1].split('</nav>', 1)[0]
				for link_label in ('Home', 'Freshly Baked', 'Desserts', 'Offers', 'Contact Us', 'Admin dashboard'):
					self.assertContains(response, link_label)
				for forbidden_link in ('Overview', 'Items', 'Orders', 'Users', 'Admin site', 'Django admin'):
					self.assertNotIn(forbidden_link, navigation)
				self.assertNotIn('href="/admin/', navigation)

		customer = User.objects.create_user(
			username='navigationcustomer',
			password='M0reSecure!blue-sky2026',
		)
		self.client.force_login(customer)
		for page_name in ('home', 'freshly-baked', 'desserts', 'offers', 'contact', 'profile'):
			with self.subTest(customer_page=page_name):
				response = self.client.get(reverse(page_name))
				navigation = response.content.decode().split('<nav class="home-nav"', 1)[1].split('</nav>', 1)[0]
				for link_label in ('Home', 'Freshly Baked', 'Desserts', 'Offers', 'Contact Us'):
					self.assertIn(link_label, navigation)
				self.assertNotIn('Admin dashboard', navigation)
				self.assertNotIn('Admin site', navigation)
				self.assertNotIn('href="/admin/', navigation)

	def test_admin_can_save_catalog_item_with_uploaded_image(self):
		staff_user = User.objects.create_user(
			username='itemadmin',
			password='M0reSecure!blue-sky2026',
			is_staff=True,
		)
		self.client.force_login(staff_user)
		image_bytes = BytesIO()
		Image.new('RGB', (2, 2), color='lavender').save(image_bytes, format='PNG')
		uploaded_image = SimpleUploadedFile(
			'lavender-cake.png',
			image_bytes.getvalue(),
			content_type='image/png',
		)

		with TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				response = self.client.post(reverse('admin-dashboard'), {
					'action': 'add_item',
					'name': 'Admin-added Lavender Cake',
					'description': 'A freshly added catalog item.',
					'price': '125.50',
					'category': 'desserts',
					'count': '8',
					'image': uploaded_image,
				})

				self.assertRedirects(response, reverse('admin-dashboard'))
				item = Item.objects.get(name='Admin-added Lavender Cake')
				self.assertEqual(item.description, 'A freshly added catalog item.')
				self.assertEqual(str(item.price), '125.50')
				self.assertEqual(item.category, 'desserts')
				self.assertEqual(item.count, 8)
				self.assertTrue(item.image.name.startswith('items/'))
				self.assertTrue(item.image.storage.exists(item.image.name))

				desserts_response = self.client.get(reverse('desserts'))
				self.assertContains(desserts_response, 'Admin-added Lavender Cake')
				self.assertContains(desserts_response, item.image.url)

	def test_non_staff_cannot_add_catalog_items(self):
		customer = User.objects.create_user(
			username='regularitemcustomer',
			password='M0reSecure!blue-sky2026',
		)
		self.client.force_login(customer)

		response = self.client.post(reverse('admin-dashboard'), {
			'name': 'Customer-added item',
			'description': '',
			'price': '5.00',
			'category': 'desserts',
			'count': '1',
		})

		self.assertEqual(response.status_code, 302)
		self.assertFalse(Item.objects.filter(name='Customer-added item').exists())

	def test_admin_can_update_and_delete_items_from_dashboard_table(self):
		staff_user = User.objects.create_user(
			username='tableadmin',
			password='M0reSecure!blue-sky2026',
			is_staff=True,
		)
		self.client.force_login(staff_user)
		item = Item.objects.create(
			name='Editable dashboard item',
			description='Original description',
			price='25.00',
			category='desserts',
			count=2,
		)

		response = self.client.get(reverse('admin-dashboard'))
		self.assertContains(response, 'Items · update or delete')
		self.assertContains(response, 'Editable dashboard item')
		self.assertContains(response, 'UPDATE')
		self.assertContains(response, 'DELETE')

		update_response = self.client.post(reverse('admin-dashboard'), {
			'action': 'update_item',
			'item_id': str(item.pk),
			f'item-{item.pk}-name': 'Updated dashboard item',
			f'item-{item.pk}-description': 'Updated description',
			f'item-{item.pk}-price': '39.50',
			f'item-{item.pk}-category': 'desserts',
			f'item-{item.pk}-count': '12',
		})
		self.assertRedirects(update_response, reverse('admin-dashboard'))
		item.refresh_from_db()
		self.assertEqual(item.name, 'Updated dashboard item')
		self.assertEqual(item.description, 'Updated description')
		self.assertEqual(str(item.price), '39.50')
		self.assertEqual(item.count, 12)

		delete_response = self.client.post(reverse('admin-dashboard'), {
			'action': 'delete_item',
			'item_id': str(item.pk),
		})
		self.assertRedirects(delete_response, reverse('admin-dashboard'))
		self.assertFalse(Item.objects.filter(pk=item.pk).exists())
