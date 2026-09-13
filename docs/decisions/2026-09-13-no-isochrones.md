# Do not use isochrone polygons for reachability

Date: September 13, 2026

## Decision

Reachability is computed with a travel time matrix (one request, minutes per school), not with an isochrone polygon and local point-in-polygon filtering.

## Why

The polygon approach also needs one request and has no destination cap, but it returns only in or out, so the table could not be sorted by journey time. Point-in-polygon against shapes with holes is about twenty lines of geometry against the current join of two lists by id. After the TravelTime free trial, isochrones are limited to medium detail, so boundary cases get coarser while the matrix stays exact.
