// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();

// Theme colors
document.documentElement.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
document.documentElement.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#222222');
document.documentElement.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
document.documentElement.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#2481cc');
document.documentElement.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2481cc');
document.documentElement.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');

// DOM Elements
const productsGrid = document.getElementById('products-container');
const categoryNav = document.getElementById('category-nav');
const productModal = document.getElementById('product-modal');
const cartModal = document.getElementById('cart-modal');
const cartButton = document.getElementById('cart-icon');
const cartCount = document.querySelector('.cart-count');
const cartItems = document.getElementById('cart-items');
const totalPrice = document.getElementById('cart-total-amount');
const checkoutBtn = document.getElementById('checkout-btn');
const closeModalButtons = document.querySelectorAll('.close-modal');

// Cart data
let cart = [];
let products = [];
let categories = [];

// Fetch products from API
async function fetchProducts() {
    try {
        productsGrid.innerHTML = '<div class="loading">Loading products...</div>';
        
        const response = await fetch('/api/products');
        products = await response.json();
        
        displayProducts('all');
    } catch (error) {
        productsGrid.innerHTML = '<div class="loading">Error loading products. Please try again.</div>';
        console.error('Error fetching products:', error);
    }
}

// Fetch categories from API
async function fetchCategories() {
    try {
        const response = await fetch('/api/categories');
        categories = await response.json();
        
        // Add "All" category
        categoryNav.innerHTML = `<button class="category-btn active" data-category="all">All</button>`;
        
        // Add other categories
        categories.forEach(category => {
            const button = document.createElement('button');
            button.className = 'category-btn';
            button.dataset.category = category.name;
            button.textContent = category.name.charAt(0).toUpperCase() + category.name.slice(1);
            categoryNav.appendChild(button);
        });
        
        // Attach event listeners
        const categoryButtons = document.querySelectorAll('.category-btn');
        categoryButtons.forEach(button => {
            button.addEventListener('click', () => {
                categoryButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                displayProducts(button.dataset.category);
            });
        });
    } catch (error) {
        console.error('Error fetching categories:', error);
    }
}

// Display products
function displayProducts(category = 'all') {
    productsGrid.innerHTML = '';
    
    const filteredProducts = category === 'all' 
        ? products 
        : products.filter(product => product.category === category);
    
    if (filteredProducts.length === 0) {
        productsGrid.innerHTML = '<div class="loading">No products found in this category.</div>';
        return;
    }
    
    filteredProducts.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'product-card';
        productCard.innerHTML = `
            <img src="${product.image}" alt="${product.name}" class="product-image">
            <div class="product-info">
                <div class="product-name">${product.name}</div>
                <div class="product-price">$${product.price.toFixed(2)}</div>
            </div>
        `;
        productCard.addEventListener('click', () => showProductDetails(product));
        productsGrid.appendChild(productCard);
    });
}

// Show product details
function showProductDetails(product) {
    const productDetailsEl = document.getElementById('product-details');
    productDetailsEl.innerHTML = `
        <img src="${product.image}" alt="${product.name}" class="product-details-img">
        <div class="product-details-name">${product.name}</div>
        <div class="product-details-price">$${product.price.toFixed(2)}</div>
        <div class="product-details-desc">${product.description}</div>
        
        <div class="size-selector">
            <h3>Select Size</h3>
            <div class="size-options">
                ${product.sizes.map(size => `
                    <div class="size-option" data-size="${size}">${size}</div>
                `).join('')}
            </div>
        </div>
        
        <div class="quantity-selector">
            <button class="quantity-minus">-</button>
            <input type="number" value="1" min="1" class="quantity-input">
            <button class="quantity-plus">+</button>
        </div>
        
        <button class="primary-btn add-to-cart-btn" data-product-id="${product.id}">Add to Cart</button>
    `;
    
    // Size selection
    const sizeOptions = productDetailsEl.querySelectorAll('.size-option');
    let selectedSize = null;
    
    sizeOptions.forEach(option => {
        option.addEventListener('click', () => {
            sizeOptions.forEach(opt => opt.classList.remove('selected'));
            option.classList.add('selected');
            selectedSize = option.dataset.size;
        });
    });
    
    // Quantity controls
    const quantityInput = productDetailsEl.querySelector('.quantity-input');
    const minusBtn = productDetailsEl.querySelector('.quantity-minus');
    const plusBtn = productDetailsEl.querySelector('.quantity-plus');
    
    minusBtn.addEventListener('click', () => {
        const currentValue = parseInt(quantityInput.value);
        if (currentValue > 1) {
            quantityInput.value = currentValue - 1;
        }
    });
    
    plusBtn.addEventListener('click', () => {
        const currentValue = parseInt(quantityInput.value);
        quantityInput.value = currentValue + 1;
    });
    
    // Add to cart
    const addToCartBtn = productDetailsEl.querySelector('.add-to-cart-btn');
    
    addToCartBtn.addEventListener('click', () => {
        if (!selectedSize) {
            alert('Please select a size');
            return;
        }
        
        const quantity = parseInt(quantityInput.value);
        addToCart(product, selectedSize, quantity);
        productModal.style.display = 'none';
    });
    
    productModal.style.display = 'block';
}

