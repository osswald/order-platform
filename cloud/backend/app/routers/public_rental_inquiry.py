"""Unauthenticated public Mietanfrage endpoint for the marketing site."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from ..i18n.errors import api_error
from ..rate_limit import RENTAL_INQUIRY_RATE_LIMIT, limiter
from ..rental_inquiry_mail import RentalInquiryMailError, send_rental_inquiry_email
from ..schemas.rental_inquiry import RentalInquiryCreate

router = APIRouter(prefix="/public", tags=["public"])


@router.post(
    "/rental-inquiry",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
@limiter.limit(RENTAL_INQUIRY_RATE_LIMIT)
def create_rental_inquiry(request: Request, payload: RentalInquiryCreate) -> Response:
    if payload.website.strip():
        # Silent success for bots; do not send mail.
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        send_rental_inquiry_email(
            name=payload.name,
            organisation=payload.organisation,
            email=str(payload.email),
            phone=payload.phone,
            timeframe=payload.timeframe,
            message=payload.message,
        )
    except RentalInquiryMailError:
        raise api_error(
            "rental_inquiry_mail_unavailable",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from None

    return Response(status_code=status.HTTP_204_NO_CONTENT)
