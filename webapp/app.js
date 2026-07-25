let tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) {
  tg.expand();
  tg.ready();
}

let products = [];
let cart = {}; // product_id -> quantity
let wishlist = JSON.parse(localStorage.getItem("wishlist") || "[]"); // array of product_ids
let currentLang = localStorage.getItem("app_lang") || "ua";
let appliedPromo = null;
let discountPercent = 0;
let userBonuses = 0;
let activeCategory = "all";

const user_id = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? tg.initDataUnsafe.user.id : "123456";
const user_name = tg && tg.initDataUnsafe && tg.initDataUnsafe.user ? (tg.initDataUnsafe.user.first_name + ' ' + (tg.initDataUnsafe.user.last_name || '')).trim() : "Клієнт";

// --- i18n Translations ---
const translations = {
  ua: {
    subtitle: "Особисті речі, фігурки та колекційки",
    search_placeholder: "🔍 Пошук речей та фігурок...",
    btn_gift_finder: "Підбір подарунка",
    cat_all: "Всі",
    cat_wishlist: "Обране",
    cat_figures: "Фігурки",
    cat_clothing: "Одяг та Мерч",
    cat_collectibles: "Колекційне",
    btn_view_cart: "Переглянути кошик 🛒",
    checkout_title: "Оформлення Замовлення 📝",
    promo_placeholder: "Промокод (наприклад: YARIK20)",
    btn_apply: "Застосувати",
    use_cashback: "Використати накопичений кешбек",
    label_name: "Ваше ПІБ / Ім'я:",
    ph_name: "Олександр Петренко",
    label_phone: "Номер телефону:",
    np_city_label: "Нова Пошта — Населений пункт:",
    np_city_ph: "Почніть вводити місто (наприклад: Київ, Львів...)",
    np_warehouse_label: "Відділення або Поштомат №:",
    np_warehouse_ph: "Введіть № або адресу відділення...",
    sum_products: "Товари:",
    sum_discount: "Знижка / Бонуси:",
    sum_total: "Разом до сплати:",
    btn_confirm_order: "Підтвердити замовлення 🎉",
    gift_modal_title: "AI-Підбір Подарунка",
    gift_for_who: "Кому шукаєте подарунок?",
    gift_interests: "Які інтереси?",
    gift_budget: "Орієнтовний бюджет?",
    btn_find_gifts: "Знайти ідеальні подарунки 🚀",
    gift_found: "Рекомендовано AI:",
    flash_ends_in: "До кінця знижки:"
  },
  en: {
    subtitle: "Personal items, figures & collectibles",
    search_placeholder: "🔍 Search items & figures...",
    btn_gift_finder: "Gift Finder",
    cat_all: "All",
    cat_wishlist: "Wishlist",
    cat_figures: "Figures",
    cat_clothing: "Clothing & Merch",
    cat_collectibles: "Collectibles",
    btn_view_cart: "View Cart 🛒",
    checkout_title: "Checkout Order 📝",
    promo_placeholder: "Promo code (e.g. YARIK20)",
    btn_apply: "Apply",
    use_cashback: "Use accumulated cashback",
    label_name: "Full Name:",
    ph_name: "Alex Petrenko",
    label_phone: "Phone Number:",
    np_city_label: "Nova Poshta — City/Settlement:",
    np_city_ph: "Type a city (e.g. Kyiv, Lviv...)",
    np_warehouse_label: "Branch or Postomat #:",
    np_warehouse_ph: "Type branch number or address...",
    sum_products: "Items:",
    sum_discount: "Discount / Bonuses:",
    sum_total: "Total Amount:",
    btn_confirm_order: "Confirm Order 🎉",
    gift_modal_title: "AI Gift Assistant",
    gift_for_who: "Who is the gift for?",
    gift_interests: "What are their interests?",
    gift_budget: "Estimated budget?",
    btn_find_gifts: "Find Perfect Gifts 🚀",
    gift_found: "AI Recommended:",
    flash_ends_in: "Sale ends in:"
  }
};

function t(key) {
  return (translations[currentLang] && translations[currentLang][key]) || key;
}

