from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Cart, CartItem, Item, Offer, Order, UserProfile
from .forms import AdminItemForm


User = get_user_model()


def _auth_redirect(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('home')


def _cart_data(cart):
    lines = list(cart.cart_lines.select_related('item', 'item__offer').order_by('item__name'))
    items = [
        {
            'id': line.pk,
            'name': line.item.name,
            'price': str(_item_price(line.item)),
            'quantity': line.quantity,
            'line_total': str(_item_price(line.item) * line.quantity),
        }
        for line in lines
    ]
    return {
        'items': items,
        'item_count': sum(line.quantity for line in lines),
        'total': str(sum((_item_price(line.item) * line.quantity for line in lines), start=0)),
    }


def _item_price(item):
    try:
        offer = item.offer
    except Offer.DoesNotExist:
        return item.price
    return offer.discounted_price if offer.is_active else item.price


@ensure_csrf_cookie
def home(request):
    featured_items = Item.objects.filter(category='home', is_available=True).order_by('name')
    return render(request, 'page.html', {'featured_items': featured_items})


@ensure_csrf_cookie
def freshly_baked(request):
    freshly_baked_items = Item.objects.filter(
        category='freshly-baked',
        is_available=True,
    ).order_by('menu_group', 'name')
    items_by_group = {}
    for item in freshly_baked_items:
        menu_group = item.menu_group or Item.MenuGroup.OTHER
        items_by_group.setdefault(menu_group, []).append(item)

    menu_groups = [
        {
            'slug': menu_group,
            'label': label,
            'items': items_by_group[menu_group],
        }
        for menu_group, label in Item.MenuGroup.choices
        if menu_group in items_by_group
    ]
    return render(request, 'freshly_baked.html', {
        'freshly_baked_items': freshly_baked_items,
        'menu_groups': menu_groups,
    })


@ensure_csrf_cookie
def desserts(request):
    dessert_items = Item.objects.filter(
        category='desserts',
        is_available=True,
    ).order_by('name')
    return render(request, 'desserts.html', {'dessert_items': dessert_items})


@ensure_csrf_cookie
def offers(request):
    available_offers = Offer.objects.filter(
        is_active=True,
        item__is_available=True,
    ).select_related('item')
    return render(request, 'offers.html', {'offers': available_offers})


def contact(request):
    return render(request, 'contact.html')


def brownies(request):
    return render(request, 'brownies.html')


def cupcakes(request):
    return render(request, 'cupcakes.html')


def pizzas(request):
    return render(request, 'pizzas.html')


def login_page(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return _auth_redirect(request)
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if not username or not email or not password:
            messages.error(request, 'All fields are required.')
        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        else:
            user = User(username=username, email=email)
            try:
                validate_password(password, user=user)
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.first_name = username
                user.save(update_fields=['first_name'])
                UserProfile.objects.get_or_create(user=user)
                messages.success(request, 'Your account has been created. Please log in.')
                return redirect('login-page')
    return render(request, 'signup.html')


@login_required(login_url='login-page')
def profile(request):
    user = request.user
    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        user.first_name = name
        user.email = email
        user.save()
        user_profile.phone_number = phone
        user_profile.save(update_fields=['phone_number'])
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    return render(request, 'profile.html', {
        'profile_name': user.first_name or user.username,
        'profile_email': user.email,
        'profile_phone': user_profile.phone_number,
    })


def logout_view(request):
    logout(request)
    return redirect('home')


@require_http_methods(['GET', 'POST'])
def cart_items(request):
    if not request.user.is_authenticated:
        if request.method == 'GET':
            return JsonResponse({'items': [], 'item_count': 0, 'total': '0'})
        return JsonResponse({'error': 'Please log in to use your cart.'}, status=401)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    if request.method == 'GET':
        return JsonResponse(_cart_data(cart))

    if request.POST.get('action') == 'remove':
        line = CartItem.objects.filter(
            pk=request.POST.get('item_id'),
            cart=cart,
        ).first()
        if line is None:
            return JsonResponse({'error': 'Cart item not found.'}, status=404)
        line.delete()
        return JsonResponse(_cart_data(cart))

    item = Item.objects.filter(
        name=request.POST.get('name', '').strip(),
        category=request.POST.get('category', '').strip(),
        is_available=True,
    ).first()
    if item is None:
        return JsonResponse({'error': 'This product is not available.'}, status=404)
    if item.category == 'offers' and not Offer.objects.filter(item=item, is_active=True).exists():
        return JsonResponse({'error': 'This offer is no longer available.'}, status=404)

    line, created = CartItem.objects.get_or_create(
        cart=cart,
        item=item,
        defaults={'quantity': 1},
    )
    if not created:
        line.quantity += 1
        line.save(update_fields=['quantity'])
    return JsonResponse(_cart_data(cart))


@user_passes_test(lambda account: account.is_staff, login_url='login-page')
@require_http_methods(['GET', 'POST'])
def admin_dashboard(request):
    item_form = AdminItemForm()
    row_form = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_item':
            item_form = AdminItemForm(request.POST, request.FILES)
            if item_form.is_valid():
                item_form.save()
                messages.success(request, 'Item saved successfully.')
                return redirect('admin-dashboard')
            messages.error(request, 'Please correct the errors below and try again.')
        elif action == 'update_item':
            item = get_object_or_404(Item, pk=request.POST.get('item_id'))
            prefix = f'item-{item.pk}'
            row_form = AdminItemForm(
                request.POST,
                request.FILES,
                instance=item,
                prefix=prefix,
            )
            if row_form.is_valid():
                row_form.save()
                messages.success(request, f'{item.name} was updated.')
                return redirect('admin-dashboard')
            messages.error(request, 'Please correct the item errors and try again.')
        elif action == 'delete_item':
            item = get_object_or_404(Item, pk=request.POST.get('item_id'))
            image_name = item.image.name
            image_storage = item.image.storage
            try:
                item.delete()
            except ProtectedError:
                messages.error(
                    request,
                    f'{item.name} cannot be deleted because it is used in an order or cart.',
                )
            else:
                if image_name:
                    image_storage.delete(image_name)
                messages.success(request, f'{item.name} was deleted.')
            return redirect('admin-dashboard')
        else:
            messages.error(request, 'Choose a valid item action.')

    item_rows = []
    for item in Item.objects.order_by('name'):
        prefix = f'item-{item.pk}'
        form = row_form if row_form and row_form.instance.pk == item.pk else AdminItemForm(
            instance=item,
            prefix=prefix,
        )
        form_id = f'update-item-{item.pk}'
        for field in form.fields.values():
            field.widget.attrs['form'] = form_id
        form.fields['image'].widget.attrs['class'] = 'admin-row-image'
        item_rows.append({'item': item, 'form': form, 'form_id': form_id})
    return render(request, 'admin_dashboard.html', {
        'item_count': Item.objects.count(),
        'order_count': Order.objects.count(),
        'pending_order_count': Order.objects.filter(status=Order.Status.PLACED).count(),
        'user_count': User.objects.count(),
        'item_form': item_form,
        'item_rows': item_rows,
    })


@user_passes_test(lambda account: account.is_staff, login_url='login-page')
def management_dashboard(request):
    return render(request, 'management.html', {
        'section': 'dashboard',
        'item_count': Item.objects.count(),
        'order_count': Order.objects.count(),
        'user_count': User.objects.count(),
        'pending_order_count': Order.objects.filter(status=Order.Status.PLACED).count(),
    })


@user_passes_test(lambda account: account.is_staff, login_url='login-page')
def management_items(request):
    return render(request, 'management.html', {
        'section': 'items',
        'items': Item.objects.order_by('name'),
        'admin_list_url': reverse('admin:app_item_changelist'),
        'admin_add_url': reverse('admin:app_item_add'),
    })


@user_passes_test(lambda account: account.is_staff, login_url='login-page')
def management_orders(request):
    return render(request, 'management.html', {
        'section': 'orders',
        'orders': Order.objects.select_related('user'),
        'admin_list_url': reverse('admin:app_order_changelist'),
        'admin_add_url': reverse('admin:app_order_add'),
    })


@user_passes_test(lambda account: account.is_superuser, login_url='login-page')
def management_users(request):
    return render(request, 'management.html', {
        'section': 'users',
        'accounts': User.objects.order_by('username'),
        'admin_list_url': reverse('admin:auth_user_changelist'),
        'admin_add_url': reverse('admin:auth_user_add'),
    })
