# Verification Checklist

Use this checklist to verify all features are working correctly after starting the application.

---

## Prerequisites

- [ ] Backend server running: `cd backend && uvicorn server:app --reload`
- [ ] Frontend dev server running: `cd frontend && npm run dev`
- [ ] Sample data generated (if first time)
- [ ] Browser open at `http://localhost:5173`

---

## 1. Financial Health Score

### Overview Dashboard
- [ ] Navigate to Overview (Home) page
- [ ] **"Financial Health Score & Needs Attention"** section visible
- [ ] Health score card displays on the left side

### Health Score Card
- [ ] Overall score (0-100) is displayed
- [ ] Status badge shows: excellent/good/fair/poor
- [ ] Overall explanation text is present
- [ ] 6 component scores are listed:
  - [ ] Cash Flow Stability
  - [ ] Revenue Stability
  - [ ] Payment Success Rate
  - [ ] Reconciliation Health
  - [ ] Refund Risk
  - [ ] Forecast Risk
- [ ] Each component shows:
  - [ ] Score value
  - [ ] Weight percentage
  - [ ] Explanation text
  - [ ] Color-coded status
- [ ] Calculation method shown at bottom
- [ ] All scores are between 0-100

### Backend API
- [ ] Open: `http://localhost:8000/api/health/score`
- [ ] Returns JSON with `overall_score`
- [ ] Returns 6 components
- [ ] Status field present

---

## 2. Proactive AI Alerts

### Needs Attention Section
- [ ] "Needs Attention" section displays on Overview page
- [ ] Alert count shown (e.g., "3 alerts")
- [ ] Alerts displayed in cards
- [ ] If no alerts: Green success card with "No critical alerts"

### Alert Cards
For each alert:
- [ ] Severity badge visible (critical/high/medium/low)
- [ ] Category label shown (Cash Flow, Revenue, etc.)
- [ ] Alert title is clear
- [ ] Explanation text describes the issue
- [ ] Metric label and value displayed
- [ ] Recommended action text present
- [ ] "Investigate" button present
- [ ] Clicking button navigates to correct screen
- [ ] Alerts sorted by severity (critical first)

### Backend API
- [ ] Open: `http://localhost:8000/api/health/alerts`
- [ ] Returns array of alerts
- [ ] Each alert has severity, title, explanation, metric, action
- [ ] Alerts sorted by severity

---

## 3. Enhanced AI CFO Insights

### Overview Page Insights
- [ ] "AI CFO insights" section visible
- [ ] 3 insight cards displayed
- [ ] Each card shows:
  - [ ] Severity badge
  - [ ] Classification (fact/prediction)
  - [ ] Category
  - [ ] Title
  - [ ] Summary
  - [ ] Metric value
  - [ ] **TWO action buttons**:
    - [ ] "Ask Why" button
    - [ ] Screen-specific button (e.g., "Review Queue", "View Forecast")
- [ ] Clicking "Ask Why" navigates to `/cfo`
- [ ] Clicking screen button navigates to correct page

### AI CFO Page Insights
- [ ] Navigate to AI CFO page
- [ ] Daily Financial Brief section visible
- [ ] 5 insight cards displayed
- [ ] Each card has dual CTAs:
  - [ ] "Ask Why" button
  - [ ] Specific action link (e.g., "Review Failures", "Analyze Refunds")
- [ ] Links navigate to appropriate screens

---

## 4. AI CFO Upgrade

### Chat Interface
- [ ] AI CFO page loads
- [ ] Chat interface visible
- [ ] Suggested questions displayed
- [ ] "Safe by design" card present

### Ask a Question
- [ ] Type a question (e.g., "What should I be concerned about today?")
- [ ] Click "Ask CFO"
- [ ] Response appears with sections:
  - [ ] Mode badge (deterministic/ollama)
  - [ ] Read-only indicator
  - [ ] Answer text
  - [ ] **Recorded facts** section
  - [ ] **Predictions** section
  - [ ] **Reasoning** section
  - [ ] **Recommendations** section
  - [ ] **Sources used** section with tool names
  - [ ] Source references listed
  - [ ] Provider message at bottom

### Verify AI Safety
- [ ] Mode is "deterministic" or "ollama"
- [ ] Facts and predictions are separated
- [ ] No financial numbers in answer that aren't from tools
- [ ] All statements have source references
- [ ] "Read only" badge present
- [ ] Provider message confirms no LLM calculations

---

## 5. Forecast Explanation

