from __future__ import annotations

from collections.abc import Callable

from .models import Invocation, Scenario, Transcript


def minimize_conversation(recorded: Transcript, still_fails: Callable[[Transcript], bool]) -> Transcript:
    """Delta-debug user-visible turns while retaining a reproducible failing trace."""
    turns = recorded.scenario.turns[:]
    granularity = 2
    while len(turns) > 1:
        chunk = max(1, len(turns) // granularity)
        reduced = False
        for start in range(0, len(turns), chunk):
            candidate = turns[:start] + turns[start + chunk :]
            if candidate and still_fails(
                Transcript(Scenario(recorded.scenario.name, candidate, recorded.scenario.metadata), recorded.invocation)
            ):
                turns, granularity, reduced = candidate, max(2, granularity - 1), True
                break
        if not reduced:
            if granularity >= len(turns):
                break
            granularity = min(len(turns), granularity * 2)
    return Transcript(Scenario(recorded.scenario.name, turns, recorded.scenario.metadata), recorded.invocation)


def minimize_with_replay(
    recorded: Transcript, replay: Callable[[Scenario], Invocation], still_fails: Callable[[Transcript], bool]
) -> Transcript:
    """Minimize only when each candidate is freshly replayed by the caller."""

    def verified_failure(candidate: Transcript) -> bool:
        fresh = Transcript(candidate.scenario, replay(candidate.scenario), candidate.schema_version)
        return still_fails(fresh)

    return minimize_conversation(recorded, verified_failure)
