"""Organisation screensaver gallery API, helpers, and edge download."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import uuid4

from app.database import SessionLocal
from app.main import app
from app.models import (
    Appliance,
    ApplianceEdgeCredential,
    HireCompany,
    Organisation,
    User,
)
from app.roles import ROLE_TENANT_ADMIN
from app.screensaver_gallery import (
    MAX_SCREENSAVER_GALLERY_IMAGES,
    MAX_SCREENSAVER_IMAGE_BYTES,
    delete_screensaver_image,
    list_screensaver_manifest,
    store_screensaver_image,
)
from app.security import get_password_hash
from fastapi.testclient import TestClient

from tests.helpers import add_lending, country_id_by_code

client = TestClient(app)

# Minimal valid-looking payloads (content-type is what we validate).
PNG_A = b"\x89PNG\r\n\x1a\n" + b"a" * 64
PNG_B = b"\x89PNG\r\n\x1a\n" + b"b" * 64
JPEG_A = b"\xff\xd8\xff" + b"j" * 64
WEBP_A = b"RIFF" + b"w" * 64


def _seed_org(*, email_prefix: str = "screensaver") -> tuple[int, str]:
    suffix = uuid4().hex[:10]
    db = SessionLocal()
    try:
        hc = HireCompany(name=f"SS HC {suffix}")
        db.add(hc)
        db.flush()
        org = Organisation(
            name=f"SS Org {suffix}",
            country_id=country_id_by_code(db, "CH"),
            hire_company_id=hc.id,
            currency="CHF",
        )
        db.add(org)
        db.flush()
        email = f"{email_prefix}-{suffix}@test.local"
        db.add(
            User(
                email=email,
                hashed_password=get_password_hash("secret"),
                role=ROLE_TENANT_ADMIN,
                hire_company_id=hc.id,
            )
        )
        db.commit()
        return org.id, email
    finally:
        db.close()


def _auth_headers(email: str) -> dict[str, str]:
    r = client.post("/auth/token", data={"username": email, "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _pair_edge(org_id: int) -> dict[str, str]:
    suffix = uuid4().hex[:10]
    db = SessionLocal()
    try:
        org = db.get(Organisation, org_id)
        assert org is not None
        appliance = Appliance(
            hire_company_id=org.hire_company_id,
            type="server",
            name=f"SS Pi {suffix}",
        )
        db.add(appliance)
        db.flush()
        today = datetime.now(UTC).date()
        add_lending(
            db,
            appliance_id=appliance.id,
            organisation_id=org.id,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )
        secret = f"secret-{suffix}"
        cred = ApplianceEdgeCredential(
            appliance_id=appliance.id,
            edge_client_id=f"ss-cid-{suffix}",
            edge_secret_hash=get_password_hash(secret),
            status="active",
        )
        db.add(cred)
        db.commit()
        return {
            "X-Edge-Client-Id": cred.edge_client_id,
            "X-Edge-Secret": secret,
        }
    finally:
        db.close()


def _upload(
    org_id: int,
    headers: dict[str, str],
    raw: bytes,
    *,
    content_type: str = "image/png",
    filename: str = "img.png",
):
    return client.post(
        f"/organisations/{org_id}/screensaver-images",
        headers=headers,
        files={"file": (filename, BytesIO(raw), content_type)},
    )


def test_upload_list_and_delete_screensaver_image():
    org_id, email = _seed_org()
    headers = _auth_headers(email)

    listed = client.get(f"/organisations/{org_id}/screensaver-images", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []

    created = _upload(org_id, headers, PNG_A)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["mime"] == "image/png"
    assert body["sha256"] == hashlib.sha256(PNG_A).hexdigest()
    image_id = body["id"]

    listed = client.get(f"/organisations/{org_id}/screensaver-images", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == image_id

    deleted = client.delete(
        f"/organisations/{org_id}/screensaver-images/{image_id}",
        headers=headers,
    )
    assert deleted.status_code == 204

    listed = client.get(f"/organisations/{org_id}/screensaver-images", headers=headers)
    assert listed.json() == []


def test_reject_eleventh_screensaver_image():
    org_id, email = _seed_org(email_prefix="ss-max")
    headers = _auth_headers(email)

    for i in range(MAX_SCREENSAVER_GALLERY_IMAGES):
        raw = PNG_A + bytes([i])
        r = _upload(org_id, headers, raw, filename=f"img{i}.png")
        assert r.status_code == 201, r.text

    eleventh = _upload(org_id, headers, PNG_A + b"\xff", filename="too-many.png")
    assert eleventh.status_code == 400


def test_reject_bad_mime_and_oversized():
    org_id, email = _seed_org(email_prefix="ss-bad")
    headers = _auth_headers(email)

    bad_mime = _upload(
        org_id,
        headers,
        b"%PDF-1.4",
        content_type="application/pdf",
        filename="x.pdf",
    )
    assert bad_mime.status_code == 400

    oversized = _upload(
        org_id,
        headers,
        b"\x89PNG" + (b"x" * (MAX_SCREENSAVER_IMAGE_BYTES + 1)),
        filename="big.png",
    )
    assert oversized.status_code == 400


def test_helpers_manifest_and_delete():
    org_id, _email = _seed_org(email_prefix="ss-helper")
    db = SessionLocal()
    try:
        org = db.get(Organisation, org_id)
        assert org is not None
        row = store_screensaver_image(db, org, "image/jpeg", JPEG_A)
        db.commit()
        assert row.sha256 == hashlib.sha256(JPEG_A).hexdigest()
        assert row.mime == "image/jpeg"

        manifest = list_screensaver_manifest(db, org_id)
        assert manifest == [{"sha256": row.sha256, "mime": "image/jpeg"}]
        assert "data" not in manifest[0]

        delete_screensaver_image(db, org_id, row.id)
        db.commit()
        assert list_screensaver_manifest(db, org_id) == []
    finally:
        db.close()


def test_webp_accepted():
    org_id, email = _seed_org(email_prefix="ss-webp")
    headers = _auth_headers(email)
    r = _upload(org_id, headers, WEBP_A, content_type="image/webp", filename="a.webp")
    assert r.status_code == 201, r.text
    assert r.json()["mime"] == "image/webp"


def test_edge_download_scoped_to_credential_organisation():
    org_a, email_a = _seed_org(email_prefix="ss-edge-a")
    org_b, email_b = _seed_org(email_prefix="ss-edge-b")
    headers_a = _auth_headers(email_a)
    headers_b = _auth_headers(email_b)

    up_a = _upload(org_a, headers_a, PNG_A)
    assert up_a.status_code == 201, up_a.text
    sha_a = up_a.json()["sha256"]

    up_b = _upload(org_b, headers_b, PNG_B)
    assert up_b.status_code == 201, up_b.text
    sha_b = up_b.json()["sha256"]

    edge_a = _pair_edge(org_a)

    ok = client.get(f"/edge/v1/screensaver/{sha_a}", headers=edge_a)
    assert ok.status_code == 200
    assert ok.content == PNG_A
    assert ok.headers["content-type"].startswith("image/png")

    other = client.get(f"/edge/v1/screensaver/{sha_b}", headers=edge_a)
    assert other.status_code == 404

    missing = client.get(f"/edge/v1/screensaver/{'0' * 64}", headers=edge_a)
    assert missing.status_code == 404


def test_edge_bundle_includes_screensaver_manifest_without_bytes():
    org_id, email = _seed_org(email_prefix="ss-bundle")
    headers = _auth_headers(email)
    up = _upload(org_id, headers, PNG_A)
    assert up.status_code == 201, up.text
    sha = up.json()["sha256"]

    edge = _pair_edge(org_id)
    response = client.get("/edge/v1/bundle", headers=edge)
    assert response.status_code == 200, response.text
    body = response.json()
    images = body.get("screensaver_images")
    assert images == [{"sha256": sha, "mime": "image/png"}]
    blob = response.text
    assert "data" not in images[0]
    # raw image bytes must not appear in the JSON bundle
    assert PNG_A.decode("latin-1") not in blob
