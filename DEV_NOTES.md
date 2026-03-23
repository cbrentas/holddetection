# Hold Detection - Developer Notes

This document contains key architectural developer notes added during the creation of the Phase 7 routing system.

## Core Product Architecture

### Why RouteHolds reference WallHolds instead of duplicating geometry
By designing `RouteHold` as a simple relational table that references a specific `wall_hold_id`, we guarantee that there is a single source of truth for the hold geometry. If the wall is updated later (e.g., holds are refined or adjusted), all routes that depend on that wall implicitly inherit the new, correct geometry. We avoid desynchronization between walls and routes.

### Why predictions remain raw ML output
The system preserves raw YOLO ML predictions without mutating them during user edits. This is essential to ensure that we always have a ground truth of the machine learning model's raw performance. `WallHold` records are initialized from predictions but become the editable representation of geometry. This clear boundary means we can use the edited `WallHolds` as verified datasets to retrain our ML models in the future.

### Support for sharing, mobile, and offline caching
The separation of the stable `Wall` object from the lightweight `Route` object implies that downloading a route locally on a mobile device only requires fetching the stable wall information once. When sharing or discovering new routes on the same wall, users only need to download lightweight metadata and relational ids. The system is therefore inherently positioned to support strong offline caching effectively.

## Source of Truth Rules

- **Backend is the source of truth for**:
  - `walls`
  - `wall_holds`
  - `routes`
  - `route_holds`
- **Frontend must never maintain independent state** that diverges from the backend. The frontend UI operates merely as a visualization and editor for what the backend contains.
- **Route membership must always be derived from backend responses**.
- **The `/walls/{id}/routes/full` endpoint is the canonical snapshot** for caching and offline use, delivering the full structured representation of a wall's routing state.