### Forecast Page
- [ ] Navigate to Cash Flow Forecast page
- [ ] Select horizon (7, 30, or 90 days)
- [ ] Forecast chart displays
- [ ] Scroll down past risks section

### "What's Driving This Forecast?" Card
- [ ] Section visible below risks
- [ ] "Forecast Analysis" heading
- [ ] 5-7 drivers displayed
- [ ] Each driver shows:
  - [ ] Category (Income, Expenses, Net Change, Risk)
  - [ ] Impact badge (positive/negative/neutral)
  - [ ] Label
  - [ ] Value (formatted currency)
  - [ ] Explanation text

### "How Confident Is This Forecast?" Card
- [ ] Confidence card displayed below drivers
- [ ] Confidence explanation paragraph present
- [ ] Confidence factors list shown (4-5 items)
- [ ] "Understanding the uncertainty range" section at bottom
- [ ] Uncertainty explanation text present

### Backend API
- [ ] Open: `http://localhost:8000/api/forecast/30/explanation`
- [ ] Returns JSON with `drivers` array
- [ ] Returns `confidence_explanation`
- [ ] Returns `confidence_factors` array
- [ ] Returns `uncertainty_range_explanation`

---

## 6. Financial Consistency

### Data Validation
- [ ] Navigate to Overview page
- [ ] Check Current Balance metric
- [ ] Navigate to Forecast page
- [ ] Current cash balance should match Overview
- [ ] Navigate to Reconciliation page
- [ ] Matched + exceptions should equal total transactions
- [ ] Navigate to AI CFO page
- [ ] Ask: "What is my current cash balance?"
- [ ] Value should match Overview and Forecast

### Calculation Verification
- [ ] All currency values display in ₹ format
- [ ] No negative balances (unless expected)
- [ ] Forecast ending balance is reasonable
- [ ] Health score components sum to 100% weight
- [ ] Alert metric values match insight values

---

## 7. UI/UX Consistency

### Visual Design
- [ ] Rose accent color used consistently (#e11d48)
- [ ] Slate neutrals for text
- [ ] Emerald for positive/success
- [ ] Amber for warnings
- [ ] Typography matches existing pages
- [ ] Spacing consistent with other sections
- [ ] Border radius matches existing cards
- [ ] Shadow depths consistent

### Navigation
- [ ] All links work correctly
- [ ] Back button functions properly
- [ ] Breadcrumbs (if present) are correct
- [ ] No broken navigation

### Responsiveness
- [ ] Test on desktop (>1280px)
- [ ] Test on tablet (768-1279px)
- [ ] Test on mobile (320-767px)
- [ ] Cards stack properly on small screens
- [ ] Text remains readable
- [ ] No horizontal scrolling

---

## 8. Safety Verification

### Backend Calculations
- [ ] Health score is deterministic (refresh page → same score)
- [ ] Alerts are consistent (refresh page → same alerts)
- [ ] Forecast explanation is consistent
- [ ] No random LLM-generated numbers

### AI CFO Safety
- [ ] AI never shows financial numbers not from tools
- [ ] Facts section only shows recorded data
- [ ] Predictions section labeled as predictions
- [ ] If data insufficient, explicitly states so
- [ ] Sources always provided
- [ ] Read-only badge always present

### Financial Integrity
- [ ] No write operations from AI CFO
- [ ] All calculations traceable
- [ ] Source references accurate
- [ ] No unexplained financial changes

---

## Testing Checklist Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Health Score Display | ⬜ | |
| Health Score Calculation | ⬜ | |
| Alerts Display | ⬜ | |
| Alerts Detection | ⬜ | |
| Enhanced Insights CTAs | ⬜ | |
| AI CFO Tool Architecture | ⬜ | |
| AI CFO Safety | ⬜ | |
| Forecast Explanation Display | ⬜ | |
| Forecast Drivers | ⬜ | |
| Forecast Confidence | ⬜ | |
| Financial Consistency | ⬜ | |
| UI/UX Consistency | ⬜ | |
| Backend APIs | ⬜ | |
| Type Safety | ⬜ | |
| Responsiveness | ⬜ | |

---

## Issue Reporting

If any checkbox fails, note:
1. **Feature**: Which feature failed
2. **Expected**: What should happen
3. **Actual**: What actually happened
4. **Steps**: How to reproduce
5. **Browser**: Browser and version
6. **Console**: Any console errors

---

## Success Criteria

All checkboxes must be ✅ for successful verification.

**Status:** ⬜ Not Started | 🟨 In Progress | ✅ Complete
