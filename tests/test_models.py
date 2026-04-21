import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models import Contributor, CanonicalQuestion, ResearchArtifact, CommunityFlag, ReuseEvent

def test_model_table_names():
    assert Contributor.__tablename__ == "contributors"
    assert CanonicalQuestion.__tablename__ == "canonical_questions"
    assert ResearchArtifact.__tablename__ == "research_artifacts"
    assert CommunityFlag.__tablename__ == "community_flags"
    assert ReuseEvent.__tablename__ == "reuse_events"
