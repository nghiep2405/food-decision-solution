# Quy định branch, commit và pull request

Tài liệu này áp dụng chung cho frontend và backend. Jira quản lý task/assignee; GitHub quản lý code, pull request và review.

## 1. Các branch được dùng

```text
main  <- bản ổn định
  ↑
dev   <- branch tích hợp
  ↑
task branches
```

- Không commit trực tiếp vào `main` hoặc `dev`.
- Mỗi task branch chỉ xử lý **một Jira task** và được tạo từ `dev` mới nhất.
- Không tạo branch cá nhân dài hạn.

## 2. Đặt tên branch

```text
feature/FDS-12-restaurant-search
fix/FDS-25-budget-rounding
docs/FDS-30-api-instructions
chore/FDS-35-update-dependencies
```

Chỉ dùng bốn prefix:

- `feature/`: thêm hoặc thay đổi chức năng.
- `fix/`: sửa hành vi sai.
- `docs/`: chỉ thay đổi tài liệu.
- `chore/`: cấu hình, dependency hoặc việc bảo trì không đổi business behavior.

Format: `<prefix>/FDS-<number>-<mô-tả-ngắn-kebab-case>`.

## 3. Luồng làm một task

```powershell
git switch dev
git pull origin dev
git switch -c feature/FDS-12-restaurant-search

# Làm việc và kiểm tra file thay đổi
git status
git diff

# Add đúng file của task
git add frontend/src/features/restaurant-discovery/index.js
git add frontend/src/features/restaurant-discovery/view.js

git commit -m "FDS-12 add restaurant search form"
git push -u origin feature/FDS-12-restaurant-search
```

Sau khi push, tạo pull request vào `dev` và chuyển Jira task sang `In Review`.

Không khuyến khích thành viên mới dùng `git add .`; hãy add đúng file để tránh đưa `.env`, file tạm hoặc thay đổi không liên quan vào commit.

## 4. Commit message

Format:

```text
FDS-<number> <động từ> <nội dung thay đổi ngắn gọn>
```

Ví dụ:

```text
FDS-12 add restaurant search endpoint
FDS-18 add menu OCR response schema
FDS-25 fix missing-price calculation
FDS-30 document backend setup
```

Quy tắc:

- Bắt đầu bằng Jira key.
- Dùng động từ rõ như `add`, `fix`, `update`, `remove`, `document`, `refactor`.
- Một commit chứa một thay đổi logic; không gom nhiều task không liên quan.
- Không bắt buộc Conventional Commits ở giai đoạn này.
- Không commit `.env`, API key, dữ liệu cá nhân, `node_modules/`, `.venv/` hoặc `dist/`.

## 5. Kiểm tra trước khi push

Frontend:

```powershell
cd frontend
npm run build
```

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Chạy `git status` lần cuối và chắc chắn chỉ có file thuộc Jira task.

## 6. Quy tắc pull request

- Base branch là `dev`; chỉ coordinator tạo release PR `dev -> main`.
- Một PR tương ứng một Jira task, tiêu đề dạng `[FDS-12] Add restaurant search`.
- Có ít nhất một reviewer khác author.
- PR phải ghi: Jira link, thay đổi chính, cách kiểm tra và evidence.
- Không merge khi test/build fail hoặc feedback chưa xử lý.
- Dùng **Squash and merge** để giữ lịch sử `dev` gọn.
- Sau khi merge, xóa task branch và chuyển Jira task sang `Done`.

## 7. Nội dung PR tối thiểu

```markdown
## Jira
FDS-___: <link>

## What changed?
-

## How to check?
-

## Evidence
Screenshot, sample request/response hoặc test result.

## Checklist
- [ ] Chỉ thay đổi đúng task
- [ ] Đã tự review diff
- [ ] Đã chạy/test phần liên quan
- [ ] Không có secret hoặc dữ liệu cá nhân
```

Nếu branch bị chậm hơn `dev`, cập nhật trước khi hoàn thiện PR:

```powershell
git switch dev
git pull origin dev
git switch <task-branch>
git merge dev
```

Thành viên chưa quen Git ưu tiên `merge dev` như trên; không tự rebase hoặc force-push branch đã có người khác cùng làm.
