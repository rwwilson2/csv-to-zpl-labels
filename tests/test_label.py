import unittest

from csv_to_zpl.label import (
    REQUIRED_FIELDS,
    LabelSize,
    MissingFieldError,
    render_label,
    validate_row,
)


def _row(**overrides):
    row = {
        "order_id": "ORD-1",
        "name": "Jane Cooper",
        "address1": "4821 Birch St",
        "city": "Springfield",
        "state": "IL",
        "zip": "62704",
    }
    row.update(overrides)
    return row


class RenderLabelTests(unittest.TestCase):
    def test_wraps_content_in_start_and_end_commands(self):
        label = render_label(_row())
        self.assertTrue(label.startswith("^XA\n"))
        self.assertTrue(label.endswith("^XZ\n"))

    def test_includes_all_required_fields(self):
        label = render_label(_row())
        self.assertIn("^FDJane Cooper^FS", label)
        self.assertIn("^FD4821 Birch St^FS", label)
        self.assertIn("^FDSpringfield, IL 62704^FS", label)
        self.assertIn("^FDORD-1^FS", label)

    def test_address2_included_when_present(self):
        label = render_label(_row(address2="Apt 4B"))
        self.assertIn("^FDApt 4B^FS", label)

    def test_address2_omitted_when_blank(self):
        label = render_label(_row(address2=""))
        self.assertNotIn("Apt", label)

    def test_weight_included_when_present(self):
        label = render_label(_row(weight_lbs="2.3"))
        self.assertIn("Weight: 2.3 lb", label)

    def test_weight_omitted_when_absent(self):
        label = render_label(_row())
        self.assertNotIn("Weight:", label)

    def test_missing_required_field_raises(self):
        row = _row()
        del row["city"]
        with self.assertRaises(MissingFieldError):
            render_label(row)

    def test_blank_required_field_treated_as_missing(self):
        with self.assertRaises(MissingFieldError):
            render_label(_row(name=""))

    def test_error_message_lists_every_missing_field(self):
        with self.assertRaises(MissingFieldError) as ctx:
            validate_row({"name": "Jane"})
        message = str(ctx.exception)
        for field in REQUIRED_FIELDS:
            if field != "name":
                self.assertIn(field, message)

    def test_caret_and_tilde_stripped_from_field_data(self):
        label = render_label(_row(name="Weird^Name~Here"))
        self.assertIn("^FDWeirdNameHere^FS", label)
        self.assertNotIn("Weird^Name", label)
        self.assertNotIn("Name~Here", label)


class LabelSizeTests(unittest.TestCase):
    def test_default_size_is_4x6_at_203dpi(self):
        label = render_label(_row())
        self.assertIn("^PW812", label)
        self.assertIn("^LL1218", label)

    def test_width_and_height_set_page_size_in_dots(self):
        label = render_label(_row(), size=LabelSize(width_in=6, height_in=4))
        self.assertIn("^PW1218", label)
        self.assertIn("^LL812", label)

    def test_changing_width_and_height_alone_does_not_rescale_fonts(self):
        label = render_label(_row(), size=LabelSize(width_in=6, height_in=4))
        self.assertIn("^A0N,50,50^FDJane Cooper^FS", label)

    def test_higher_dpi_scales_layout_to_match_physical_size(self):
        label = render_label(_row(), size=LabelSize(dpi=406))
        self.assertIn("^PW1624", label)
        self.assertIn("^LL2436", label)
        self.assertIn("^A0N,100,100^FDJane Cooper^FS", label)

    def test_lower_dpi_never_shrinks_barcode_module_width_below_one(self):
        label = render_label(_row(), size=LabelSize(dpi=25))
        self.assertIn("^BY1", label)


if __name__ == "__main__":
    unittest.main()
