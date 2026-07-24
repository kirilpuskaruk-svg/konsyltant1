let tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) {
  tg.expand();
  tg.ready();
}

let products = [];
let cart = {}; // product_id -> quantity
let appliedPromo = null;
let discountPercent = 0;
let userBonuses = 0;
let activeCategory = "all";
let currentOfferProduct = null;

const user_id = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : "123456";
const user_name = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? (tg.initDataUnsafe.user.first_name + ' ' + (tg.initDataUnsafe.user.last_name || '')).trim() : "Клієнт";

// Init App
document.addEventListener("DOMContentLoaded", () => {
  fetchCategories();
  fetchProducts();
  fetchUserBonuses();

  // Search
  document.getElementById("searchInput").addEventListener("input", filterAndRenderProducts);

  // Category filter & Drag / Wheel Scroll
  const catContainer = document.getElementById("categoriesContainer");
  if (catContainer) {
    let isDown = false;
    let startX;
    let scrollLeft;

    catContainer.addEventListener('mousedown', (e) => {
      isDown = true;
      startX = e.pageX - catContainer.offsetLeft;
      scrollLeft = catContainer.scrollLeft;
    });

    catContainer.addEventListener('mouseleave', () => {
      isDown = false;
      catContainer.classList.remove('active-grab');
    });

    catContainer.addEventListener('mouseup', () => {
      isDown = false;
      catContainer.classList.remove('active-grab');
    });

    catContainer.addEventListener('mousemove', (e) => {
      if (!isDown) return;
      const x = e.pageX - catContainer.offsetLeft;
      const walk = (x - startX) * 2;
      if (Math.abs(walk) > 5) {
        catContainer.classList.add('active-grab');
        catContainer.scrollLeft = scrollLeft - walk;
      }
    });

    catContainer.addEventListener('wheel', (e) => {
      if (e.deltaY !== 0) {
        catContainer.scrollLeft += e.deltaY;
      }
    }, { passive: true });

    initCategoryButtons(catContainer);
  }

  // Modal open / close
  document.getElementById("btnOpenCheckout").addEventListener("click", openCheckoutModal);
  document.getElementById("btnCloseModal").addEventListener("click", closeCheckoutModal);

  // Offer modal close
  document.getElementById("btnCloseOfferModal").addEventListener("click", closeOfferModal);
  document.getElementById("btnSubmitOffer").addEventListener("click", submitOffer);

  // Promo code
  document.getElementById("btnApplyPromo").addEventListener("click", applyPromoCode);

  // Form submit
  document.getElementById("orderForm").addEventListener("submit", submitOrder);

  // Prefill user name if available
  if (user_name) {
    document.getElementById("orderName").value = user_name;
  }
});

async function fetchProducts() {
  try {
    const res = await fetch("/api/products");
    products = await res.json();
    filterAndRenderProducts();
  } catch (err) {
    console.error("Error fetching products:", err);
  }
}

async function fetchUserBonuses() {
  try {
    const res = await fetch(`/api/user_bonuses?user_id=${user_id}`);
    const data = await res.json();
    userBonuses = data.bonuses || 0;
    document.getElementById("userBonusesCount").innerText = userBonuses;
    document.getElementById("availBonuses").innerText = userBonuses;
  } catch (err) {
    console.error("Error fetching bonuses:", err);
  }
}

function initCategoryButtons(container) {
  if (!container) return;
  container.querySelectorAll(".cat-chip").forEach(chip => {
    chip.onclick = (e) => {
      e.stopPropagation();
      container.querySelectorAll(".cat-chip").forEach(c => c.classList.remove("active"));
      const target = e.currentTarget;
      target.classList.add("active");
      activeCategory = target.dataset.cat || "all";
      filterAndRenderProducts();
    };
  });
}

async function fetchCategories() {
  try {
    const res = await fetch('/api/categories');
    const cats = await res.json();
    const container = document.getElementById("categoriesContainer");
    if (!container || !Array.isArray(cats)) return;

    container.innerHTML = `<button class="cat-chip ${activeCategory === 'all' ? 'active' : ''}" data-cat="all">Всі</button>`;
    cats.forEach(cat => {
      let emoji = "📦";
      if (cat.includes("Фігур")) emoji = "🧸";
      else if (cat.includes("Одяг") || cat.includes("Мерч")) emoji = "👕";
      else if (cat.includes("Колекційн")) emoji = "✨";

      const btn = document.createElement("button");
      btn.className = `cat-chip ${activeCategory === cat ? 'active' : ''}`;
      btn.dataset.cat = cat;
      btn.innerHTML = `${emoji} ${cat}`;
      container.appendChild(btn);
    });

    initCategoryButtons(container);
  } catch (err) {
    console.error("Error fetching categories:", err);
  }
}

function filterAndRenderProducts() {
  const searchTerm = document.getElementById("searchInput").value.toLowerCase();
  const grid = document.getElementById("productsGrid");
  grid.innerHTML = "";

  const filtered = products.filter(p => {
    const matchesCat = activeCategory === "all" || p.category === activeCategory;
    const matchesSearch = p.name.toLowerCase().includes(searchTerm) || p.description.toLowerCase().includes(searchTerm);
    return matchesCat && matchesSearch;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="empty-products"><p>На жаль, товарів не знайдено 🛍️</p></div>`;
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement("div");
    card.className = "product-card";

    const qtyInCart = cart[p.id] || 0;
    const conditionBadge = p.condition ? `<span class="condition-badge">✨ ${p.condition}</span>` : "";
    const videoBtn = p.video_url ? `<a href="${p.video_url}" target="_blank" class="btn-video-link">🎥 Огляд</a>` : "";

    card.innerHTML = `
      <div class="product-img-wrapper">
        <img src="${p.image_url}" alt="${p.name}" class="product-img" loading="lazy">
        <div class="rating-chip">★ ${p.rating || 5.0}</div>
        ${conditionBadge}
      </div>
      <div class="product-info">
        <h3 class="product-title">${p.name}</h3>
        <p class="product-desc">${p.description}</p>
        <div class="product-actions-bar">
          <div class="price-tag">${p.price} ₴</div>
          ${videoBtn}
        </div>
        <div class="card-buttons-row">
          <button class="btn-offer" onclick="openOfferModal(${p.id})">🤝 Торг</button>
          ${qtyInCart === 0 ? `
            <button class="btn-add-cart" onclick="addToCart(${p.id})">+ Додати</button>
          ` : `
            <div class="qty-controls">
              <button onclick="changeQty(${p.id}, -1)">-</button>
              <span>${qtyInCart}</span>
              <button onclick="changeQty(${p.id}, 1)">+</button>
            </div>
          `}
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function addToCart(productId) {
  cart[productId] = (cart[productId] || 0) + 1;
  updateCartUI();
  filterAndRenderProducts();
}

function changeQty(productId, delta) {
  if (!cart[productId]) return;
  cart[productId] += delta;
  if (cart[productId] <= 0) {
    delete cart[productId];
  }
  updateCartUI();
  filterAndRenderProducts();
}

function updateCartUI() {
  const floatingBar = document.getElementById("cartFloatingBar");
  let totalCount = 0;
  let totalPrice = 0;

  for (let id in cart) {
    const count = cart[id];
    const product = products.find(p => p.id == id);
    if (product) {
      totalCount += count;
      totalPrice += product.price * count;
    }
  }

  if (totalCount > 0) {
    floatingBar.classList.remove("hidden");
    document.getElementById("cartItemCount").innerText = totalCount;
    document.getElementById("cartTotalPrice").innerText = totalPrice + " ₴";
  } else {
    floatingBar.classList.add("hidden");
  }
}

// MAKE OFFER MODAL
function openOfferModal(productId) {
  currentOfferProduct = products.find(p => p.id == productId);
  if (!currentOfferProduct) return;

  document.getElementById("offerProductName").innerText = currentOfferProduct.name;
  document.getElementById("offerOrigPrice").innerText = currentOfferProduct.price;
  document.getElementById("offerPriceInput").value = "";
  document.getElementById("offerStatusMsg").innerText = "";
  document.getElementById("offerModal").classList.remove("hidden");
}

function closeOfferModal() {
  document.getElementById("offerModal").classList.add("hidden");
}

async function submitOffer() {
  const priceVal = parseFloat(document.getElementById("offerPriceInput").value);
  if (!priceVal || priceVal <= 0) {
    document.getElementById("offerStatusMsg").innerText = "⚠️ Введіть коректну ціну!";
    return;
  }

  try {
    const res = await fetch("/api/make_offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: user_id,
        product_id: currentOfferProduct.id,
        offered_price: priceVal
      })
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById("offerStatusMsg").innerText = "🎉 Пропозицію надіслано продавцю!";
      setTimeout(closeOfferModal, 1800);
    } else {
      document.getElementById("offerStatusMsg").innerText = "❌ Помилка: " + data.error;
    }
  } catch (err) {
    document.getElementById("offerStatusMsg").innerText = "❌ Помилка з'єднання.";
  }
}

// CHECKOUT MODAL
function openCheckoutModal() {
  renderModalCartItems();
  recalculateTotals();
  document.getElementById("checkoutModal").classList.remove("hidden");
}

function closeCheckoutModal() {
  document.getElementById("checkoutModal").classList.add("hidden");
}

function renderModalCartItems() {
  const container = document.getElementById("modalCartItems");
  container.innerHTML = "";

  for (let id in cart) {
    const count = cart[id];
    const product = products.find(p => p.id == id);
    if (!product) continue;

    const row = document.createElement("div");
    row.className = "cart-item-row";
    row.innerHTML = `
      <img src="${product.image_url}" class="cart-item-thumb" />
      <div class="cart-item-info">
        <div class="cart-item-title">${product.name}</div>
        <div class="cart-item-subtotal">${count} x ${product.price} ₴ = ${count * product.price} ₴</div>
      </div>
      <div class="cart-item-qty">
        <button onclick="changeQty(${product.id}, -1); renderModalCartItems(); recalculateTotals();">-</button>
        <span>${count}</span>
        <button onclick="changeQty(${product.id}, 1); renderModalCartItems(); recalculateTotals();">+</button>
      </div>
    `;
    container.appendChild(row);
  }
}

function recalculateTotals() {
  let subtotal = 0;
  for (let id in cart) {
    const count = cart[id];
    const product = products.find(p => p.id == id);
    if (product) {
      subtotal += product.price * count;
    }
  }

  let discount = 0;
  if (discountPercent > 0) {
    discount += subtotal * (discountPercent / 100);
  }

  const useBonuses = document.getElementById("useBonusesCheckbox").checked;
  if (useBonuses) {
    discount += Math.min(subtotal - discount, userBonuses);
  }

  const finalTotal = Math.max(0, subtotal - discount);

  document.getElementById("summarySubtotal").innerText = subtotal + " ₴";
  document.getElementById("summaryFinalTotal").innerText = finalTotal.toFixed(1) + " ₴";

  const discountRow = document.getElementById("discountRow");
  if (discount > 0) {
    discountRow.style.display = "flex";
    document.getElementById("summaryDiscount").innerText = "- " + discount.toFixed(1) + " ₴";
  } else {
    discountRow.style.display = "none";
  }
}

async function applyPromoCode() {
  const code = document.getElementById("promoInput").value.trim();
  const msgEl = document.getElementById("promoMessage");
  if (!code) return;

  try {
    const res = await fetch("/api/validate_promo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code })
    });
    const data = await res.json();
    if (data.valid) {
      discountPercent = data.discount_percent;
      appliedPromo = code;
      msgEl.className = "promo-message success";
      msgEl.innerText = `🎉 Промокод активовано! Знижка ${discountPercent}%`;
      recalculateTotals();
    } else {
      msgEl.className = "promo-message error";
      msgEl.innerText = `❌ ${data.message}`;
    }
  } catch (err) {
    msgEl.className = "promo-message error";
    msgEl.innerText = "❌ Помилка перевірки промокоду.";
  }
}

