"""Authenticated trip management API endpoints."""

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreate, TripResponse
from app.services.idempotency_execution_service import (
    IdempotencyConflictError,
    IdempotencyExecutionService,
)
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["Trips"])

DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_trip_service(db: DatabaseSession) -> TripService:
    """Build the trip service for the current request."""
    return TripService(db)


TripServiceDependency = Annotated[
    TripService,
    Depends(get_trip_service),
]


def get_idempotency_execution_service(
    db: DatabaseSession,
) -> IdempotencyExecutionService:
    """Build the idempotency service for the current request."""
    return IdempotencyExecutionService(db)


IdempotencyServiceDependency = Annotated[
    IdempotencyExecutionService,
    Depends(get_idempotency_execution_service),
]


@router.post("", response_model=TripResponse, status_code=201)
def create_trip(
    payload: TripCreate,
    current_user: CurrentUser,
    service: TripServiceDependency,
    idempotency_service: IdempotencyServiceDependency,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key"),
    ] = None,
) -> TripResponse | JSONResponse:
    """Create a trip with optional persistent idempotency protection."""

    def replay_response(record) -> JSONResponse:
        return JSONResponse(
            status_code=record.response_status,
            content=record.response_body,
        )

    # Preserve the existing behavior when no key is provided.
    if idempotency_key is None:
        trip = service.create_trip(
            user_id=current_user.id,
            origin=payload.origin,
            destination=payload.destination,
            start_date=payload.start_date,
            end_date=payload.end_date,
            travelers=payload.travelers,
            budget=payload.budget,
            currency=payload.currency,
            travel_style=payload.travel_style,
            special_requirements=payload.special_requirements,
        )
        return TripResponse.model_validate(trip)

    request_data = payload.model_dump(mode="json")

    try:
        # Reuse an existing response if this request was already completed.
        existing = idempotency_service.find_existing(
            user_id=current_user.id,
            key=idempotency_key,
            payload=request_data,
        )

        if existing is not None:
            return replay_response(existing)

        # Create the trip and audit event without committing yet.
        trip = service.create_trip(
            user_id=current_user.id,
            origin=payload.origin,
            destination=payload.destination,
            start_date=payload.start_date,
            end_date=payload.end_date,
            travelers=payload.travelers,
            budget=payload.budget,
            currency=payload.currency,
            travel_style=payload.travel_style,
            special_requirements=payload.special_requirements,
            commit=False,
        )

        response_body = TripResponse.model_validate(
            trip
        ).model_dump(mode="json")

        record, inserted = idempotency_service.store_response(
            user_id=current_user.id,
            key=idempotency_key,
            payload=request_data,
            response_status=201,
            response_body=response_body,
        )

        if inserted:
            # Commit the trip, audit event, and idempotency record together.
            db.commit()
            return JSONResponse(
                status_code=201,
                content=response_body,
            )

        # A concurrent request won the key. Discard this request's
        # uncommitted trip and audit event.
        db.rollback()

        # Reload the winning request's record after rollback.
        existing = idempotency_service.find_existing(
            user_id=current_user.id,
            key=idempotency_key,
            payload=request_data,
        )

        if existing is None:
            raise RuntimeError(
                "Idempotency record disappeared after a concurrent request"
            )

        return replay_response(existing)

    except IdempotencyConflictError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: uuid.UUID,
    current_user: CurrentUser,
    db: DatabaseSession,
) -> TripResponse:
    """Retrieve a trip only when it belongs to the authenticated user."""
    trip = TripRepository(db).get_by_id_for_user(
        trip_id=trip_id,
        user_id=current_user.id,
    )

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    return TripResponse.model_validate(trip)


@router.get("", response_model=list[TripResponse])
def list_trips(
    current_user: CurrentUser,
    service: TripServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TripResponse]:
    """List trips belonging to the authenticated user."""
    trips = service.list_user_trips(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return [TripResponse.model_validate(trip) for trip in trips]