function updateLanguageUI() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (translations[currentLang][key]) {
      el.innerText = translations[currentLang][key];
    }
  });
  document.querySelectorAll("[data-i18n-ph]").forEach(el => {
    const key = el.getAttribute("data-i18n-ph");
    if (translations[currentLang][key]) {
      el.placeholder = translations[currentLang][key];
    }
  });
  document.getElementById("langToggle").innerText = currentLang === "ua" ? "🇺🇦 UA" : "🇬🇧 EN";
}

function toggleLanguage() {
  currentLang = currentLang === "ua" ? "en" : "ua";
  localStorage.setItem("app_lang", currentLang);
  updateLanguageUI();
  filterAndRenderProducts();
}

// --- Init App ---
document.addEventListener("DOMContentLoaded", () => {
  fetchCategories();
  fetchProducts();
  fetchUserBonuses();
  updateWishlistCount();

  // Language button
  document.getElementById("langToggle").addEventListener("click", toggleLanguage);

  // Search & Mic
  document.getElementById("searchInput").addEventListener("input", filterAndRenderProducts);
  document.getElementById("btnVoiceSearch").addEventListener("click", startVoiceSearch);

  // Category filter & Drag / Wheel Scroll
  const catContainer = document.getElementById("categoriesContainer");
  if (catContainer) {
    let isDown = false;
    let startX, scrollLeft;
    catContainer.addEventListener('mousedown', (e) => {
      isDown = true;
      startX = e.pageX - catContainer.offsetLeft;
      scrollLeft = catContainer.scrollLeft;
    });
    catContainer.addEventListener('mouseleave', () => { isDown = false; catContainer.classList.remove('active-grab'); });
    catContainer.addEventListener('mouseup', () => { isDown = false; catContainer.classList.remove('active-grab'); });
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
      if (e.deltaY !== 0) catContainer.scrollLeft += e.deltaY;
    }, { passive: true });

    initCategoryButtons(catContainer);
  }

  // Modals open / close
  document.getElementById("btnOpenCheckout").addEventListener("click", openCheckoutModal);
  document.getElementById("btnCloseModal").addEventListener("click", closeCheckoutModal);

  // Gift Modal
  document.getElementById("btnOpenGiftModal").addEventListener("click", openGiftModal);
  document.getElementById("btnCloseGiftModal").addEventListener("click", closeGiftModal);
  document.getElementById("btnFindGifts").addEventListener("click", processGiftFinder);
  document.getElementById("btnBackToWizard").addEventListener("click", () => {
    document.getElementById("giftResults").classList.add("hidden");
    document.getElementById("giftStep1").classList.remove("hidden");
  });
  initWizardChips();

  // Promo code
  document.getElementById("btnApplyPromo").addEventListener("click", applyPromoCode);

  // Form submit & Nova Poshta
  document.getElementById("useBonusesCheckbox").addEventListener("change", recalculateTotals);
  document.getElementById("orderForm").addEventListener("submit", submitOrder);
  initNovaPoshtaAutocomplete();

  // Start Flash Sale Timer Interval
  setInterval(updateFlashSaleTimers, 1000);
});

// --- Wishlist Management ---
function toggleWishlist(productId) {
  const index = wishlist.indexOf(productId);
  if (index > -1) {
    wishlist.splice(index, 1);
  } else {
    wishlist.push(productId);
  }
  localStorage.setItem("wishlist", JSON.stringify(wishlist));
  updateWishlistCount();
  filterAndRenderProducts();
}

function updateWishlistCount() {
  document.getElementById("wishlistCount").innerText = wishlist.length;
}

// --- Fetch API ---
async function fetchCategories() {
  try {
    const res = await fetch("/api/categories");
    const cats = await res.json();
    renderCategories(cats);
  } catch (e) {
    console.warn("Categories fetch error", e);
  }
}

async function fetchProducts() {
  try {
    const res = await fetch("/api/products");
    products = await res.json();
    filterAndRenderProducts();
  } catch (e) {
    console.error("Products fetch error", e);
  }
}

