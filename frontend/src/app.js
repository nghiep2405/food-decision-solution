import './styles/global.css';
import { createAppShell } from './core/ui/app-shell.js';
import { mountHome } from './features/home/index.js';
import { DEMO_SCENARIOS, mountRestaurantDiscovery } from './features/restaurant-discovery/index.js';
import { mountSearchArea } from './features/search-area/index.js';
import { mountRecommendation } from './features/recommendation/index.js';
import { fetchRecommendations } from './features/recommendation/api.js';
import { mountResults } from './features/results/index.js';
import { demoMenu, demoRestaurant, mountMenu } from './features/menu/index.js';
import { fetchRestaurantMenu } from './features/menu/api.js';
import { mountBudget } from './features/budget/index.js';
import { mountReviewReliability } from './features/review-reliability/index.js';
import { analyzeReviews } from './features/review-reliability/api.js';

const appRoot = document.querySelector('#app');

if (!appRoot) {
  throw new Error('Không tìm thấy phần tử #app để khởi tạo giao diện.');
}

let activeFeature = null;
let selectedRestaurant = null;
let currentSearchContext = null;
let currentMenu = demoMenu;
let selectedMenuItems = [];
let mealRestaurantId = null;
let menuLoadAttemptedForId = null;
let currentRankedResult = null;
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

function prepareRestaurantMeal() {
  selectedRestaurant ??= demoRestaurant;
  if (mealRestaurantId === selectedRestaurant.id) return;
  mealRestaurantId = selectedRestaurant.id;
  currentMenu = demoMenu;
  selectedMenuItems = [];
  menuLoadAttemptedForId = null;
}

