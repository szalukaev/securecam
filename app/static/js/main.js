/* ═══════════════════════════════════════════════════
   SECURECAM — Main JavaScript
═══════════════════════════════════════════════════ */

// ─── Cart Store ───────────────────────────────────
function cartStore() {
  return {
    items: [],
    open: false,
    openOrder: false,
    orderDone: false,
    loading: false,
    orderError: '',
    orderForm: { name: '', phone: '', email: '', comment: '' },

    get count() { return this.items.reduce((s, i) => s + i.qty, 0); },
    get total() { return this.items.reduce((s, i) => s + i.price * i.qty, 0); },

    load() {
      try {
        const saved = sessionStorage.getItem('sc_cart');
        if (saved) this.items = JSON.parse(saved);
      } catch {}
      wishlistStore.load();
      compareStore.load();
    },
    save() {
      try { sessionStorage.setItem('sc_cart', JSON.stringify(this.items)); } catch {}
    },
    add(product) {
      const existing = this.items.find(i => i.id === product.id);
      if (existing) { existing.qty++; } else { this.items.push({ ...product, qty: 1 }); }
      this.save();
      showToast(`${product.name} добавлен в корзину`, 'cart', product);
    },
    remove(index) { this.items.splice(index, 1); this.save(); },
    changeQty(index, delta) {
      const item = this.items[index];
      if (!item) return;
      item.qty = Math.max(1, item.qty + delta);
      this.save();
    },
    clear() { this.items = []; this.save(); },

    async submitOrder() {
      if (!this.orderForm.name || !this.orderForm.phone) {
        this.orderError = 'Пожалуйста, укажите имя и телефон';
        return;
      }
      this.loading = true;
      this.orderError = '';
      try {
        const res = await fetch('/api/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            customer_name: this.orderForm.name,
            customer_phone: this.orderForm.phone,
            customer_email: this.orderForm.email,
            comment: this.orderForm.comment,
            items: this.items,
          }),
        });
        const data = await res.json();
        if (data.ok) { this.orderDone = true; this.clear(); }
        else { this.orderError = data.detail || 'Ошибка отправки заказа'; }
      } catch { this.orderError = 'Ошибка соединения. Попробуйте позже.'; }
      finally { this.loading = false; }
    },
  };
}

// ─── Wishlist Store ───────────────────────────────
const wishlistStore = {
  items: [],
  load() {
    try { this.items = JSON.parse(sessionStorage.getItem('sc_wish') || '[]'); } catch {}
  },
  save() {
    try { sessionStorage.setItem('sc_wish', JSON.stringify(this.items)); } catch {}
  },
  toggle(product) {
    const idx = this.items.findIndex(i => i.id === product.id);
    if (idx >= 0) {
      this.items.splice(idx, 1);
      showToast(`${product.name} удалён из избранного`, 'info');
    } else {
      this.items.push(product);
      showToast(`${product.name} добавлен в избранное`, 'wish');
    }
    this.save();
    this._notify();
  },
  has(id) { return this.items.some(i => i.id === id); },
  get count() { return this.items.length; },
  _notify() { document.dispatchEvent(new CustomEvent('wishlist-updated')); },
};

// ─── Compare Store ────────────────────────────────
const compareStore = {
  items: [],
  load() {
    try { this.items = JSON.parse(sessionStorage.getItem('sc_compare') || '[]'); } catch {}
  },
  save() {
    try { sessionStorage.setItem('sc_compare', JSON.stringify(this.items)); } catch {}
  },
  toggle(product) {
    const idx = this.items.findIndex(i => i.id === product.id);
    if (idx >= 0) {
      this.items.splice(idx, 1);
      showToast(`${product.name} удалён из сравнения`, 'info');
    } else {
      if (this.items.length >= 4) {
        showToast('Можно сравнивать не более 4 товаров', 'warn');
        return;
      }
      this.items.push(product);
      showToast(`${product.name} добавлен к сравнению`, 'compare');
    }
    this.save();
    this._notify();
  },
  has(id) { return this.items.some(i => i.id === id); },
  get count() { return this.items.length; },
  _notify() { document.dispatchEvent(new CustomEvent('compare-updated')); },
};

