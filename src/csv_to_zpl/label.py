"""Build a single ZPL (^XA ... ^XZ) shipping label from a CSV row."""

from __future__ import annotations

from dataclasses import dataclass

REQUIRED_FIELDS = ("order_id", "name", "address1", "city", "state", "zip")

BASE_DPI = 203  # the resolution the hardcoded layout coordinates below were tuned at


@dataclass(frozen=True)
class LabelSize:
    """Physical label dimensions and print resolution.

    width_in/height_in set ^PW/^LL directly. dpi additionally scales every
    layout coordinate so a label printed at a higher resolution comes out
    the same physical size instead of shrinking into a corner of the page.
    """

    width_in: float = 4.0
    height_in: float = 6.0
    dpi: int = BASE_DPI

    @property
    def width_dots(self) -> int:
        return round(self.width_in * self.dpi)

    @property
    def height_dots(self) -> int:
        return round(self.height_in * self.dpi)


DEFAULT_SIZE = LabelSize()


class MissingFieldError(ValueError):
    """A CSV row is missing a field the label layout needs."""


def validate_row(row: dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if not row.get(field)]
    if missing:
        raise MissingFieldError(f"missing required field(s): {', '.join(missing)}")


def render_label(row: dict, size: LabelSize = DEFAULT_SIZE) -> str:
    """Render one label at the given physical size and resolution.

    The field layout was designed for 4x6in at 203dpi (the default on
    almost every desktop thermal shipping printer) and scales from there;
    picking a much smaller width/height than that can still overflow the
    page since fields aren't reflowed, just repositioned.
    """
    validate_row(row)

    scale = size.dpi / BASE_DPI

    def d(dots: float) -> int:
        return round(dots * scale)

    name = _escape(row["name"])
    address1 = _escape(row["address1"])
    address2 = _escape(row.get("address2", ""))
    city_line = _escape(f"{row['city']}, {row['state']} {row['zip']}")
    order_id = _escape(row["order_id"])
    weight = row.get("weight_lbs", "")

    lines = [
        "^XA",
        "^CI28",  # UTF-8, so accented addresses print correctly
        f"^PW{size.width_dots}",
        f"^LL{size.height_dots}",
        f"^FO{d(40)},{d(40)}^A0N,{d(50)},{d(50)}^FD{name}^FS",
        f"^FO{d(40)},{d(100)}^A0N,{d(35)},{d(35)}^FD{address1}^FS",
    ]

    y = 140
    if address2:
        lines.append(f"^FO{d(40)},{d(y)}^A0N,{d(35)},{d(35)}^FD{address2}^FS")
        y += 40
    lines.append(f"^FO{d(40)},{d(y)}^A0N,{d(35)},{d(35)}^FD{city_line}^FS")
    y += 60

    if weight:
        lines.append(f"^FO{d(40)},{d(y)}^A0N,{d(28)},{d(28)}^FDWeight: {_escape(str(weight))} lb^FS")
        y += 40

    lines += [
        f"^FO{d(40)},{d(y + 20)}^BY{max(1, d(3))}",
        f"^BCN,{d(100)},Y,N,N",
        f"^FD{order_id}^FS",
        "^XZ",
    ]
    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    """Strip ZPL's own command prefixes out of field data before embedding it."""
    return value.replace("^", "").replace("~", "")
