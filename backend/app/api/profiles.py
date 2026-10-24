from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_csrf
from app.core.database import get_db
from app.models.entities import AuditEvent, IdentityProfile, User
from app.schemas.profiles import ProfileCreate, ProfileRead, ProfileUpdate, SearchPlanRead
from app.services.search_strategy import SearchMode, build_search_plan

router = APIRouter(prefix="/profiles", tags=["identités"])


def _owned(profile_id: str, user: User, db: Session) -> IdentityProfile:
    profile = db.scalar(
        select(IdentityProfile).where(
            IdentityProfile.id == profile_id, IdentityProfile.owner_id == user.id
        )
    )
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    return profile


def _data(payload: ProfileCreate | ProfileUpdate) -> dict[str, object]:
    return payload.model_dump(mode="json")


@router.get("", response_model=list[ProfileRead])
def list_profiles(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[IdentityProfile]:
    return list(
        db.scalars(
            select(IdentityProfile)
            .where(IdentityProfile.owner_id == user.id)
            .order_by(IdentityProfile.created_at.desc())
        )
    )


@router.post(
    "",
    response_model=ProfileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_profile(
    payload: ProfileCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> IdentityProfile:
    profile = IdentityProfile(owner_id=user.id, **_data(payload))
    db.add(profile)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="profile.create",
            resource_type="profile",
            resource_id=profile.id,
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> IdentityProfile:
    return _owned(profile_id, user, db)


@router.get("/{profile_id}/search-strategy", response_model=SearchPlanRead)
def preview_search_strategy(
    profile_id: str,
    mode: SearchMode = SearchMode.STANDARD,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchPlanRead:
    plan = build_search_plan(_owned(profile_id, user, db), mode)
    return SearchPlanRead.model_validate(plan, from_attributes=True)


@router.put("/{profile_id}", response_model=ProfileRead, dependencies=[Depends(require_csrf)])
def update_profile(
    profile_id: str,
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IdentityProfile:
    profile = _owned(profile_id, user, db)
    for key, value in _data(payload).items():
        setattr(profile, key, value)
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="profile.update",
            resource_type="profile",
            resource_id=profile.id,
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.delete(
    "/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
def delete_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    profile = _owned(profile_id, user, db)
    resource_id = profile.id
    db.delete(profile)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=user.id,
            action="profile.delete",
            resource_type="profile",
            resource_id=resource_id,
        )
    )
    db.commit()