async function submitOrder(e) {
  e.preventDefault();

  const btn = document.getElementById("btnConfirmOrder");
  btn.disabled = true;
  btn.innerText = "Обробка...";

  const name = document.getElementById("orderName").value;
  const phone = document.getElementById("orderPhone").value;
  const address = document.getElementById("orderAddress").value;
  const use_bonuses = document.getElementById("useBonusesCheckbox").checked;

  let items = [];
  for (let id in cart) {
    const count = cart[id];
    const p = products.find(prod => prod.id == id);
    if (p) {
      items.push({ product_id: p.id, name: p.name, quantity: count, price: p.price, subtotal: count * p.price });
    }
  }

  try {
    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id,
        name,
        phone,
        address,
        items,
        promo_code: appliedPromo,
        use_bonuses
      })
    });
    const data = await res.json();
    if (data.success) {
      closeCheckoutModal();
      cart = {};
      updateCartUI();
      if (tg) {
        tg.showAlert(`🎉 Дякуємо! Замовлення №${data.order_id} успішно створено!`);
        tg.close();
      } else {
        alert(`🎉 Замовлення №${data.order_id} успішно створено!`);
      }
    } else {
      alert("❌ Помилка створення замовлення: " + data.error);
    }
  } catch (err) {
    alert("❌ Помилка підключення до сервера.");
  } finally {
    btn.disabled = false;
    btn.innerText = "Підтвердити замовлення 🎉";
  }
}
