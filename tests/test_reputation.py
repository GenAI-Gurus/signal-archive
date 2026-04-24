import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reputation.scorer import compute_reputation_score


def test_high_reuse_high_useful_flags_scores_well():
    score = compute_reputation_score(
        total_contributions=10,
        total_reuse_count=40,
        useful_flags=20,
        stale_flags=1,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert score > 40.0
    assert score <= 100.0


def test_zero_contributions_scores_zero():
    score = compute_reputation_score(
        total_contributions=0,
        total_reuse_count=0,
        useful_flags=0,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert score == 0.0


def test_high_wrong_flags_penalizes_score():
    score_bad = compute_reputation_score(
        total_contributions=5,
        total_reuse_count=5,
        useful_flags=0,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=10,
    )
    score_good = compute_reputation_score(
        total_contributions=5,
        total_reuse_count=5,
        useful_flags=10,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert score_bad < score_good


def test_score_is_clamped_to_0_100():
    score = compute_reputation_score(
        total_contributions=1,
        total_reuse_count=1000,
        useful_flags=1000,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert 0.0 <= score <= 100.0


def test_no_flags_gives_neutral_flag_ratio():
    # No flags → flag_ratio = 0.5 → contributes 2.5 to raw score
    score = compute_reputation_score(
        total_contributions=10,
        total_reuse_count=10,  # reuse_ratio=1.0 → contributes 10
        useful_flags=0,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=0,
    )
    assert abs(score - 12.5) < 0.001  # 10 + 2.5


def test_all_wrong_flags_zeroes_flag_ratio():
    # All wrong → flag_ratio = 0 → contributes 0 to raw score
    score = compute_reputation_score(
        total_contributions=5,
        total_reuse_count=0,  # reuse_ratio = 0
        useful_flags=0,
        stale_flags=0,
        weakly_sourced_flags=0,
        wrong_flags=5,
    )
    assert score == 0.0