const shell = createAppShell(appRoot, {
  onBack() {
    const route = currentRoute();
    if (route === '/search' || route === '/recommendation') navigate('/');
    else if (route === '/results') navigate('/recommendation');
    else if (route === '/restaurant-detail' || route === '/menu') navigate(restaurantReturnRoute);
    else if (route === '/budget') navigate('/restaurant-detail');
    else if (route === '/review-reliability') navigate('/restaurant-detail');
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
  mealRestaurantId = null;
  menuLoadAttemptedForId = null;
  currentRankedResult = null;
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
  shell.main.innerHTML = `
    <header class="ui-page-hero">
      <div>
        <p class="ui-kicker">Tìm theo món</p>
        <h1>Tìm một nơi đúng gu của bạn</h1>
        <p class="ui-page-hero__lead">Chọn vị trí và vùng trên bản đồ, rồi tìm món bạn muốn ăn.</p>
      </div>
    </header>
    <div class="search-workspace">
      <aside class="search-workspace__panel search-workspace__filters" data-role="search-area" aria-label="Điều kiện tìm kiếm"></aside>
      <div class="search-workspace__content" data-mobile-view="map">
        <div class="search-workspace__switch" role="group" aria-label="Chế độ xem kết quả">
          <button class="ui-button ui-button--outline" type="button" data-view="map" aria-pressed="true">Bản đồ</button>
          <button class="ui-button ui-button--outline" type="button" data-view="list" aria-pressed="false">Danh sách</button>
        </div>
        <section class="search-workspace__panel search-workspace__map" data-role="map-area" aria-label="Bản đồ tìm quán"></section>
        <section class="search-workspace__panel search-workspace__results" data-role="discovery" aria-labelledby="restaurant-result-title"></section>
      </div>
    </div>`;

  const content = shell.main.querySelector('.search-workspace__content');
  const viewButtons = [...content.querySelectorAll('[data-view]')];
  const params = new URLSearchParams(window.location.search);
  const requestedScenario = params.get('scenario');
  const requestedDelay = params.get('delay');
  const rawDelay = Number(requestedDelay);
  const scenario = DEMO_SCENARIOS.includes(requestedScenario) ? requestedScenario : 'full';
  const delayMs = requestedDelay !== null && Number.isFinite(rawDelay) ? Math.min(10000, Math.max(0, rawDelay)) : 250;
  let mapResizeFrame = null;

  function setMobileView(view) {
    content.dataset.mobileView = view;
    for (const button of viewButtons) button.setAttribute('aria-pressed', String(button.dataset.view === view));
    window.cancelAnimationFrame(mapResizeFrame);
    if (view === 'map') {
      mapResizeFrame = window.requestAnimationFrame(() => {
        searchArea.invalidateSize();
        if (selectedRestaurant) searchArea.selectRestaurant(selectedRestaurant.id);
      });
    }
  }

  function selectRestaurant(restaurant, source) {
    const id = restaurant?.id ?? null;
    const selectionChanged = selectedRestaurant?.id !== restaurant?.id;
    selectedRestaurant = restaurant;
    const mobile = window.matchMedia('(max-width: 850px)').matches;
    if (restaurant && mobile) setMobileView(source === 'map' ? 'list' : 'map');
    discovery.selectRestaurant(id, { focus: source === 'map' });
    if (mobile && source === 'list') searchArea.invalidateSize();
    searchArea.selectRestaurant(id, { pan: !mobile || source === 'list' });
    shell.setSelection(restaurant ? {
      label: 'Quán đã chọn',
      name: restaurant.name,
      actionLabel: 'Xem thực đơn',
    } : null);
    if (restaurant && selectionChanged) shell.showToast(`Đã chọn ${restaurant.name}.`, 'success');
  }

  function openDetail(restaurant) {
    selectedRestaurant = restaurant;
    restaurantReturnRoute = '/search';
    navigate('/restaurant-detail');
  }

  const discovery = mountRestaurantDiscovery(content.querySelector('[data-role="discovery"]'), {
    scenario,
    delayMs,
    showSelectionBar: false,
    onResultsChange: (restaurants) => searchArea.setRestaurants(restaurants),
    onBusyChange: (busy) => searchArea.setBusy(busy),
    onSelectRestaurant: (restaurant) => selectRestaurant(restaurant, 'list'),
    onOpenDetail: openDetail,
    onReset: () => searchArea.reset(),
  });
  const searchArea = mountSearchArea(
    shell.main.querySelector('[data-role="search-area"]'),
    content.querySelector('[data-role="map-area"]'),
    {
      onSearch: (context) => {
        currentSearchContext = context;
        return discovery.search(context);
      },
      onSelectRestaurant: (restaurant) => selectRestaurant(restaurant, 'map'),
      onOpenDetail: openDetail,
    },
  );

  for (const button of viewButtons) {
    button.addEventListener('click', () => setMobileView(button.dataset.view));
  }
  activeFeature = {
    clearSelection: () => selectRestaurant(null, 'list'),
    unmount() {
      window.cancelAnimationFrame(mapResizeFrame);
      discovery.destroy();
      searchArea.destroy();
    },
  };
  searchArea.search();
}

function renderRecommendationRoute() {
  document.title = 'Food Decision - Gợi ý món phù hợp';
  selectedRestaurant = null;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Trang chủ' });
  activeFeature = mountRecommendation(shell.main, {
    initialPreset: currentSearchContext?.preferences?.isColdStart ? 'cold-start' : 'returning',
    async onSubmit(searchContext) {
      currentSearchContext = searchContext;
      currentRankedResult = null;
      shell.setLoading(true, 'Đang tìm ứng viên và xếp hạng gợi ý...');
      try {
        currentRankedResult = await fetchRecommendations(searchContext);
        shell.showToast('Đã xếp hạng quán từ dữ liệu backend.', 'success');
        navigate('/results');
      } catch (error) {
        shell.showToast(`Không gọi được backend: ${error.message} Đang dùng dữ liệu demo.`, 'warning');
        navigate('/results');
      } finally {
        shell.setLoading(false);
      }
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
    rankedItems: currentRankedResult?.items ?? null,
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
  prepareRestaurantMeal();
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
    onOpenReviewReliability() {
      navigate('/review-reliability');
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

  const restaurantId = selectedRestaurant.id;
  if (!restaurantId.startsWith('demo-') && menuLoadAttemptedForId !== restaurantId) {
    menuLoadAttemptedForId = restaurantId;
    fetchRestaurantMenu(restaurantId)
      .then((menuItems) => {
        if (selectedRestaurant?.id !== restaurantId) return;
        currentMenu = menuItems;
        selectedMenuItems = [];
        if (currentRoute() === '/restaurant-detail' || currentRoute() === '/menu') {
          activeFeature?.unmount?.();
          renderMenuRoute();
          shell.showToast('Đã tải menu chuẩn hóa từ backend.', 'success');
        }
      })
      .catch((error) => {
        shell.showToast(`Chưa tải được menu backend: ${error.message} Đang giữ menu demo.`, 'warning');
      });
  }
}

function renderReviewReliabilityRoute() {
  selectedRestaurant ??= demoRestaurant;
  document.title = `Food Decision - Độ tin cậy đánh giá tại ${selectedRestaurant.name}`;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Chi tiết quán' });

  const summary = selectedRestaurant.reviewSummary ?? null;
  activeFeature = mountReviewReliability(shell.main, {
    restaurant: selectedRestaurant,
    summaryData: summary,
    onOpenFeedback() {
      shell.showToast('Feature Feedback chưa được tích hợp vào main.', 'info');
    },
  });

  const restaurantId = selectedRestaurant.id;
  const loadAnalysis = async () => {
    activeFeature?.setViewState?.('loading');
    try {
      const nextSummary = await analyzeReviews(restaurantId, 'combined');
      if (currentRoute() === '/review-reliability' && selectedRestaurant?.id === restaurantId) {
        activeFeature?.setSummaryData?.(nextSummary);
      }
    } catch (error) {
      activeFeature?.setViewState?.('error');
      shell.showToast(`Không phân tích được review: ${error.message}`, 'warning');
    }
  };

  shell.main.addEventListener('review:retry-analysis', loadAnalysis, { once: true });
  if (!restaurantId.startsWith('demo-')) loadAnalysis();
}

function renderBudgetRoute() {
  prepareRestaurantMeal();
  document.title = `Food Decision - Ngân sách tại ${selectedRestaurant.name}`;
  shell.setSelection(null);
  shell.setBackAction({ visible: true, label: 'Thực đơn' });

  const recommendationBudget = currentSearchContext?.budget;
  const directBudgetPerPerson = currentSearchContext?.mode === 'direct'
    ? currentSearchContext.budgetPerPerson
    : null;
  activeFeature = mountBudget(shell.main, {
    restaurant: menuRestaurant(selectedRestaurant),
    menu: currentMenu,
    initialSelections: selectedMenuItems,
    initialDinerCount: currentSearchContext?.dinerCount ?? 2,
    initialBudget: recommendationBudget?.amount ?? directBudgetPerPerson ?? 200000,
    initialBudgetMode: recommendationBudget
      ? (recommendationBudget.mode === 'perPerson' ? 'perPerson' : 'total')
      : (directBudgetPerPerson != null ? 'perPerson' : 'total'),
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
  else if (route === '/review-reliability') renderReviewReliabilityRoute();
  else { navigate('/'); return; }

  window.scrollTo({ top: 0, behavior: 'auto' });
  shell.focusMain();
}

window.addEventListener('hashchange', renderRoute);
renderRoute();
