"""
services_v2/gateway/gateway_service.py
"""

from __future__ import annotations
import hashlib
import json
from typing import Optional
from sqlalchemy.orm import Session

from models_v2.models_v2 import EconomicsEstimateV2
from schemas_v2.economics_v2_schema import EstimateRequestV2


class GatewayService:

    def check_idempotency(self, idempotency_key: str, db: Session) -> Optional[dict]:
        if not idempotency_key:
            return None
        existing = (
            db.query(EconomicsEstimateV2)
            .filter(
                EconomicsEstimateV2.idempotency_key == idempotency_key,
                EconomicsEstimateV2.is_recommended == True,
            )
            .first()
        )
        return existing.to_dict() if existing else None

    def build_fingerprint(self, request: EstimateRequestV2) -> str:
        key_fields = {
            "use_case":       request.use_case.value,
            "duration_class": request.duration_class.value,
            "quality_bar":    request.quality_bar.value,
            "latency_mode":   request.latency_mode.value,
            "batch_size":     request.batch_size,
            "variant_count":  request.variant_count,
            "workspace_id":   request.workspace_id,
            "campaign_id":    request.campaign_id,
        }
        raw = json.dumps(key_fields, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
