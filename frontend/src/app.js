import './styles/global.css';
import { createAppShell } from './core/ui/app-shell.js';
import { renderIntegrationStage } from './core/ui/integration-stage.js';
import { mountHome } from './features/home/index.js';
import { mountRestaurantDiscovery } from './features/restaurant-discovery/index.js';

const appRoot = document.querySelector('#app');

if (!appRoot) {
  throw new Error('Không tìm thấy phần tử #app để khởi tạo giao diện.');
}

let activeFeature = null;
let selectedRestaurant = null;

function currentRoute() {
  const route = window.location.hash.replace(/^#/, '') || '/';
  return route.startsWith('/') ? route : `/${route}`;
}

function navigate(route) {
  const nextHash = `#${route}`;
  if (window.location.hash === nextHash) {
    renderRoute();
  } else {
    window.location.hash = nextHash;
  }
}

const shell = createAppShell(appRoot, {
  onBack() {
    const route = currentRoute();
    navigate(route === '/restaurant-detail' ? '/search' : '/');
  },
  onClearSelection() {
    activeFeature?.clearSelection?.();
    selectedRestaurant = null;
    shell.setSelection(null);
    shell.showToast('Đã bỏ lựa chọn quán.', 'info');
  },
  onContinueSelection() {
    if (selectedRestaurant) navigate('/restaurant-detail');
  },
});

function showRouteLoading(label, nextRoute) {
  shell.setLoading(true, label);
  window.setTimeout(() => {
    shell.setLoading(false);
    navigate(nextRoute);
  }, 260);
}

function renderHomeRoute() {
  document.title = 'Food Decision - Chọn cách bắt đầu';
  activeFeature = mountHome(shell.main, {
    onContinue(mode) {
      if (mode === 'direct') {
        showRouteLoading('Đang mở luồng tìm theo món...', '/search');
      } else {
        showRouteLoading('Đang mở luồng gợi ý phù hợp...', '/recommendation');
      }
    },
  });
  selectedRestaurant = null;
  shell.setSelection(null);
  shell.setBackAction({ visible: false });
}

function renderSearchRoute() {
  document.title = 'Food Decision - Tìm quán theo món';
  shell.setBackAction({ visible: true, label: 'Trang chủ' });
  activeFeature = mountRestaurantDiscovery(shell.main, {
    onSelectionChange(restaurant) {
      selectedRestaurant = restaurant;
      shell.setSelection(restaurant ? { label: 'Quán đã chọn', name: restaurant.name } : null);
      if (restaurant) shell.showToast(`Đã chọn ${restaurant.name}.`, 'success');
    },
  });
}

function renderRecommendationRoute() {
  document.title = 'Food Decision - Luồng gợi ý phù hợp';
  activeFeature = null;
  selectedRestaurant = null;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Trang chủ' });
  renderIntegrationStage(shell.main, {
    type: 'recommendation',
    onReturn: () => navigate('/'),
  });
}

function renderDetailRoute() {
  if (!selectedRestaurant) {
    navigate('/search');
    return;
  }
  document.title = `Food Decision - ${selectedRestaurant.name}`;
  activeFeature = null;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Kết quả' });
  renderIntegrationStage(shell.main, {
    type: 'detail',
    selection: selectedRestaurant,
    onReturn: () => navigate('/search'),
  });
}

function renderRoute() {
  shell.setLoading(false);
  const route = currentRoute();

  if (route === '/') renderHomeRoute();
  else if (route === '/search') renderSearchRoute();
  else if (route === '/recommendation') renderRecommendationRoute();
  else if (route === '/restaurant-detail') renderDetailRoute();
  else navigate('/');

  window.scrollTo({ top: 0, behavior: 'auto' });
  shell.focusMain();
}

window.addEventListener('hashchange', renderRoute);
renderRoute();
