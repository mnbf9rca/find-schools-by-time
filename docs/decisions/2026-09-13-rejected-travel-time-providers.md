# Rejected hosted travel-time providers and live per-search routing

Date: September 13, 2026

## Decision

No hosted travel-time API is used for the public site, and travel times are not computed live at search time. This record exists so the options below are not reopened without new information.

## Why

Treating the site as commercial, because it carries ads, removes most free tiers, and none of the survivors gives England-wide public transport, a fixed 08:30 arrival and a large destination list at the same time.

- **TravelTime**, the provider the local prototype uses, stays local. Its free plan is for evaluation only and forbids use by end users, so it cannot serve a public site.
- **Geoapify** fails on both of its relevant endpoints. The Isoline API has no departure or arrival time parameter, so it answers "within N minutes of roughly now" rather than "arrive by 08:30", and its transit coverage outside official GTFS areas is an approximated model. The Route Matrix API supports driving, truck and walking only, with no transit mode.
- **Google Routes `computeRouteMatrix`** has the correct semantics, including transit and a fixed arrival time, but transit requests cap at 100 elements, so one search across 2,000 schools costs about $10 at list price.
- **Targomo** supports transit in both isochrones and matrices and offers free monthly usage for publicly accessible applications, but its terms forbid permanently caching or storing results for reuse, which rules out precomputing.
- **Stadia Maps** and **Transitous** both exclude commercial use on their free offerings, so the ads disqualify them.
- **Mapbox**, **HERE** and **hosted OpenRouteService** have no transit matrix at all. Mapbox and HERE support driving, walking, cycling and, for HERE, truck; HERE's public transit lives in a separate point-to-point API. OpenRouteService's `public-transport` profile exists only in self-hosted builds with GTFS loaded.

Live per-search routing against our own engine is rejected separately. It would require running a server continuously, which is the operational cost this project is avoiding, and it would buy nothing: the answer for a given origin only changes when the timetables change, so recomputing it on every visit repeats identical work.

See `docs/superpowers/research/2026-09-13-public-deployment-providers.md` for the full provider comparison, the pricing sources and the one-off cost arithmetic.
