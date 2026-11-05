import './styles/global.css';
import { createAppShell } from './core/ui/app-shell.js';
import { mountHome } from './features/home/index.js';
import { mountRestaurantDiscovery } from './features/restaurant-discovery/index.js';
import { mountRecommendation } from './features/recommendation/index.js';
import { mountResults } from './features/results/index.js';
import { demoMenu, demoRestaurant, mountMenu } from './features/menu/index.js';
import { mountBudget } from './features/budget/index.js';

const appRoot = document.querySelector('#app');

if (!appRoot) {
  throw new Error('Không tìm thấy phần tử #app để khởi tạo giao diện.');
}

let activeFeature = null;
let selectedRestaurant = null;
let currentSearchContext = null;
let currentMenu = demoMenu;
let selectedMenuItems = [];
let restaurantReturnRoute = '/search';

function currentRoute() {
  const route = window.location.hash.replace(/^#/, '') || '/';
  return route.startsWith('/') ? route : `/${route}`;
}

function navigate(route) {
  const nextHash = `#${route}`;
  if (window.location.hash === nextHash) renderRoute();
  else window.location.hash = nextHash;
}

function menuRestaurant(restaurant) {
  if (!restaurant) return demoRestaurant;
  const route = restaurant.travelMinutes == null
    ? null
    : `${restaurant.distanceKm ?? 'Chưa rõ'} km · ${restaurant.travelMinutes} phút`;

  return {
    ...restaurant,
    route: restaurant.route ?? route,
    verificationStatus: restaurant.verificationStatus
      ?? (restaurant.menuVerified ? 'verified' : 'unverified'),
  };
}

function totalSelectedQuantity() {
  return selectedMenuItems.reduce((total, selection) => total + Number(selection.quantity || 0), 0);
}

const shell = createAppShell(appRoot, {
  onBack() {
    const route = currentRoute();
    if (route === '/search' || route === '/recommendation') navigate('/');
    else if (route === '/results') navigate('/recommendation');
    else if (route === '/restaurant-detail' || route === '/menu') navigate(restaurantReturnRoute);
    else if (route === '/budget') navigate('/restaurant-detail');
    else navigate('/');
  },
  onClearSelection() {
    activeFeature?.clearSelection?.();
    if (currentRoute() === '/restaurant-detail' || currentRoute() === '/menu') {
      selectedMenuItems = [];
      shell.showToast('Đã bỏ các món đang chọn.', 'info');
    } else {
      selectedRestaurant = null;
      shell.showToast('Đã bỏ lựa chọn quán.', 'info');
    }
    shell.setSelection(null);
  },
  onContinueSelection() {
    const route = currentRoute();
    if ((route === '/search' || route === '/results') && selectedRestaurant) {
      restaurantReturnRoute = route;
      navigate('/restaurant-detail');
    } else if ((route === '/restaurant-detail' || route === '/menu') && totalSelectedQuantity() > 0) {
      navigate('/budget');
    }
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
  selectedRestaurant = null;
  currentSearchContext = null;
  currentMenu = demoMenu;
  selectedMenuItems = [];
  shell.setSelection(null);
  shell.setBackAction({ visible: false });
  activeFeature = mountHome(shell.main, {
    onContinue(mode) {
      showRouteLoading(
        mode === 'direct' ? 'Đang mở luồng tìm theo món...' : 'Đang mở luồng gợi ý phù hợp...',
        mode === 'direct' ? '/search' : '/recommendation',
      );
    },
  });
}

function renderSearchRoute() {
  document.title = 'Food Decision - Tìm quán theo món';
  selectedRestaurant = null;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Trang chủ' });
  activeFeature = mountRestaurantDiscovery(shell.main, {
    onSelectionChange(restaurant) {
      selectedRestaurant = restaurant;
      shell.setSelection(restaurant ? {
        label: 'Quán đã chọn',
        name: restaurant.name,
        actionLabel: 'Xem thực đơn',
      } : null);
      if (restaurant) shell.showToast(`Đã chọn ${restaurant.name}.`, 'success');
    },
  });
}

function renderRecommendationRoute() {
  document.title = 'Food Decision - Gợi ý món phù hợp';
  selectedRestaurant = null;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Trang chủ' });
  activeFeature = mountRecommendation(shell.main, {
    initialPreset: currentSearchContext?.preferences?.isColdStart ? 'cold-start' : 'returning',
    onSubmit(searchContext) {
      currentSearchContext = searchContext;
      shell.showToast('Đã tạo yêu cầu gợi ý và chuyển sang bảng xếp hạng.', 'success');
      navigate('/results');
    },
    onSwitchMode() {
      navigate('/search');
    },
  });
}

function renderResultsRoute() {
  document.title = 'Food Decision - Kết quả được xếp hạng';
  selectedRestaurant = null;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Sở thích & bối cảnh' });
  activeFeature = mountResults(shell.main, {
    searchContext: currentSearchContext,
    initialScenario: currentSearchContext?.preferences?.isColdStart ? 'cold-start' : 'recommendation',
    onSelectRestaurant(restaurant) {
      selectedRestaurant = restaurant;
      shell.setSelection(restaurant ? {
        label: 'Quán được chọn từ bảng xếp hạng',
        name: restaurant.name,
        actionLabel: 'Xem thực đơn',
      } : null);
      if (restaurant) shell.showToast(`Đã chọn ${restaurant.name}.`, 'success');
    },
    onOpenDetail(restaurant) {
      selectedRestaurant = restaurant;
      restaurantReturnRoute = '/results';
      navigate('/restaurant-detail');
    },
    onOpenFeedback() {
      shell.showToast('Feature Feedback chưa được tích hợp vào main.', 'info');
    },
    onChangeSearchContext() {
      navigate('/recommendation');
    },
  });
}

function renderMenuRoute() {
  selectedRestaurant ??= demoRestaurant;
  document.title = `Food Decision - ${selectedRestaurant.name}`;
  shell.setSelection(null);
  shell.setBackAction({
    visible: true,
    label: restaurantReturnRoute === '/results' ? 'Kết quả xếp hạng' : 'Kết quả tìm quán',
  });
  activeFeature = mountMenu(shell.main, {
    restaurant: menuRestaurant(selectedRestaurant),
    menu: currentMenu,
    initialSelections: selectedMenuItems,
    onSelectionChange(selections, menuItems) {
      selectedMenuItems = selections.filter((selection) => selection.quantity > 0);
      currentMenu = menuItems;
      const quantity = totalSelectedQuantity();
      shell.setSelection(quantity > 0 ? {
        label: 'Món đã chọn',
        name: `${quantity} phần tại ${selectedRestaurant.name}`,
        actionLabel: 'Kiểm tra ngân sách',
      } : null);
    },
  });

  const quantity = totalSelectedQuantity();
  if (quantity > 0) {
    shell.setSelection({
      label: 'Món đã chọn',
      name: `${quantity} phần tại ${selectedRestaurant.name}`,
      actionLabel: 'Kiểm tra ngân sách',
    });
  }
}

function renderBudgetRoute() {
  selectedRestaurant ??= demoRestaurant;
  document.title = `Food Decision - Ngân sách tại ${selectedRestaurant.name}`;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Thực đơn' });

  const recommendationBudget = currentSearchContext?.budget;
  activeFeature = mountBudget(shell.main, {
    restaurant: menuRestaurant(selectedRestaurant),
    menu: currentMenu,
    initialSelections: selectedMenuItems,
    initialDinerCount: currentSearchContext?.dinerCount ?? 2,
    initialBudget: recommendationBudget?.amount ?? 200000,
    initialBudgetMode: recommendationBudget?.mode === 'perPerson' ? 'perPerson' : 'total',
  });
}

function renderRoute() {
  shell.setLoading(false);
  activeFeature?.unmount?.();
  activeFeature = null;

  const route = currentRoute();
  if (route === '/') renderHomeRoute();
  else if (route === '/search') renderSearchRoute();
  else if (route === '/recommendation') renderRecommendationRoute();
  else if (route === '/results') renderResultsRoute();
  else if (route === '/restaurant-detail' || route === '/menu') renderMenuRoute();
  else if (route === '/budget') renderBudgetRoute();
  else { navigate('/'); return; }

  window.scrollTo({ top: 0, behavior: 'auto' });
  shell.focusMain();
}

window.addEventListener('hashchange', renderRoute);
renderRoute();
