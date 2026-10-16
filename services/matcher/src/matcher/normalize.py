"""Batch normalisation: dispatch each raw item to its source adapter, collecting rejections
instead of failing the whole batch (one malformed item must not stop a run)."""

from matcher.models import NormalizeRequest, NormalizeResponse, Rejected
from matcher.sources import chiletrabajos, getonbrd

ADAPTERS = {"getonbrd": getonbrd.to_canonical, "chiletrabajos": chiletrabajos.to_canonical}


def normalize_batch(request: NormalizeRequest) -> NormalizeResponse:
    adapter = ADAPTERS[request.source]
    offers, rejected, seen = [], [], set()
    for index, item in enumerate(request.items):
        try:
            offer = adapter(item, request.usd_clp)
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append(Rejected(index=index, reason=str(exc) or type(exc).__name__))
            continue
        if offer.offer_id in seen:
            rejected.append(Rejected(index=index, reason=f"duplicate offer_id in batch: {offer.offer_id}"))
            continue
        seen.add(offer.offer_id)
        offers.append(offer)
    return NormalizeResponse(offers=offers, rejected=rejected)
