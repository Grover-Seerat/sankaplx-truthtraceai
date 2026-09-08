# TruthTrace Frontend Redesign

This build keeps the existing TruthTrace workflows, API contracts, roles, case scoping and forensic functionality intact while applying a restrained professional UI treatment.

## Visual direction
- Dark charcoal forensic-workstation palette rather than blue/purple SaaS styling
- Thin borders and compact rectangular surfaces
- 4–8px corner radii instead of large floating cards
- No decorative gradients, glow effects or glassmorphism
- Reduced visual noise and tighter information density
- Muted blue-grey accent with semantic green/amber/red states
- Conventional enterprise tables and navigation
- Compact forensic confidence bar instead of a decorative circular gauge

## Areas updated
- Global theme and spacing
- Application shell and sidebar
- Dashboard surfaces and primary investigation action
- Workspace header and tab strip
- Shared panels, fields, pills and metric primitives
- Simple page headers used by cases, evidence, reports, users and settings
- Authenticity confidence presentation
- Login surface

## Functional constraint
No backend APIs, authentication, authorization, role logic, database structure, forensic calculations, propagation logic, audit logic or report generation were intentionally changed as part of this visual pass.

## Run
```bash
npm install
npm run dev
```
