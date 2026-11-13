# EV Mobility React frontend

This is the new React + TypeScript customer-facing frontend workspace. It is intentionally separate from the existing `web/`, `backend/` and `flutter_app/` directories so the current site and services remain untouched while the new UI is reviewed.

## Requirements
- Node.js 20+
- npm 10+

## Run locally
```bash
cd frontend
npm install
npm run dev
```

## Production build
```bash
npm run build
npm run preview
```

## Current scope
- Customer home dashboard and shared design system
- Ride & Earn entry point (UI prototype)
- Rent an EV entry point (UI prototype)
- Nearby charging station discovery entry point (UI prototype)
- Activity and account navigation (UI prototype)

The current release uses local mock data only. It does not submit real ride/rental bookings, process payments, authenticate against the backend, or provide live GPS tracking. Those capabilities will be connected in later phases.
