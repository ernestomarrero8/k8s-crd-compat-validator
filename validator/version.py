"""Strict release parsing; vendor build suffixes never become patch numbers."""
from dataclasses import dataclass
import re

PATTERN = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+]([0-9A-Za-z][0-9A-Za-z.+-]*))?$")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value):
        match = PATTERN.fullmatch(value) if isinstance(value, str) else None
        if not match:
            raise ValueError("Versión inválida; use 1.35.9 o v1.35.9 (con sufijo de proveedor opcional).")
        if match[4] and re.match(r"(?:alpha|beta|rc)(?:\.|$)", match[4]):
            raise ValueError("Versiones prerelease no soportadas; utilice una versión estable.")
        version = cls(*(int(match[i]) for i in (1, 2, 3)))
        if version.major != 1 or version.minor < 16:
            raise ValueError("Este validador requiere Kubernetes 1.16 o posterior de la serie 1.x.")
        return version

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"


def upgrade_path(current, target):
    if target <= current:
        raise ValueError("La versión objetivo debe ser mayor que la versión actual.")
    return {"minor_difference": target.minor - current.minor,
            "intermediate_minors": [f"1.{m}" for m in range(current.minor + 1, target.minor)],
            "skips_minors": target.minor - current.minor > 1}
