# csv-to-zpl

Turns a shipment CSV export into ZPL labels, one label per row.

Most warehouse and fulfillment tools export orders as a plain CSV, but
Zebra-style thermal printers speak ZPL. The usual fix is either a GUI label
designer or a heavyweight shipping SDK, both overkill if all you need is
"take this spreadsheet, print these boxes." This is a single command that
does that one conversion and nothing else.

The order files this is meant for run to hundreds of thousands of rows, so
the tool reads and writes one row at a time rather than loading the CSV or
buffering the ZPL output in memory. You can point it at a huge file, or pipe
it straight into a network printer, without worrying about memory use.

## Usage

```
python -m csv_to_zpl orders.csv > labels.zpl
```

Read from stdin with `-`:

```
cat orders.csv | python -m csv_to_zpl - > labels.zpl
```

Write to a file explicitly instead of stdout:

```
python -m csv_to_zpl orders.csv --output labels.zpl
```

Pipe straight to a network-attached printer (port 9100 is the usual raw
port on Zebra printers):

```
python -m csv_to_zpl orders.csv | nc 192.168.1.50 9100
```

Gzip-compressed input is handled automatically, whether it's a `.gz` file
or a gzip stream piped over stdin. Detection is by magic bytes, not the
file extension, so this works either way:

```
python -m csv_to_zpl orders.csv.gz > labels.zpl
zcat orders.csv.gz | python -m csv_to_zpl - > labels.zpl
```

If a row is missing a required field, the tool prints which file, line, and
field failed to stderr and exits with status 1, without printing any labels
past that point.

Pass `--skip-errors` to keep going instead: bad rows are logged to stderr and
skipped, every other row still gets a label, and the process exits 1 at the
end only if at least one row was skipped.

```
python -m csv_to_zpl orders.csv --skip-errors > labels.zpl
```

## CSV format

One row per shipment. Column order doesn't matter; extra columns are
ignored.

| column        | required | notes                              |
|---------------|----------|-------------------------------------|
| `order_id`    | yes      | printed as a Code 128 barcode       |
| `name`        | yes      | recipient name                      |
| `address1`    | yes      | street address                      |
| `address2`    | no       | apartment/suite, omitted if blank   |
| `city`        | yes      |                                      |
| `state`       | yes      |                                      |
| `zip`         | yes      |                                      |
| `weight_lbs`  | no       | printed on the label if present     |

Example input:

```csv
order_id,name,address1,city,state,zip,weight_lbs
ORD-10234,Jane Cooper,4821 Birch St,Springfield,IL,62704,2.3
```

Labels are laid out for 4x6in stock at 203dpi, the default size and
resolution for most desktop thermal shipping printers.

## Install

No dependencies beyond the Python standard library.

```
pip install -e .
```

This installs a `csv-to-zpl` command as well as the `python -m csv_to_zpl`
form shown above.
