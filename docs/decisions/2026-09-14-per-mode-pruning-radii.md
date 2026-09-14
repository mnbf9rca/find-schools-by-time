# Prune origins per mode: 90 km for transit, 25 km for bike, 136 km for car

Date: September 14, 2026

## Decision

Each school's search sends only the origins within its mode's radius: 90 kilometres for public transport with the direct walk, 25 kilometres for cycling and 136 kilometres for driving. No request carries more than 20,000 origins.

## Why

`fixtures/measure_reach.py` measured the whole England grid against the combined graph, arriving at 08:30 on Wednesday September 16, 2026, with a 5,400 second cap on every mode. Over four schools chosen for contrast, St Marylebone in central London, North Liverpool Academy, rural Cottesloe and island Medina, the furthest reachable origin was 81.2 kilometres by public transport, 22.1 by bike and 122.8 by car. A ten percent margin on those distances gives 89.331, 24.356 and 135.085 kilometres, rounded up to the whole kilometres above.

Those radii leave about 25,000 origins per school for public transport, 1,900 for cycling and 51,000 to 57,000 for driving. That projects the full run over 4,373 schools at 5.1 hours on one worker or 1.2 hours on eight, with the server peaking at 8.8 GB resident at eight concurrent requests. Across 36 school and mode runs at these radii, pruning lost no origin that the unpruned grid had found.

The batch size is not a preference. MOTIS resets the connection on request bodies above roughly 24,000 origins and logs "body limit exceeded", even with `onetomany_max_many` set to 200,000. Batching at 20,000 stays clear of that edge.

## Open points

Four schools do not prove that the radii hold everywhere. The validator in issue #18 checks the published dataset for any origin reachable from beyond its mode's radius, which is what would catch a school this sample did not represent.
