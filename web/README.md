# Web (`web`)

> This part is super in progress (the least component I've worked on). Was vibecoded using [Stitch](https://stitch.withgoogle.com/projects/11911733043970495332)!

## a) System architecture
- React + TypeScript SPA built with Vite.
- UI is served by Nginx in containerized runs.
- Frontend calls backend API routes under `/api/v1`.

## b) Setup commands
```bash
# Install deps
cd web && npm install

# Local frontend dev server
npm run dev

# Production build + preview
npm run build
npm run preview
```

## c) Why these technologies
- **React**: component model for interactive chat/document UI.
- **TypeScript**: safer refactors and better IDE support.
- **Vite**: very fast startup and rebuilds for local development.
- **Nginx**: lightweight static hosting for production image delivery.
