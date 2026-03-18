PROJECT: HOLD DETECTION PLATFORM — IMPLEMENTATION PLAN
CONTEXT:
Current implementation already has:
- FastAPI backend
- PostgreSQL database
- Alembic migrations
- Async job model (uploads -> jobs -> worker)
- YOLO-based inference worker
- Predictions stored in DB
- Basic auth via env vars
- Local VPS storage folders
- Hetzner VPS deployment target

PRIMARY GOAL RIGHT NOW:
Build an ML-first web system where a user can:
1. upload a wall photo
2. trigger inference
3. view the labeled output image
4. inspect prediction/training stats and results
5. keep the system structured so retraining and future product features are straightforward

IMPORTANT PRINCIPLES:
1. Do not optimize for mobile app yet.
2. Do not overbuild the route editor yet.
3. Treat annotated result images as preview artifacts, not the source of truth.
4. Keep raw predictions separate from future user-edited wall objects.
5. Do not store images in the DB.
6. Use local VPS filesystem now, but design storage abstraction so S3-compatible storage can replace it later.
7. Keep API, worker, training metadata, and storage modular.

==================================================
PHASE 0 — STABILIZE CURRENT FOUNDATION
GOAL:
Make the current pipeline reliable, consistent, and presentable.

TASKS:
0.1 Clean repo structure
- ensure folders are clearly separated:
  - app/api
  - app/core
  - app/db
  - app/services
  - app/workers
  - storage/uploads
  - storage/results
  - storage/models
  - scripts
  - alembic

0.2 Clean config management
- all secrets and runtime configuration must come from .env via settings.py
- no hardcoded credentials
- add .env.example
- ensure README explains required environment variables

0.3 Stabilize job lifecycle
- statuses must remain:
  - pending
  - running
  - succeeded
  - failed
- failed jobs must store error text
- worker must always set finished_at on completion/failure
- inference_meta should include basic runtime stats

0.4 Ensure annotated image generation works end-to-end
- worker must:
  - run inference
  - save predictions
  - save annotated output image
  - set result_annotated_uri
  - set inference_meta such as:
    - num_predictions
    - model_id
    - inference_time_ms if possible
    - image_width
    - image_height

DELIVERABLE:
A stable async inference pipeline with:
- upload endpoint
- job status endpoint
- predictions endpoint
- result image endpoint

==================================================
PHASE 1 — ML-FIRST WEB MVP
GOAL:
Create a simple browser UI for upload + result viewing.

USER EXPERIENCE:
- user opens a web page
- uploads an image
- sees job progress
- gets back labeled image
- can inspect prediction counts and basic stats

TASKS:
1.1 Build minimal web frontend
Recommended:
- simple server-rendered HTML first, or a tiny frontend page
- no framework required initially unless you want Vue immediately
- use web first, not Flutter

UI REQUIREMENTS:
- upload file input
- submit button
- loading / processing state
- job status display
- result image display
- prediction count display
- basic metadata display

1.2 Add polling flow
Frontend should:
- POST upload
- receive job_id
- poll /jobs/{job_id}
- when succeeded:
  - fetch /jobs/{job_id}/image
  - fetch /jobs/{job_id}/predictions
  - render summary

1.3 Add basic image controls
Minimum:
- image fits in container
- zoom in/out
- pan if zoomed
- toggle labels on/off if practical
- slider for image scale if easy

IMPORTANT:
This phase is about display, not editing.

DELIVERABLE:
A working ML demo on the VPS:
- upload wall photo
- see processed labeled image in browser
- see prediction JSON summary/stats

==================================================
PHASE 2 — PREDICTION + TRAINING OBSERVABILITY
GOAL:
Make the project visibly ML-centric and easy to inspect.

OBJECTIVE:
Provide minimal but impressive ML result screens:
- recent predictions
- model metrics
- training run summaries
- flashy percentages if desired, but backed by real stored data

IMPORTANT:
Do not fake metrics. You can format them nicely, but they must come from actual stored values.

TASKS:
2.1 Expand DB usage for training runs
Use existing tables:
- datasets
- training_runs
- artifacts
- models

Ensure training_runs can store:
- dataset_id
- code_version
- hyperparams JSON
- metrics JSON
- started_at
- finished_at
- status

Metrics examples:
- precision
- recall
- mAP50
- mAP50_95
- training_epochs
- loss history summary
- notes

