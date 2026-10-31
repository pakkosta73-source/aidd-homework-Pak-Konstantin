---
sessionId: session-261030-225341-47g4
---

# Requirements

### Overview & Goals
Implement a **Personal Share Monitoring** feature that allows authenticated users to:
- Create personal watchlists of shares they want to track
- Set target price levels for each watched share
- Receive notifications when a share's price reaches the target level
- Prevent duplicate notifications for the same event

### User Stories
1. As an authenticated user, I want to add shares to my personal watchlist so that I can monitor specific shares.
2. As an authenticated user, I want to set a target price for a watched share so that I know when to be notified.
3. As an authenticated user, I want to see a page with my watchlist and the current status of each watched share.
4. As an authenticated user, I want to receive a notification when a share reaches my target price.
5. As an authenticated user, I want to remove shares from my watchlist when I no longer want to track them.
6. As an authenticated user, I want to view my notification history to see past alerts.
7. As the system, I want to automatically check watchlist conditions during price updates and trigger notifications.
8. As the system, I want to avoid sending duplicate notifications for the same price-target event.

### Functional Requirements

**FR-11: Watchlist management**
- Authenticated users can add/remove shares from their personal watchlist.
- Each watchlist entry includes a target price and an optional comparison type (above/below).
- Only authenticated users can access their watchlist.

**FR-12: Notification system**
- When a share's price reaches the target level (during Celery price updates), a notification is created.
- Notifications are stored in the database and visible to the user in the UI.
- Duplicate notifications are prevented: once a notification is sent for a specific target price, no further notifications are generated for the same condition.

**FR-13: Watchlist UI**
- A new page (`/watchlist/`) shows the user's watchlist with current prices, target prices, and status.
- A new page (`/notifications/`) shows the user's notification history.
- Navigation links to these pages are added to the base template (visible only to authenticated users).

### Scope
**In Scope:**
- New models: `WatchlistEntry`, `Notification`
- New views: watchlist CRUD, notifications list
- New templates: watchlist page, notifications page
- Integration with Celery `update_last_price` task to check conditions
- Django Admin registration for new models
- REST API endpoints for watchlist and notifications

**Out of Scope:**
- Email/push notifications (only in-app notifications)
- Real-time WebSocket updates
- Shared watchlists

# Technical Design

### Current Implementation
- **Models:** `Share` (`dashboard/models.py`) stores share data with `last_price` updated by Celery every 5 minutes.
- **Celery:** `dashboard/tasks.py` — `update_last_price()` task updates prices via Tinkoff API.
- **Views:** Class-based generic views in `dashboard/views.py` with `IsUserAuthenticatedMixin` for auth protection.
- **Templates:** Bootstrap 5, extends `dashboard/base.html` with nav header and footer.
- **URLs:** `dashboard/urls.py` with `app_name = "dashboard"`.
- **API:** DRF ViewSet in `dashboard/api/v1/views.py` with serializer in `serializer.py`.
- **Admin:** `dashboard/admin.py` registers `Share` with `@admin.register`.
- **A-2 (Ambiguity):** No user-to-share relationship exists — this feature introduces it.

### Key Decisions
1. **Models in `dashboard` app** — keeping all share-related models together, consistent with existing structure.
2. **Target price comparison** — support two modes: "price reaches or exceeds target" (above) and "price drops to or below target" (below). This covers the most common use cases.
3. **Duplicate prevention** — a `notified` boolean flag on `WatchlistEntry` prevents re-notification once the target is hit. Users can reset it manually to re-arm the alert.
4. **Notifications stored in DB** — simple `Notification` model linked to user, share, and watchlist entry. Visible in the UI as a history list.
5. **Check during price update** — integrate watchlist checking into the existing `update_last_price` Celery task to avoid adding a separate scheduled task.

### Data Models

**`WatchlistEntry`** (dashboard/models.py)
| Field | Type | Description |
|---|---|---|
| `user` | ForeignKey(User) | Owner of the watchlist entry |
| `share` | ForeignKey(Share) | Watched share |
| `target_price` | FloatField | Target price level |
| `condition` | CharField | "above" or "below" — price direction |
| `notified` | BooleanField (default=False) | Whether notification was already sent |
| `created_at` | DateTimeField (auto_now_add) | Creation time |

Unique constraint: `(user, share)` — one entry per user per share.

**`Notification`** (dashboard/models.py)
| Field | Type | Description |
|---|---|---|
| `user` | ForeignKey(User) | Recipient |
| `share` | ForeignKey(Share) | Share that triggered the notification |
| `message` | TextField | Notification text (e.g., "SBER reached target price 250.00") |
| `created_at` | DateTimeField (auto_now_add) | Time of notification |

### Proposed Changes

**1. Models** (`dashboard/models.py`)
- Add `WatchlistEntry` and `Notification` models.
- Add migration.

**2. Forms** (`dashboard/forms.py`)
- Add `WatchlistEntryForm` for creating/editing watchlist entries (share selection, target price, condition).

**3. Views** (`dashboard/views.py`)
- `WatchlistListView` — shows user's watchlist with current prices.
- `WatchlistCreateView` — add a share to watchlist.
- `WatchlistDeleteView` — remove a share from watchlist.
- `WatchlistResetView` — reset the `notified` flag to re-arm the alert.
- `NotificationListView` — show user's notification history.

**4. Celery Task** (`dashboard/tasks.py`)
- Extend `update_last_price()` to check `WatchlistEntry` conditions after updating prices.
- Create `Notification` objects when conditions are met and `notified` is False.
- Set `notified=True` to prevent duplicates.

