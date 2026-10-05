(function () {
	const script = document.currentScript;
	const cartUrl = script.dataset.cartUrl;
	const loginUrl = script.dataset.loginUrl;
	const cartButton = document.querySelector('#cart-button');
	const cartPanel = document.querySelector('#cart-panel');
	const closeButton = document.querySelector('#close-cart');
	const countElement = document.querySelector('#cart-count');
	const emptyElement = document.querySelector('#cart-empty');
	const categoryElement = document.querySelector('[data-cart-category]');
	let listElement;
	let totalElement;

	function getCookie(name) {
		const cookie = document.cookie.split('; ').find(function (entry) {
			return entry.startsWith(name + '=');
		});
		return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : '';
	}

	function setPanelOpen(isOpen) {
		cartPanel.hidden = !isOpen;
		cartButton.setAttribute('aria-expanded', String(isOpen));
	}

	function updateCart(data) {
		countElement.textContent = data.item_count;
		if (!listElement) {
			listElement = document.createElement('div');
			listElement.className = 'cart-items-list';
			cartPanel.insertBefore(listElement, emptyElement.nextSibling);
		}
		if (!totalElement) {
			totalElement = document.createElement('div');
			totalElement.className = 'cart-total';
			listElement.after(totalElement);
		}

		listElement.replaceChildren();
		data.items.forEach(function (item) {
			const row = document.createElement('div');
			row.className = 'cart-item';
			const name = document.createElement('span');
			name.textContent = item.name + ' x ' + item.quantity;
			const price = document.createElement('span');
			price.textContent = '₹' + item.line_total;
			const removeButton = document.createElement('button');
			removeButton.type = 'button';
			removeButton.className = 'cart-remove';
			removeButton.dataset.cartItemId = item.id;
			removeButton.setAttribute('aria-label', 'Remove ' + item.name + ' from cart');
			removeButton.textContent = '×';
			row.append(name, price, removeButton);
			listElement.append(row);
		});

		emptyElement.hidden = data.items.length > 0;
		totalElement.replaceChildren();
		if (data.items.length) {
			const total = document.createElement('strong');
			total.textContent = 'Total: ₹' + data.total;
			totalElement.append(total);
		}
	}

	async function sendCartRequest(values) {
		const response = await fetch(cartUrl, {
			method: values ? 'POST' : 'GET',
			credentials: 'same-origin',
			headers: values ? { 'X-CSRFToken': getCookie('csrftoken') } : {},
			body: values ? new URLSearchParams(values) : undefined,
		});
		if (response.status === 401) {
			if (values) window.location.assign(loginUrl);
			return null;
		}
		const data = await response.json();
		if (!response.ok) {
			throw new Error(data.error || 'The cart could not be updated.');
		}
		return data;
	}

	async function refreshCart() {
		try {
			const data = await sendCartRequest();
			if (data) updateCart(data);
		} catch (error) {
			emptyElement.textContent = error.message;
		}
	}

	async function addProduct(button) {
		const card = button.closest('.delivery-card, .offer-card');
		const nameElement = card && card.querySelector('h3, h2');
		if (!nameElement || !categoryElement) return;

		button.disabled = true;
		try {
			const data = await sendCartRequest({
				name: nameElement.textContent.trim(),
				category: categoryElement.dataset.cartCategory,
			});
			if (!data) return;
			updateCart(data);
			button.classList.add('action-complete');
			if (button.dataset.action === 'buy') setPanelOpen(true);
			window.setTimeout(function () {
				button.classList.remove('action-complete');
			}, 900);
		} catch (error) {
			emptyElement.textContent = error.message;
			setPanelOpen(true);
		} finally {
			button.disabled = false;
		}
	}

	async function removeCartItem(button) {
		try {
			const data = await sendCartRequest({
				action: 'remove',
				item_id: button.dataset.cartItemId,
			});
			if (data) updateCart(data);
		} catch (error) {
			emptyElement.textContent = error.message;
		}
	}

	document.addEventListener('click', function (event) {
		const addButton = event.target.closest('[data-action="add"], [data-action="buy"]');
		if (addButton) {
			event.preventDefault();
			event.stopImmediatePropagation();
			addProduct(addButton);
			return;
		}

		const removeButton = event.target.closest('[data-cart-item-id]');
		if (removeButton) {
			event.preventDefault();
			event.stopImmediatePropagation();
			removeCartItem(removeButton);
			return;
		}

		if (cartButton && cartButton.contains(event.target)) {
			event.preventDefault();
			event.stopImmediatePropagation();
			setPanelOpen(cartPanel.hidden);
			return;
		}

		if (closeButton && closeButton.contains(event.target)) {
			event.preventDefault();
			event.stopImmediatePropagation();
			setPanelOpen(false);
			return;
		}

		if (!cartPanel.hidden && !cartPanel.contains(event.target)) setPanelOpen(false);
	}, true);

	refreshCart();
})();