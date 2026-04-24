def compute_reputation_score(
    total_contributions: int,
    total_reuse_count: int,
    useful_flags: int,
    stale_flags: int,
    weakly_sourced_flags: int,
    wrong_flags: int,
) -> float:
    if total_contributions == 0:
        return 0.0

    reuse_ratio = total_reuse_count / total_contributions
    total_flags = useful_flags + stale_flags + weakly_sourced_flags + wrong_flags
    if total_flags == 0:
        flag_ratio = 0.5  # neutral when no flags
    else:
        weighted = useful_flags - wrong_flags
        flag_ratio = (weighted + total_flags) / (2 * total_flags)  # normalised to [0, 1]

    raw = reuse_ratio * 10 + flag_ratio * 5
    return max(0.0, min(100.0, raw))
