"""Build a single ZPL (^XA ... ^XZ) shipping label from a CSV row."""

from __future__ import annotations

REQUIRED_FIELDS = ("order_id", "name", "address1", "city", "state", "zip")


class MissingFieldError(ValueError):
    """A CSV row is missing a field the label layout needs."""


def validate_row(row: dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if not row.get(field)]
    if missing:
        raise MissingFieldError(f"missing required field(s): {', '.join(missing)}")


def render_label(row: dict) -> str:
    """Render one label targeting a 4x6in printer at 203dpi.

    That size/resolution pair is the default on almost every desktop
    thermal shipping printer, so it's a safe layout to hardcode for now.
    """
    validate_row(row)

    name = _escape(row["name"])
    address1 = _escape(row["address1"])
    address2 = _escape(row.get("address2", ""))
    city_line = _escape(f"{row['city']}, {row['state']} {row['zip']}")
    order_id = _escape(row["order_id"])
    weight = row.get("weight_lbs", "")

    lines = [
        "^XA",
        "^CI28",  # UTF-8, so accented addresses print correctly
        "^PW812",  # 4in wide at 203dpi
        "^LL1218",  # 6in tall at 203dpi
        f"^FO40,40^A0N,50,50^FD{name}^FS",
        f"^FO40,100^A0N,35,35^FD{address1}^FS",
    ]

    y = 140
    if address2:
        lines.append(f"^FO40,{y}^A0N,35,35^FD{address2}^FS")
        y += 40
    lines.append(f"^FO40,{y}^A0N,35,35^FD{city_line}^FS")
    y += 60

    if weight:
        lines.append(f"^FO40,{y}^A0N,28,28^FDWeight: {_escape(str(weight))} lb^FS")
        y += 40

    lines += [
        f"^FO40,{y + 20}^BY3",
        "^BCN,100,Y,N,N",
        f"^FD{order_id}^FS",
        "^XZ",
    ]
    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    """Strip ZPL's own command prefixes out of field data before embedding it."""
    return value.replace("^", "").replace("~", "")
