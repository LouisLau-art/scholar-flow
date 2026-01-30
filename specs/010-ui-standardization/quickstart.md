# Quickstart Guide: UI Standardization

## Prerequisites

- Node.js 20+
- Python 3.11+ (for backend if running full stack)

## Setup

1. **Install Dependencies** (New Shadcn dependencies):
   ```bash
   cd frontend
   npm install
   ```

2. **Run Development Server**:
   ```bash
   npm run dev
   ```

## Verification Steps

### 1. Decision Panel (Manual)
1. Log in as an Editor.
2. Navigate to a manuscript detail page or the decision route.
3. Verify the "Decision" section uses a **Radio Group** (clickable cards) instead of simple buttons.
4. Verify the "Submit" button uses the standard UI style (blue background, white text).
5. **Check Contrast**: Ensure text is clearly visible in both "Selected" and "Unselected" states.
6. **State Precedence**: Select an option, then hover over it. Ensure it STAYS selected (dark background) and doesn't revert to hover style (light grey).

### 2. Component Styles
1. Check `Tabs` on any dashboard page.
2. Verify they have the standard "Slate" look (active: white bg, dark text).

### 3. Light Mode Enforcement
1. Change system theme to Dark Mode.
2. Verify the application **does NOT** change appearance (stays in Light Mode).

### 4. Automated Tests
Run the frontend test suite to ensure no regressions:
```bash
cd frontend
npm run test
```