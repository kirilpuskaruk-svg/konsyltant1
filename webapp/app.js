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

const user_id = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : "123456";
const user_name = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? (tg.initDataUnsafe.user.first_name + ' ' + (tg.initDataUnsafe.user.last_name || '')).trim() : "Клієнт";

// Init App
document.addEventListener("DOMContentLoaded", () => {
  fetchProducts();
  fetchUserBonuses();

  // Search
  document.getElementById("searchInput").addEventListener("input", filterAndRenderProducts);

  // Category filter
  document.querySelectorAll(".cat-chip").forEach(chip => {
    chip.addEventListener("click", (e) => {
      document.querySelectorAll(".cat-chip").forEach(c => c.classList.remove("active"));
      e.target.classList.add("active");
      activeCategory = e.target.dataset.cat;
      filterAndRenderProducts();
    });
  });

  // Modal open / close
  document.getElementById("btnOpenCheckout").addEventListener("click", openCheckoutModal);
  document.getElementById("btnCloseModal").addEventListener("click", closeCheckoutModal);

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
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 40px; color: #94a3b8;">Печива не знайдено 🍪</div>`;
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement("div");
    card.className = "product-card";
    const imgUrl = p.image_url || "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=600&q=80";

    card.innerHTML = `
      <div class="product-img-wrapper">
        <img src="${imgUrl}" alt="${p.name}" />
        <span class="product-rating">⭐ ${p.rating || '4.9'}</span>
      </div>
      <div class="product-details">
        <h3 class="product-name">${p.name}</h3>
        <p class="product-desc">${p.description}</p>
        <div class="product-footer">
          <span class="product-price">${p.price} ₴</span>
          <button class="btn-add-cart" onclick="addToCart(${p.id})">+ Додати</button>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function addToCart(productId) {
  cart[productId] = (cart[productId] || 0) + 1;
  updateCartBar();
  if (tg && tg.HapticFeedback) {
    tg.HapticFeedback.impactOccurred('light');
  }
}

function removeFromCart(productId) {
  if (cart[productId]) {
    cart[productId]--;
    if (cart[productId] <= 0) {
      delete cart[productId];
    }
  }
  updateCartBar();
  renderModalItems();
}

function updateCartBar() {
  const totalCount = Object.values(cart).reduce((a, b) => a + b, 0);
  let totalPrice = 0;

  for (let pid in cart) {
    const p = products.find(prod => prod.id == pid);
    if (p) {
      totalPrice += p.price * cart[pid];
    }
  }

  const bar = document.getElementById("cartFloatingBar");
  if (totalCount > 0) {
    bar.classList.remove("hidden");
    document.getElementById("cartItemCount").innerText = `${totalCount} шт`;
    document.getElementById("cartTotalPrice").innerText = `${totalPrice} ₴`;
  } else {
    bar.classList.add("hidden");
  }
}

function openCheckoutModal() {
  renderModalItems();
  document.getElementById("checkoutModal").classList.remove("hidden");
}

function closeCheckoutModal() {
  document.getElementById("checkoutModal").classList.add("hidden");
}

function renderModalItems() {
  const container = document.getElementById("modalCartItems");
  container.innerHTML = "";

  let subtotal = 0;

  for (let pid in cart) {
    const p = products.find(prod => prod.id == pid);
    if (!p) continue;
    const qty = cart[pid];
    const itemSubtotal = p.price * qty;
    subtotal += itemSubtotal;

    const div = document.createElement("div");
    div.className = "modal-cart-item";
    div.innerHTML = `
      <div>
        <strong>${p.name}</strong><br>
        <span style="font-size:12px; color:#94a3b8">${p.price} ₴ x ${qty}</span>
      </div>
      <div class="item-qty-controls">
        <button class="btn-qty" onclick="removeFromCart(${p.id})">-</button>
        <span>${qty}</span>
        <button class="btn-qty" onclick="addToCart(${p.id})">+</button>
      </div>
    `;
    container.appendChild(div);
  }

  calculateTotals(subtotal);
}

function calculateTotals(subtotal) {
  let discount = 0;
  if (discountPercent > 0) {
    discount = (subtotal * discountPercent) / 100;
  }

  let useBonus = document.getElementById("useBonusesCheckbox").checked;
  let bonusDeduction = 0;
  if (useBonus && userBonuses > 0) {
    const remainingAfterDiscount = subtotal - discount;
    bonusDeduction = Math.min(userBonuses, remainingAfterDiscount);
  }

  const totalDiscount = discount + bonusDeduction;
  const finalTotal = Math.max(0, subtotal - totalDiscount);

  document.getElementById("summarySubtotal").innerText = `${subtotal} ₴`;
  const discRow = document.getElementById("discountRow");
  if (totalDiscount > 0) {
    discRow.style.display = "flex";
    document.getElementById("summaryDiscount").innerText = `-${totalDiscount.toFixed(1)} ₴`;
  } else {
    discRow.style.display = "none";
  }
  document.getElementById("summaryFinalTotal").innerText = `${finalTotal.toFixed(1)} ₴`;
}

document.getElementById("useBonusesCheckbox").addEventListener("change", () => {
  renderModalItems();
});

async function applyPromoCode() {
  const promoText = document.getElementById("promoInput").value.trim().toUpperCase();
  const msgDiv = document.getElementById("promoMessage");

  if (!promoText) return;

  try {
    const res = await fetch("/api/validate_promo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ promo: promoText })
    });
    const data = await res.json();

    if (data.valid) {
      discountPercent = data.discount_percent;
      appliedPromo = promoText;
      msgDiv.style.color = "#2ec4b6";
      msgDiv.innerText = `✅ Промокод застосовано! Знижка ${discountPercent}%`;
      renderModalItems();
    } else {
      msgDiv.style.color = "#e71d36";
      msgDiv.innerText = `❌ Недійсний промокод`;
    }
  } catch (err) {
    console.error("Error applying promo:", err);
  }
}

async function submitOrder(e) {
  e.preventDefault();

  const items = [];
  for (let pid in cart) {
    const p = products.find(prod => prod.id == pid);
    if (p) {
      items.push({
        product_id: p.id,
        name: p.name,
        price: p.price,
        quantity: cart[pid],
        subtotal: p.price * cart[pid]
      });
    }
  }

  if (items.length === 0) {
    alert("Ваш кошик порожній!");
    return;
  }

  const name = document.getElementById("orderName").value.trim();
  const phone = document.getElementById("orderPhone").value.trim();
  const address = document.getElementById("orderAddress").value.trim();
  const useBonus = document.getElementById("useBonusesCheckbox").checked;

  const orderPayload = {
    user_id: user_id,
    name: name,
    phone: phone,
    address: address,
    items: items,
    promo_code: appliedPromo,
    use_bonuses: useBonus
  };

  try {
    const res = await fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(orderPayload)
    });
    const result = await res.json();

    if (result.success) {
      if (tg) {
        tg.showAlert(`🎉 Дякуємо, ${name}! Замовлення #${result.order_id} успішно прийнято!`);
        tg.close();
      } else {
        alert(`🎉 Дякуємо, ${name}! Замовлення #${result.order_id} успішно прийнято!`);
        location.reload();
      }
    } else {
      alert("Помилка при створенні замовлення.");
    }
  } catch (err) {
    console.error("Error submitting order:", err);
    alert("Помилка зв'язку з сервером.");
  }
}