// Add product to cart
function addToCart(product, size, quantity) {
    // Check if this product with same size already exists in cart
    const existingItemIndex = cart.findIndex(
        item => item.id === product.id && item.size === size
    );
    
    if (existingItemIndex >= 0) {
        // Update quantity if product already in cart
        cart[existingItemIndex].quantity += quantity;
    } else {
        // Add new item to cart
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            size: size,
            quantity: quantity
        });
    }
    
    updateCartUI();
}

// Update cart UI
function updateCartUI() {
    // Update cart count
    const totalItems = cart.reduce((total, item) => total + item.quantity, 0);
    cartCount.textContent = totalItems;
    
    // Update cart items display
    if (cart.length === 0) {
        cartItems.innerHTML = '<div class="empty-cart">Your cart is empty</div>';
        checkoutBtn.disabled = true;
    } else {
        cartItems.innerHTML = '';
        cart.forEach((item, index) => {
            const cartItem = document.createElement('div');
            cartItem.className = 'cart-item';
            cartItem.innerHTML = `
                <img src="${item.image}" alt="${item.name}" class="cart-item-img">
                <div class="cart-item-details">
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-size">Size: ${item.size}</div>
                    <div class="cart-item-price">$${item.price.toFixed(2)}</div>
                    <div class="cart-item-quantity">
                        <button class="cart-item-minus" data-index="${index}">-</button>
                        <span>${item.quantity}</span>
                        <button class="cart-item-plus" data-index="${index}">+</button>
                    </div>
                    <button class="cart-item-remove" data-index="${index}">Remove</button>
                </div>
            `;
            cartItems.appendChild(cartItem);
        });
        
        // Attach event listeners to cart item buttons
        const minusButtons = cartItems.querySelectorAll('.cart-item-minus');
        const plusButtons = cartItems.querySelectorAll('.cart-item-plus');
        const removeButtons = cartItems.querySelectorAll('.cart-item-remove');
        
        minusButtons.forEach(button => {
            button.addEventListener('click', () => {
                const index = button.dataset.index;
                if (cart[index].quantity > 1) {
                    cart[index].quantity--;
                    updateCartUI();
                }
            });
        });
        
        plusButtons.forEach(button => {
            button.addEventListener('click', () => {
                const index = button.dataset.index;
                cart[index].quantity++;
                updateCartUI();
            });
        });
        
        removeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const index = button.dataset.index;
                cart.splice(index, 1);
                updateCartUI();
            });
        });
        
        checkoutBtn.disabled = false;
    }
    
    // Update total price
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    totalPrice.textContent = `$${total.toFixed(2)}`;
}

// Show cart
function showCart() {
    updateCartUI();
    cartModal.style.display = 'block';
}

// Event Listeners
// Cart button
cartButton.addEventListener('click', showCart);

// Close modals
closeModalButtons.forEach(button => {
    button.addEventListener('click', () => {
        productModal.style.display = 'none';
        cartModal.style.display = 'none';
    });
});

// Click outside modal to close
window.addEventListener('click', event => {
    if (event.target === productModal) {
        productModal.style.display = 'none';
    }
    if (event.target === cartModal) {
        cartModal.style.display = 'none';
    }
});

// Checkout button
checkoutBtn.addEventListener('click', () => {
    if (cart.length === 0) return;
    
    // Prepare order data
    const orderData = {
        items: cart.map(item => ({
            id: item.id,
            name: item.name,
            price: item.price,
            size: item.size,
            quantity: item.quantity
        })),
        total: cart.reduce((sum, item) => sum + (item.price * item.quantity), 0)
    };
    
    // Send data back to Telegram
    tg.sendData(JSON.stringify(orderData));
    
    // Close cart modal
    cartModal.style.display = 'none';
    
    // Clear cart
    cart = [];
    updateCartUI();
});

// Initial load
document.addEventListener('DOMContentLoaded', async () => {
    await fetchCategories();
    await fetchProducts();
    updateCartUI();
}); 