2.2 Add training artifact registration flow
Training will still happen externally (Colab for now), but after each run you should be able to register:
- best weights path
- results plot
- confusion matrix
- sample predictions
- metrics JSON
- training notes

This can be done by:
- manual script initially
- later API endpoint or admin UI

2.3 Build ML dashboard page
Page should show:
- active model
- past model versions
- latest training runs
- selected key metrics
- simple improvement indicators

Display ideas:
- "mAP50 improved by +3.1%"
- "Recall improved by +2.4%"
- "Current active model: hold-detector v3"
- "Predictions processed: N"

2.4 Keep specifics accessible
Need drill-down:
- click training run -> see full metrics JSON
- click artifact -> see plot or file path
- click model -> see linked training run

DELIVERABLE:
A minimal ML dashboard that is useful for:
- demo
- development
- self-tracking
- future retraining decisions

==================================================
PHASE 3 — DATASET FEEDBACK LOOP
GOAL:
Make it straightforward to use real production images to improve the model.

THIS IS CRITICAL.
Your real bottleneck is data, not model family.

TASKS:
3.1 Add upload retention policy
Every uploaded wall image that is useful for retraining should be retainable.

Need concept of:
- upload accepted for dataset enrichment?
- upload reviewed?
- upload labeled?
- upload exported?

Possible future columns:
uploads:
- keep_for_training boolean
- reviewed_for_training boolean
- dataset_exported boolean
- notes text

3.2 Preserve original image + predictions
For every useful upload, keep:
- original image
- raw model predictions
- model version used
- timestamp
- optional human notes

3.3 Add export workflow for dataset building
Need a script or admin flow that can:
- list candidate uploads
- copy selected images into export folder
- export associated prediction metadata
- optionally prepare files for annotation/retraining

3.4 Prepare for human correction later
Do not build full editor yet, but design with this in mind:
- raw predictions should remain stored
- future corrected annotations should be stored separately
- later these corrected annotations become high-value retraining data

3.5 Add dataset registration
Each exported training dataset version should create a row in:
- datasets

Fields:
- name
- version
- storage_uri
- meta JSON
Examples in meta:
- num_images
- num_annotations
- source_upload_ids
- annotation_method
- exported_at

DELIVERABLE:
A repeatable path:
production uploads -> select useful data -> export -> train -> register new model

==================================================
PHASE 4 — STORAGE STRATEGY
GOAL:
Avoid storing binary image data in DB and keep future migration easy.

CURRENT RECOMMENDATION:
Use VPS filesystem now, but abstract it immediately.

DO NOT STORE IMAGES IN POSTGRES.

STORAGE PLAN:
4.1 Current storage backend: local filesystem
Use directories:
- storage/uploads
- storage/results
- storage/models
- storage/training_artifacts
- storage/datasets_exports

DB stores URIs/paths only.

4.2 Introduce storage abstraction service
Create service layer like:
- save_upload(file) -> uri
- save_result_image(image) -> uri
- save_model(file) -> uri
- save_artifact(file) -> uri
- open_file(uri) -> stream/path

Implementation 1:
- LocalStorageService

Future implementation:
- S3StorageService

4.3 Future storage target
Later migrate to S3-compatible object storage:
Options:
- Hetzner Object Storage
- self-hosted Garage
- MinIO
- Cloudflare R2

Recommendation:
- do NOT self-host complex object storage early unless needed
- easiest later target is S3-compatible object storage
- Garage or MinIO only if you explicitly want to manage infra

4.4 Migration rule
Never let business logic care whether file lives:
- on local disk
- in S3
- in object storage

Everything should use storage service interfaces.

DELIVERABLE:
Local storage now, painless object-storage migration later.

==================================================
PHASE 5 — FORMALIZE THE WALL DOMAIN OBJECT
GOAL:
Move from “job output” to “persistent wall entity”.

RATIONALE:
Users do not care about a transient inference job.
They care about saved walls.

TASKS:
5.1 Add walls table
Suggested structure:
walls
- id
- title
- original_upload_id
- latest_job_id
- original_image_uri
- preview_image_uri
- status
- created_by nullable
- created_at
- updated_at
- meta JSON