**5. URLs** (`dashboard/urls.py`)
- Add routes: `/watchlist/`, `/watchlist/add/`, `/watchlist/remove/<pk>/`, `/watchlist/reset/<pk>/`, `/notifications/`.

**6. Templates**
- `dashboard/templates/dashboard/watchlist.html` — watchlist table with share info, current price, target price, status, actions.
- `dashboard/templates/dashboard/notification_list.html` — notification history.
- Update `dashboard/templates/dashboard/base.html` — add nav links for "Watchlist" and "Notifications" (authenticated users only).

**7. Admin** (`dashboard/admin.py`)
- Register `WatchlistEntry` and `Notification` in Django Admin.

**8. REST API**
- Add `WatchlistEntrySerializer` and `NotificationSerializer`.
- Add `WatchlistEntryViewSet` and `NotificationViewSet`.
- Register in router.

### Architecture Diagram

``` mermaid
graph LR
    U[User] -->|views| WL[WatchlistListView]
    U -->|views| NL[NotificationListView]
    U -->|form| WC[WatchlistCreateView]
    WL --> WE[WatchlistEntry Model]
    NL --> NT[Notification Model]
    WC --> WE
    CT[Celery Beat] -->|every 5min| UP[update_last_price task]
    UP -->|updates| S[Share Model]
    UP -->|checks| WE
    UP -->|creates| NT
    WE -->|FK| S
    WE -->|FK| U
    NT -->|FK| S
    NT -->|FK| U
```

### File Structure

**Modified files:**
- `dashboard/models.py` — add `WatchlistEntry`, `Notification`
- `dashboard/views.py` — add watchlist and notification views
- `dashboard/urls.py` — add new routes
- `dashboard/forms.py` — add `WatchlistEntryForm`
- `dashboard/tasks.py` — add watchlist checking logic
- `dashboard/admin.py` — register new models
- `dashboard/api/v1/serializer.py` — add serializers
- `dashboard/api/v1/views.py` — add ViewSets
- `dashboard/api/v1/router.py` — register new ViewSets
- `dashboard/templates/dashboard/base.html` — add nav links

**New files:**
- `dashboard/migrations/0008_watchlist_and_notifications.py`
- `dashboard/templates/dashboard/watchlist.html`
- `dashboard/templates/dashboard/notification_list.html`

### Risks
- **Performance:** If many users have watchlists, the Celery task may slow down. Mitigation: batch queries and use `bulk_update`.
- **Race conditions:** Multiple Celery workers could process the same watchlist entry. Mitigation: use `select_for_update()` or atomic updates with `notified` flag.
- **Price precision:** Floating point comparison for prices. Mitigation: use epsilon-based comparison (e.g., `abs(current - target) < 0.01` or directional check).

# Delivery Steps

### ✓ Step 1: Add models, migration, and admin registration
Create `WatchlistEntry` and `Notification` models, generate migration, and register in Django Admin.
- Add `WatchlistEntry` model to `dashboard/models.py` with fields: user, share, target_price, condition (above/below), notified flag, created_at. Unique constraint on (user, share).
- Add `Notification` model to `dashboard/models.py` with fields: user, share, message, created_at.
- Run `python manage.py makemigrations` to generate `0008_watchlist_and_notifications.py`.
- Register both models in `dashboard/admin.py` with appropriate list_display, list_filter, and search_fields.

### ✓ Step 2: Implement watchlist views, forms, URLs, and templates
Add the full watchlist management UI — list, create, delete, reset, and notifications pages.
- Create `WatchlistEntryForm` in `dashboard/forms.py` with fields: share (ModelChoiceQueryset), target_price (DecimalField), condition (ChoiceField: above/below).
- Add views to `dashboard/views.py`: `WatchlistListView` (ListView, filtered by request.user), `WatchlistCreateView` (CreateView), `WatchlistDeleteView` (DeleteView), `WatchlistResetView` (View to reset notified flag), `NotificationListView` (ListView, filtered by request.user). All protected with `IsUserAuthenticatedMixin`.
- Add URL patterns to `dashboard/urls.py`: `watchlist/`, `watchlist/add/`, `watchlist/remove/<pk>/`, `watchlist/reset/<pk>/`, `notifications/`.
- Create `watchlist.html` template (extends base.html) with a table showing share, current price, target price, condition, status (notified/not), and actions (reset, remove).
- Create `notification_list.html` template with a list of notifications (share, message, timestamp).
- Update `base.html` to add "Watchlist" and "Notifications" nav links (visible only to authenticated users).

### ✓ Step 3: Integrate watchlist checking into Celery task and add REST API
Extend the Celery price update task to check watchlist conditions and create notifications. Add REST API endpoints.
- Modify `update_last_price()` in `dashboard/tasks.py`: after updating share prices, iterate over all `WatchlistEntry` objects where `notified=False`. For each entry, check if the share's new `last_price` meets the condition (above/below target). If met, create a `Notification` and set `notified=True`. Use `bulk_update` for efficiency.
- Add `WatchlistEntrySerializer` and `NotificationSerializer` to `dashboard/api/v1/serializer.py`.
- Add `WatchlistEntryViewSet` (filtered by request.user) and `NotificationViewSet` to `dashboard/api/v1/views.py`.
- Register new ViewSets in `dashboard/api/v1/router.py`.
- Verify the complete flow: add watchlist entry → trigger price update → notification created → no duplicate on next update → reset re-arms the alert.