async function fetchUserBonuses() {
  try {
    const res = await fetch(`/api/user_bonuses?user_id=${user_id}`);
    const data = await res.json();
    userBonuses = data.bonuses || 0;
    document.getElementById("userBonusesCount").innerText = userBonuses;
    document.getElementById("availBonuses").innerText = userBonuses;
  } catch (e) {
    console.warn("Bonuses fetch error", e);
  }
}

// --- Categories ---
function initCategoryButtons(container) {
  container.addEventListener("click", (e) => {
    const btn = e.target.closest(".cat-chip");
    if (!btn) return;
    container.querySelectorAll(".cat-chip").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeCategory = btn.dataset.cat;
    filterAndRenderProducts();
  });
}

function renderCategories(cats) {
  const container = document.getElementById("categoriesContainer");
  const defaultChips = `
    <button class="cat-chip ${activeCategory === 'all' ? 'active' : ''}" data-cat="all" data-i18n="cat_all">${t("cat_all")}</button>
    <button class="cat-chip ${activeCategory === 'wishlist' ? 'active' : ''}" data-cat="wishlist" id="chipWishlist">❤️ <span data-i18n="cat_wishlist">${t("cat_wishlist")}</span> (<span id="wishlistCount">${wishlist.length}</span>)</button>
  `;

  let dynamicChips = "";
  if (Array.isArray(cats)) {
    dynamicChips = cats.map(c => {
      const name = typeof c === 'string' ? c : c.name;
      const icon = typeof c === 'object' && c.icon ? c.icon : '✨';
      return `<button class="cat-chip ${activeCategory === name ? 'active' : ''}" data-cat="${name}">${icon} ${name}</button>`;
    }).join("");
  }

  container.innerHTML = defaultChips + dynamicChips;
}

