# Use the standard Time Filter endpoint with a computed departure time

Date: September 13, 2026

## Decision

Travel times come from TravelTime's standard `/v4/time-filter` endpoint with one departure search: departure time is 08:30 Europe/London on the next weekday minus the requested minutes, and the travel time cap is the requested minutes. A school appears exactly when you can leave home at that time and be there by 08:30.

## Why

The user's question is "which schools can I reach for an 08:30 start". The endpoint's one-origin-to-many-destinations form only takes a departure time, and its arrival-time form runs the other way (many origins to one destination), so a computed departure time is the only way to express the requirement. The Time Filter Fast endpoint was tried first because it has no destination cap, but its `weekday_morning` setting is a generic profile and cannot target a time, so it was rejected.

## Consequences

The standard endpoint caps a search at 2,000 destinations, so the server sends the 2,000 schools nearest the origin by straight-line distance. The 2,000th nearest school is about 70 miles from any London or South East origin, far beyond any hour's travel, so nothing reachable is excluded. The reported minutes count from the fixed departure time, so a school whose best train leaves later shows a slightly higher figure than a well-timed journey would take.
