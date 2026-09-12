import gzip
import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr

from csv_to_zpl.cli import main, run

CSV_HEADER = "order_id,name,address1,city,state,zip,weight_lbs\n"


def _write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(CSV_HEADER)
        f.writelines(rows)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))

    def _path(self, name):
        return os.path.join(self.tmpdir, name)

    def test_writes_one_label_per_row(self):
        input_path = self._path("orders.csv")
        _write_csv(
            input_path,
            [
                "ORD-1,Jane Cooper,4821 Birch St,Springfield,IL,62704,2.3\n",
                "ORD-2,John Doe,10 Main St,Chicago,IL,60601,\n",
            ],
        )
        output_path = self._path("labels.zpl")

        status = run(input_path, output_path)

        self.assertEqual(status, 0)
        content = open(output_path, encoding="utf-8").read()
        self.assertEqual(content.count("^XA"), 2)
        self.assertIn("ORD-1", content)
        self.assertIn("ORD-2", content)

    def test_aborts_on_first_bad_row_without_skip_errors(self):
        input_path = self._path("orders.csv")
        _write_csv(
            input_path,
            [
                "ORD-1,Jane Cooper,4821 Birch St,Springfield,IL,62704,\n",
                "ORD-2,,10 Main St,Chicago,IL,60601,\n",  # missing name
                "ORD-3,Sam Lee,1 Oak St,Peoria,IL,61601,\n",
            ],
        )
        output_path = self._path("labels.zpl")

        with redirect_stderr(io.StringIO()) as stderr:
            status = run(input_path, output_path)

        self.assertEqual(status, 1)
        self.assertIn("missing required field", stderr.getvalue())
        content = open(output_path, encoding="utf-8").read()
        self.assertEqual(content.count("^XA"), 1)
        self.assertIn("ORD-1", content)
        self.assertNotIn("ORD-3", content)

    def test_skip_errors_keeps_going_past_bad_rows(self):
        input_path = self._path("orders.csv")
        _write_csv(
            input_path,
            [
                "ORD-1,Jane Cooper,4821 Birch St,Springfield,IL,62704,\n",
                "ORD-2,,10 Main St,Chicago,IL,60601,\n",
                "ORD-3,Sam Lee,1 Oak St,Peoria,IL,61601,\n",
            ],
        )
        output_path = self._path("labels.zpl")

        with redirect_stderr(io.StringIO()):
            status = run(input_path, output_path, skip_errors=True)

        self.assertEqual(status, 1)
        content = open(output_path, encoding="utf-8").read()
        self.assertEqual(content.count("^XA"), 2)
        self.assertIn("ORD-1", content)
        self.assertIn("ORD-3", content)
        self.assertNotIn("ORD-2", content)

    def test_reads_gzip_input_by_magic_bytes_not_extension(self):
        input_path = self._path("orders.csv.gz")
        with gzip.open(input_path, "wt", encoding="utf-8", newline="") as f:
            f.write(CSV_HEADER)
            f.write("ORD-1,Jane Cooper,4821 Birch St,Springfield,IL,62704,\n")
        output_path = self._path("labels.zpl")

        status = run(input_path, output_path)

        self.assertEqual(status, 0)
        content = open(output_path, encoding="utf-8").read()
        self.assertIn("ORD-1", content)

    def test_main_wires_up_run_and_returns_its_status(self):
        input_path = self._path("orders.csv")
        _write_csv(input_path, ["ORD-1,Jane Cooper,4821 Birch St,Springfield,IL,62704,\n"])
        output_path = self._path("labels.zpl")

        status = main([input_path, "--output", output_path])

        self.assertEqual(status, 0)
        self.assertIn("ORD-1", open(output_path, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
