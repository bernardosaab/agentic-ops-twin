"""Domain-pack registry."""

from __future__ import annotations

from collections.abc import Callable

from throughline.packs import insurance, procurement, support
from throughline.packs.base import DomainPack

_BUILDERS: dict[str, Callable[[], DomainPack]] = {
    "insurance": insurance.build,
    "procurement": procurement.build,
    "support": support.build,
}

PACK_IDS: tuple[str, ...] = tuple(_BUILDERS)


def get_pack(pack_id: str) -> DomainPack:
    try:
        return _BUILDERS[pack_id]()
    except KeyError:
        raise KeyError(f"unknown pack '{pack_id}'; available: {', '.join(PACK_IDS)}") from None
