from dataclasses import dataclass
from typing import List
from cascade.diff_parser import FileDiff

@dataclass
class RoutingDecision:
    tier: str
    reason: str
    total_lines: int

def route(files: List[FileDiff], config: dict) -> RoutingDecision:
    total = sum(f.total_changes for f in files)
    routing = config.get("routing", {})

    force = routing.get("force_tier", "auto")
    if force != "auto":
        return RoutingDecision(tier=force, reason=f"forced via config", total_lines=total)

    local_max = routing.get("local_max_lines", 50)
    mid_max = routing.get("mid_max_lines", 200)

    if total <= local_max:
        return RoutingDecision(tier="local", reason=f"{total} lines — local threshold ({local_max})", total_lines=total)
    elif total <= mid_max:
        return RoutingDecision(tier="mid", reason=f"{total} lines — mid threshold ({mid_max})", total_lines=total)
    else:
        return RoutingDecision(tier="frontier", reason=f"{total} lines — exceeds mid threshold ({mid_max})", total_lines=total)