5.2 Add wall_holds table
Suggested structure:
wall_holds
- id
- wall_id
- prediction_id nullable
- source_type (model/manual)
- class_name
- confidence nullable
- x1
- y1
- x2
- y2
- center_x
- center_y
- geometry JSON
- label_text nullable
- label_x nullable
- label_y nullable
- is_hidden
- is_user_adjusted
- created_at
- updated_at

IMPORTANT:
Keep predictions table as raw inference output.
wall_holds becomes editable product state.

5.3 Create wall generation flow
After job succeeds:
- create wall record if not exists
- copy prediction results into wall_holds
- create preview image

DELIVERABLE:
A saved wall object that can later power:
- editing
- route building
- sharing
- history

==================================================
PHASE 6 — WEB ANNOTATION / EDITOR MVP
GOAL:
Allow manual refinement of ML results.

THIS IS THE START OF PRODUCT LAYER.
Do not do it before Phases 1–5 are solid.

FIRST EDITING FEATURES:
- select hold
- rename hold
- drag label position
- hide false positives
- add hold manually
- save changes

IMPORTANT DESIGN RULE:
Do not overwrite raw predictions.
Only update wall_holds.

UI REQUIREMENTS:
- image canvas
- overlay boxes / points
- selected hold panel
- editable label text
- draggable label anchor
- save button

ZOOM / DENSITY NOTE:
For dense spray walls:
- do not always show full labels for all holds
- use multiple display modes:
  - overview mode: small markers / ids
  - edit mode: detailed selected labels
- label size should scale with zoom
- hold markers should remain visible at different zoom levels

DELIVERABLE:
A usable wall annotation tool for correcting ML output.

==================================================
PHASE 7 — ROUTES / CLIMBING PRODUCT FEATURES
GOAL:
Build actual climbing functionality after the ML object model is stable.

TASKS:
7.1 Add routes table
routes
- id
- wall_id
- name
- difficulty nullable
- description nullable
- created_by nullable
- created_at
- updated_at

7.2 Add route_holds table
route_holds
- id
- route_id
- wall_hold_id
- role (start / hand / foot / finish / optional)
- order_index nullable

7.3 Add route viewer
- select holds to create route
- save route
- render route overlay on wall

7.4 Sharing
Later:
- shareable public link
- private/public visibility
- ownership model

DELIVERABLE:
The wall becomes a usable route-building object.

==================================================
PHASE 8 — APP LAYER
GOAL:
Only after web workflow is validated should this become mobile.

RATIONALE:
Web is faster for:
- annotation tooling
- debugging
- deployment
- interaction complexity

APP STRATEGY:
- keep backend API stable
- web becomes reference implementation
- mobile app later consumes same wall / hold / route APIs

DELIVERABLE:
Port, not redesign.

==================================================
PRIORITY ORDER (IMPORTANT)
DO THIS ORDER:

1. Stabilize current pipeline
2. Build upload/result web MVP
3. Build ML metrics/training dashboard
4. Build dataset feedback loop
5. Add storage abstraction
6. Add wall / wall_holds domain model
7. Add annotation/editor
8. Add route creation
9. Add sharing
10. Build mobile app

==================================================
IMMEDIATE NEXT SPRINT
FOCUS ONLY ON THIS:

SPRINT A — ML SHOWCASE MVP
Goal:
A user can upload a wall image and see the labeled result in browser, while you can inspect model/training stats.

Tasks:
A1. Finish annotated result image saving
A2. Add /jobs/{id}/image endpoint
A3. Build upload/result HTML page
A4. Build simple training/model dashboard page
A5. Add training run registration script
A6. Add storage service abstraction
A7. Clean README and repo structure

Deliverable:
A demoable ML system on VPS:
- upload image
- run async inference
- see labeled result
- inspect model/training history
- ready to iterate with more data

==================================================
WHAT NOT TO DO YET
- do not build Flutter app
- do not build full collaboration
- do not build complex auth
- do not build perfect label auto-layout
- do not switch model families prematurely
- do not move images into DB
- do not tightly couple to Google Colab

==================================================
SUCCESS DEFINITION FOR CURRENT PHASE
You are successful when:

1. A user can upload a wall photo from browser
2. The backend stores original image path, job metadata, predictions, annotated result path
3. The browser displays the labeled result image
4. You can inspect past prediction jobs and current active model
5. You can register training runs and compare basic model metrics
6. Useful uploads can be retained and exported for future retraining
7. The system remains structured enough to add wall editing later without rewrite

END OF PLAN