// ─── Toast уведомления ────────────────────────────
function showToast(msg, type = 'success', product = null) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `sc-toast sc-toast-${type}`;

  let extra = '';
  if (type === 'cart' && product) {
    extra = `<a href="#" class="sc-toast-btn" onclick="document.body._x_dataStack[0].cart.open=true;this.closest('.sc-toast').remove();return false">Перейти в корзину</a>`;
  } else if (type === 'wish') {
    extra = `<a href="/wishlist" class="sc-toast-btn">Избранное</a>`;
  } else if (type === 'compare') {
    extra = `<a href="/compare" class="sc-toast-btn">Сравнить</a>`;
  }

  const icons = {
    cart: '🛒', wish: '❤️', compare: '⚖️', info: 'ℹ️', warn: '⚠️', success: '✓'
  };

  toast.innerHTML = `
    <div class="sc-toast-content">
      <span class="sc-toast-icon">${icons[type] || '✓'}</span>
      <span class="sc-toast-msg">${msg}</span>
    </div>
    ${extra}
    <button class="sc-toast-close" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('visible'));

  setTimeout(() => {
    toast.classList.remove('visible');
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}

// ─── Catalog view toggle ──────────────────────────
// ИСПРАВЛЕНО: применяем только к grid-у без атрибута data-fixed-view
// Гриды с id="home-featured-grid" или data-view уже заданным хардкодом — не трогаем

function initCatalogView() {
  const savedView = sessionStorage.getItem('catalog_view') || 'list';

  // Применяем только к каталожным гридам (не к главной)
  setCatalogView(savedView, false);

  document.querySelectorAll('[data-view-toggle]').forEach(btn => {
    btn.addEventListener('click', () => {
      const v = btn.dataset.viewToggle;
      setCatalogView(v, true);
    });
  });
}

function setCatalogView(view, save) {
  // Берём все грид-контейнеры БЕЗ фиксированного вида (без data-fixed)
  const grids = document.querySelectorAll('.products-grid:not([data-fixed])');
  grids.forEach(grid => {
    grid.dataset.view = view;
  });

  // Кнопки переключения
  document.querySelectorAll('[data-view-toggle]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.viewToggle === view);
  });

  if (save) sessionStorage.setItem('catalog_view', view);
}

// ─── Wishlist/Compare счётчики ────────────────────
function updateNavCounters() {
  const wc = document.getElementById('wishlist-count');
  const cc = document.getElementById('compare-count');
  if (wc) {
    wc.textContent = wishlistStore.count;
    wc.style.display = wishlistStore.count > 0 ? 'flex' : 'none';
  }
  if (cc) {
    cc.textContent = compareStore.count;
    cc.style.display = compareStore.count > 0 ? 'flex' : 'none';
  }
}

document.addEventListener('wishlist-updated', updateNavCounters);
document.addEventListener('compare-updated', updateNavCounters);

// ─── Gallery & Tabs ───────────────────────────────
function initGallery() {
  const thumbs = document.querySelectorAll('.gallery-thumb');
  const main = document.querySelector('.gallery-main img');
  if (!thumbs.length || !main) return;
  thumbs.forEach(thumb => {
    thumb.addEventListener('click', () => {
      thumbs.forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
      main.src = thumb.querySelector('img').src;
    });
  });
}

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.hidden = true);
      btn.classList.add('active');
      const pane = document.getElementById(target);
      if (pane) pane.hidden = false;
    });
  });
}

function formatPrice(n) {
  return Math.round(n).toLocaleString('ru-RU');
}

document.addEventListener('DOMContentLoaded', () => {
  initGallery();
  initTabs();
  initCatalogView();
  updateNavCounters();
});

// ─── Helpers ──────────────────────────────────────
function toggleSearch() {
  const bar = document.getElementById('search-bar');
  bar.classList.toggle('active');
  if (bar.classList.contains('active')) bar.querySelector('input').focus();
}
function toggleNav() {
  document.getElementById('main-nav').classList.toggle('open');
}
window.addEventListener('scroll', () => {
  document.getElementById('header').classList.toggle('sticky', window.scrollY > 60);
});