// --- Render Products ---
function filterAndRenderProducts() {
  const query = document.getElementById("searchInput").value.toLowerCase().trim();
  const grid = document.getElementById("productsGrid");
  grid.innerHTML = "";

  const filtered = products.filter(p => {
    const matchesCat = (activeCategory === "all") ||
                       (activeCategory === "wishlist" && wishlist.includes(p.id)) ||
                       (p.category === activeCategory);
    const matchesSearch = p.name.toLowerCase().includes(query) || p.description.toLowerCase().includes(query);
    return matchesCat && matchesSearch;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px 10px; color: var(--text-muted);">
      🔍 ${currentLang === 'ua' ? 'Товарів не знайдено' : 'No items found'}
    </div>`;
    return;
  }

  filtered.forEach(p => {
    const isWish = wishlist.includes(p.id);
    const qtyInCart = cart[p.id] || 0;

    let flashBadge = "";
    let finalPrice = p.price;
    if (p.flash_sale) {
      const disc = p.flash_sale.discount_percent || 15;
      finalPrice = Math.round(p.price * (1 - disc / 100));
      flashBadge = `<div class="flash-sale-badge">⚡ -${disc}% <span class="flash-timer" data-hours="${p.flash_sale.hours_left || 12}"></span></div>`;
    }

    const card = document.createElement("div");
    card.className = "product-card";
    card.innerHTML = `
      <div class="product-img-wrapper">
        <button class="btn-wishlist-heart ${isWish ? 'active' : ''}" onclick="toggleWishlist(${p.id})">
          ${isWish ? '❤️' : '🤍'}
        </button>
        <img src="${p.image_url}" alt="${p.name}" class="product-img" loading="lazy" />
        ${flashBadge}
        <div class="condition-badge">${p.condition || 'New'}</div>
      </div>
      <div class="product-info">
        <h3 class="product-title">${p.name}</h3>
        <p class="product-desc">${p.description}</p>
        <div class="product-actions-bar">
          <div class="price-tag">
            ${p.flash_sale ? `<span style="text-decoration:line-through; font-size:12px; color:var(--text-muted); font-weight:normal; margin-right:4px;">${p.price}₴</span>${finalPrice} ₴` : `${p.price} ₴`}
          </div>
        </div>
        <div class="card-buttons-row">
          ${qtyInCart === 0 ? `
            <button class="btn-add-cart" onclick="addToCart(${p.id})">+ ${currentLang === 'ua' ? 'Додати' : 'Add'}</button>
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

  updateFlashSaleTimers();
}

// --- Flash Sale Timers ---
function updateFlashSaleTimers() {
  const now = new Date().getTime();
  document.querySelectorAll(".flash-timer").forEach(el => {
    const hours = parseInt(el.getAttribute("data-hours") || "12");
    // Target end time anchored to standard offset
    const end = (new Date()).setHours(23, 59, 59, 0);
    const diff = end - now;

    if (diff <= 0) {
      el.innerText = "00:00:00";
      return;
    }

    const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const s = Math.floor((diff % (1000 * 60)) / 1000);

    el.innerText = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  });
}

// --- Voice Search ---
function startVoiceSearch() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert(currentLang === 'ua' ? "Голосовий пошук не підтримується цим браузером." : "Voice search is not supported by this browser.");
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = currentLang === 'ua' ? 'uk-UA' : 'en-US';
  recognition.continuous = false;

  const btnMic = document.getElementById("btnVoiceSearch");
  btnMic.classList.add("listening");

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById("searchInput").value = transcript;
    filterAndRenderProducts();
    btnMic.classList.remove("listening");
  };

  recognition.onerror = () => {
    btnMic.classList.remove("listening");
  };

  recognition.onend = () => {
    btnMic.classList.remove("listening");
  };

  recognition.start();
}

// --- Cart Actions ---
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
      const price = product.flash_sale ? Math.round(product.price * (1 - (product.flash_sale.discount_percent || 15)/100)) : product.price;
      totalCount += count;
      totalPrice += price * count;
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

// --- Nova Poshta Autocomplete ---
const npCities = ["Київ", "Харків", "Одеса", "Дніпро", "Львів", "Запоріжжя", "Кривий Ріг", "Миколаїв", "Вінниця", "Полтава", "Чернігів", "Черкаси", "Житомир", "Суми", "Хмельницький", "Чернівці", "Рівне", "Івано-Франківськ", "Тернопіль", "Ужгород", "Луцьк"];

function initNovaPoshtaAutocomplete() {
  const cityInput = document.getElementById("npCityInput");
  const cityDropdown = document.getElementById("npCityDropdown");
  const whInput = document.getElementById("npWarehouseInput");
  const whDropdown = document.getElementById("npWarehouseDropdown");

  cityInput.addEventListener("input", () => {
    const val = cityInput.value.trim().toLowerCase();
    cityDropdown.innerHTML = "";
    if (val.length < 1) {
      cityDropdown.classList.add("hidden");
      return;
    }

    const matches = npCities.filter(c => c.toLowerCase().includes(val));
    if (matches.length > 0) {
      cityDropdown.classList.remove("hidden");
      matches.forEach(city => {
        const div = document.createElement("div");
        div.className = "autocomplete-item";
        div.innerText = city;
        div.onclick = () => {
          cityInput.value = city;
          cityDropdown.classList.add("hidden");
          whInput.focus();
        };
        cityDropdown.appendChild(div);
      });
    } else {
      cityDropdown.classList.add("hidden");
    }
  });

  whInput.addEventListener("focus", () => {
    whDropdown.innerHTML = "";
    whDropdown.classList.remove("hidden");
    for (let i = 1; i <= 15; i++) {
      const div = document.createElement("div");
      div.className = "autocomplete-item";
      div.innerText = `Відділення №${i}`;
      div.onclick = () => {
        whInput.value = `Відділення №${i}`;
        whDropdown.classList.add("hidden");
      };
      whDropdown.appendChild(div);
    }
    const pos = document.createElement("div");
    pos.className = "autocomplete-item";
    pos.innerText = "Поштомат №1001";
    pos.onclick = () => {
      whInput.value = "Поштомат №1001";
      whDropdown.classList.add("hidden");
    };
    whDropdown.appendChild(pos);
  });

  document.addEventListener("click", (e) => {
    if (!cityInput.contains(e.target) && !cityDropdown.contains(e.target)) {
      cityDropdown.classList.add("hidden");
    }
    if (!whInput.contains(e.target) && !whDropdown.contains(e.target)) {
      whDropdown.classList.add("hidden");
    }
  });
}

// --- AI Gift Finder Modal ---
function openGiftModal() {
  document.getElementById("giftStep1").classList.remove("hidden");
  document.getElementById("giftResults").classList.add("hidden");
  document.getElementById("giftModal").classList.remove("hidden");
}

function closeGiftModal() {
  document.getElementById("giftModal").classList.add("hidden");
}

function initWizardChips() {
  document.querySelectorAll(".wizard-options").forEach(group => {
    group.addEventListener("click", (e) => {
      const chip = e.target.closest(".wizard-chip");
      if (!chip) return;
      group.querySelectorAll(".wizard-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
    });
  });
}

function processGiftFinder() {
  document.getElementById("giftStep1").classList.add("hidden");
  document.getElementById("giftResults").classList.remove("hidden");

  const list = document.getElementById("giftProductsList");
  list.innerHTML = "";

  // Recommend 2-3 products randomly or by match
  const giftItems = products.slice(0, 3);
  giftItems.forEach(p => {
    const item = document.createElement("div");
    item.className = "cart-item-row";
    item.innerHTML = `
      <img src="${p.image_url}" class="cart-item-thumb" />
      <div class="cart-item-info">
        <div class="cart-item-title">${p.name}</div>
        <div class="cart-item-subtotal">${p.price} ₴</div>
      </div>
      <button class="btn-add-cart" onclick="addToCart(${p.id}); closeGiftModal();" style="flex:0 0 auto; padding:8px 12px;">+ Додати</button>
    `;
    list.appendChild(item);
  });
}

// --- Checkout Modal ---
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

    const price = product.flash_sale ? Math.round(product.price * (1 - (product.flash_sale.discount_percent || 15)/100)) : product.price;

    const row = document.createElement("div");
    row.className = "cart-item-row";
    row.innerHTML = `
      <img src="${product.image_url}" class="cart-item-thumb" />
      <div class="cart-item-info">
        <div class="cart-item-title">${product.name}</div>
        <div class="cart-item-subtotal">${count} x ${price} ₴ = ${count * price} ₴</div>
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
      const price = product.flash_sale ? Math.round(product.price * (1 - (product.flash_sale.discount_percent || 15)/100)) : product.price;
      subtotal += price * count;
    }
  }

  let discount = 0;
  if (discountPercent > 0) {
    discount = (subtotal * discountPercent) / 100;
  }

  const useBonuses = document.getElementById("useBonusesCheckbox").checked;
  if (useBonuses) {
    const rem = Math.max(0, subtotal - discount);
    discount += Math.min(userBonuses, rem);
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
      body: JSON.stringify({ promo: code })
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
      msgEl.innerText = `❌ ${currentLang === 'ua' ? 'Недійсний промокод' : 'Invalid promo code'}`;
    }
  } catch (err) {
    msgEl.className = "promo-message error";
    msgEl.innerText = "❌ Помилка перевірки.";
  }
}

async function submitOrder(e) {
  e.preventDefault();

  const btn = document.getElementById("btnConfirmOrder");
  btn.disabled = true;
  btn.innerText = "Обробка...";

  const name = document.getElementById("orderName").value;
  const phone = document.getElementById("orderPhone").value;
  const city = document.getElementById("npCityInput").value;
  const warehouse = document.getElementById("npWarehouseInput").value;
  const address = `${city}, ${warehouse}`;
  const use_bonuses = document.getElementById("useBonusesCheckbox").checked;

  let items = [];
  for (let id in cart) {
    const count = cart[id];
    const p = products.find(prod => prod.id == id);
    if (p) {
      const price = p.flash_sale ? Math.round(p.price * (1 - (p.flash_sale.discount_percent || 15)/100)) : p.price;
      items.push({ product_id: p.id, name: p.name, quantity: count, price: price, subtotal: count * price });
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
    btn.innerText = t("btn_confirm_order");
  }
}
