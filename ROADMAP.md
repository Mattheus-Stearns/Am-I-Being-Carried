# Rocket League In-Game Win Predictor & Coaching AI
## System Architecture and Execution Blueprint

This document outlines the end-to-end development plan for building a live, in-game win probability model and an automated, explainable AI coaching layer for Rocket League.

---

## Phase 1: The Predictor Layer (The Foundation)
The objective is to establish a robust mathematical baseline that processes game snapshots and outputs a continuous win probability from `0.0` (0%) to `1.0` (100%).

### 1. Data Aggregation & Structuring
*   **Temporal Snapshots:** Convert variable frame-rate replay data into unified, sequential **1-second increments**.
*   **The Target Variable ($Y$):** Map the final match outcome to every historical row of that specific match. 
    *   `1` = Blue Team eventually won the match.
    *   `0` = Orange Team eventually won the match.
*   **Unified Rows:** Combine all individual player statistics and ball physics metrics into a single flat row per second.

### 2. Preventing Data Leakage
*   **Group-Based Splitting:** When splitting your dataset into training (80%) and testing (20%) sets, **split strictly by unique Match IDs / Replay IDs**.
*   *Why:* Grouping by rows allows the model to cheat by memorizing the progression of an identical match across both sets, ruining validation accuracy.

### 3. Model Architecture
*   **Algorithm:** Use gradient-boosted decision trees (**XGBoost** or **LightGBM**).
*   **Configuration:** 
    *   `objective='binary:logistic'`
    *   `eval_metric='logloss'`
*   **Inference:** Use `predict_proba()` to retrieve a real-time decimal probability instead of a hard binary 1 or 0 prediction.

---

## Phase 2: The Explainer Layer (The Diagnostic Engine)
Once the predictor accurately understands what states lead to a win, the explainer calculates individual feature weights to determine *why* a team is struggling or succeeding.

### 1. SHAP (SHapley Additive exPlanations) Integration
*   Initialize a `shap.TreeExplainer` using your fully trained gradient boosting model.
*   Pass the live 1-second feature vectors into the explainer to calculate exact directional impact percentages for every input feature.

### 2. Feature Isolation
*   Isolate the SHAP values strictly corresponding to the target player being coached (e.g., `p1_boost`, `p1_dist_to_ball`).
*   Identify features driving the most **negative directional impact**. A heavily negative SHAP score maps directly to the specific behavior tanking the team's live win percentage.

---

## Phase 3: UI & Coaching Logic (The Interface)
This layer translates statistical anomalies and mathematical feature drops into digestible, actionable instructions for a human player.

### 1. Translation Dictionary Mapping
Map your raw Pandas dataframe feature strings directly to human-readable gaming concepts:
*   `p1_boost` $ightarrow$ "Boost Management & Resource Economy"
*   `p1_dist_to_ball` (Defending) $ightarrow$ "Shadow Proximity & Defensive Spacing"
*   `p1_velocity_z` $ightarrow$ "Recovery Velocity & Groundedness"

### 2. Incident Trigger Thresholds
*   Prevent UI alert spamming by ignoring single-frame or single-second statistical blips.
*   Implement a rolling window or a counter (e.g., if a player's `p1_boost` SHAP value is lower than `-0.08` for **3 consecutive seconds**, flag a "Coaching Incident").

### 3. Interface Delivery Models
*   **Post-Game Timeline (Recommended Milestone 1):** Present an interactive line chart tracking the win probability throughout the match. Place clickable markers on the timeline where severe dips occurred, displaying coaching cards explaining what the player did wrong.
*   **Live Text Overlay (Recommended Milestone 2):** Connect a background Python script to a live gameplay feed (via a BakkesMod C++ plugin or websocket) and render clean hud alerts like `[AI COACH]: Collect small pads` or `[AI COACH]: Rotate out, teammate is pushing`.

---

## Next Steps & Data Verification

To proceed with writing the training scripts, we must align the pipeline with your existing parsed data structures. Please provide answers or samples for the following details:

### 1. Match Type Scope
*   Are you optimizing this system for **1v1, 2v2, or 3v3** match formatting? 
*   *Note: 1v1 models are much simpler as they omit team spacing and rotation features, whereas 3v3 requires sophisticated positioning metrics.*

### 2. Current Dataframe Schema
What are the exact column names currently available in your Pandas dataframes? Specifically, confirm if you have parsed:
*   **Player Positionals:** Spatial coordinates (`x`, `y`, `z`) and velocities (`vx`, `vy`, `vz`) for all cars?
*   **Ball Metrics:** Spatial coordinates (`ball_x`, `ball_y`, `ball_z`) and vectors?
*   **Resource Tracking:** Exact individual boost percentages (`0-100`) per frame?
*   **Metadata:** Unique match identifier column and temporal tracking (`time_remaining` or `frame_number`)?
