import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from database import get_db
from models import ResearchArtifact, Contributor
from schemas import ArtifactSubmit, ArtifactResponse
from embeddings import get_embedding
from canonical import find_or_create_canonical
from auth import hash_api_key
from quality import compute_quality_score

logger = logging.getLogger(__name__)

router = APIRouter(tags=["artifacts"])

async def get_contributor_from_key(api_key: str, db: AsyncSession) -> Contributor:
    key_hash = hash_api_key(api_key)
    result = await db.execute(select(Contributor).where(Contributor.api_key_hash == key_hash))
    contributor = result.scalar_one_or_none()
    if not contributor:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return contributor

@router.post("", status_code=201)
async def submit_artifact(
    body: ArtifactSubmit,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")

    contributor = await get_contributor_from_key(x_api_key, db)
    embedding = await get_embedding(body.cleaned_question)

    # Phase 1: fail fast before creating a canonical — artifact must exist
    if body.supersedes_id is not None:
        pre_check = await db.execute(
            select(ResearchArtifact).where(ResearchArtifact.id == body.supersedes_id)
        )
        if not pre_check.scalar_one_or_none():
            raise HTTPException(
                status_code=422,
                detail=f"supersedes_id {body.supersedes_id} does not refer to an existing artifact",
            )

    canonical_id, _ = await find_or_create_canonical(
        db=db,
        question=body.cleaned_question,
        embedding=embedding,
        summary=body.short_answer,
    )

    # Auto-supersede: if this contributor already has a non-superseded artifact on this
    # canonical and the client didn't explicitly set supersedes_id, link automatically.
    if body.supersedes_id is None:
        already_superseded = select(ResearchArtifact.supersedes_id).where(
            ResearchArtifact.supersedes_id.isnot(None)
        )
        prev_result = await db.execute(
            select(ResearchArtifact.id)
            .where(
                ResearchArtifact.canonical_question_id == canonical_id,
                ResearchArtifact.contributor_id == contributor.id,
                ~ResearchArtifact.id.in_(already_superseded),
            )
            .order_by(ResearchArtifact.created_at.desc())
            .limit(1)
        )
        prev_id = prev_result.scalar_one_or_none()
        if prev_id:
            body.supersedes_id = prev_id

    # Phase 2: explicitly-provided supersedes_id must belong to the resolved canonical
    if body.supersedes_id is not None:
        result = await db.execute(
            select(ResearchArtifact).where(
                ResearchArtifact.id == body.supersedes_id,
                ResearchArtifact.canonical_question_id == canonical_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=422,
                detail=f"supersedes_id {body.supersedes_id} must refer to an artifact in the same canonical question",
            )

    artifact = ResearchArtifact(
        id=uuid.uuid4(),
        canonical_question_id=canonical_id,
        contributor_id=contributor.id,
        cleaned_question=body.cleaned_question,
        cleaned_prompt=body.cleaned_prompt,
        clarifying_qa=[qa.model_dump() for qa in body.clarifying_qa],
        short_answer=body.short_answer,
        full_body=body.full_body,
        citations=[c.model_dump() for c in body.citations],
        run_date=body.run_date,
        worker_type=body.worker_type,
        model_info=body.model_info,
        source_domains=body.source_domains,
        prompt_modified=body.prompt_modified,
        version=body.version,
        supersedes_id=body.supersedes_id,
        embedding=embedding,
    )
    db.add(artifact)
    await db.execute(
        text("UPDATE contributors SET total_contributions = total_contributions + 1 WHERE id = :id"),
        {"id": str(contributor.id)},
    )
    await db.commit()
    await db.refresh(artifact)

    try:
        score = await compute_quality_score(
            source_domains=artifact.source_domains or [],
            full_body=artifact.full_body,
            short_answer=artifact.short_answer,
        )
        await db.execute(
            text("UPDATE research_artifacts SET quality_score = :score WHERE id = :id"),
            {"score": score, "id": str(artifact.id)},
        )
        await db.commit()
    except Exception:
        logger.warning("Quality scoring failed for artifact %s", artifact.id, exc_info=True)

    return {"id": str(artifact.id), "canonical_question_id": str(canonical_id)}

@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchArtifact).where(ResearchArtifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact
