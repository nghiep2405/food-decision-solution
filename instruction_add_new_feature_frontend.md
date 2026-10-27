# Hướng dẫn thêm feature frontend

Frontend dùng HTML, CSS và JavaScript ES modules với Vite. Mỗi feature nằm trong một folder riêng để giảm conflict khi nhiều thành viên làm song song.

Tham khảo feature hoàn chỉnh: `src/features/restaurant-discovery/`.

## 1. Quy tắc dependency

```text
app.js -> feature -> core
core -X-> feature
feature A -X-> file nội bộ của feature B
```

- `app.js` ghép và khởi động các feature.
- Feature dùng helper chung trong `src/core/`.
- Feature khác chỉ được import public export từ `index.js`, không import trực tiếp `view.js`, `api.js` hoặc file nội bộ.
- Khi cần phối hợp nhiều feature, thực hiện tại `app.js`; không tạo import vòng tròn.

## 2. Cấu trúc feature

Tên folder dùng **kebab-case**, ví dụ `search-area`, `review-reliability`.

```text
src/features/{feature-name}/
├── index.js       # public exports
├── api.js         # gọi backend thông qua core/api-client.js
├── view.js        # render DOM và xử lý event
├── style.css      # style riêng của feature
└── README.md      # input, output, cách dùng/test
```

Chỉ thêm khi cần:

```text
state.js           # state đủ phức tạp để tách khỏi view
validation.js      # validation riêng
algorithm.js       # filter, sort hoặc thuật toán chạy ở browser
```

Không tạo file trống chỉ để đủ cấu trúc. Nếu feature không gọi backend, có thể bỏ `api.js` và ghi rõ trong README.

## 3. Trách nhiệm từng phần

- `index.js`: cổng công khai của feature; thường export hàm `mount...()`.
- `api.js`: chứa endpoint và chuyển đổi response; không render DOM.
- `view.js`: tạo UI, đọc input, bắt sự kiện; không gọi `fetch` trực tiếp.
- `algorithm.js`: hàm thuần, không truy cập DOM hoặc HTTP.
- `style.css`: dùng class có tên rõ theo feature; không sửa global style nếu không cần.
- `README.md`: mô tả mục tiêu, input, output, dependency và cách manual test.

Code dùng chung thật sự mới đặt trong `src/core/`. Không chuyển business logic riêng của một feature vào `core/`.

## 4. Các bước thêm feature

1. Chọn Jira task, xác định owner/reviewer và tạo task branch theo `../git_branch_commit_rules.md`.
2. Tạo folder trong `src/features/` và viết README trước để chốt input/output.
3. Viết logic độc lập; dùng `algorithm.js` nếu cần filter, sort hoặc tính toán.
4. Nếu gọi backend, dùng `getJson` hoặc helper trong `src/core/api-client.js` từ `api.js`.
5. Render và xử lý event trong `view.js`.
6. Export API công khai qua `index.js`.
7. Import feature từ `index.js` vào `src/app.js` để mount hoặc phối hợp luồng.
8. Chạy kiểm tra trước khi commit:

```powershell
npm run dev
npm run build
```

## 5. Mẫu tối thiểu

```js
// index.js
import './style.css';
import { createFeatureView } from './view.js';

export function mountFeature(container) {
  const feature = createFeatureView();
  feature.mount(container);
  return feature;
}
```

```js
// api.js
import { getJson } from '../../core/api-client.js';

export function fetchFeatureData() {
  return getJson('/api/v1/example');
}
```

## 6. Checklist trước khi tạo PR

- [ ] Đúng một Jira task và đúng folder feature.
- [ ] README nêu rõ input, output và cách kiểm tra.
- [ ] Feature khác chỉ import từ `index.js`.
- [ ] `view.js` không gọi `fetch` hoặc chứa URL backend.
- [ ] Không có API key, `.env`, dữ liệu cá nhân hoặc dữ liệu thật không được phép.
- [ ] Có happy-path manual test; thuật toán quan trọng có test khi nhóm bổ sung test runner.
- [ ] `npm run build` thành công.
- [ ] PR có hướng dẫn để reviewer kiểm tra.
