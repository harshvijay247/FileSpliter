import csv
import os
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO

from flask import Flask, render_template_string, request, send_file, redirect, url_for, flash


app = Flask(__name__)
app.secret_key = "change-me"  # required for flash messages


def split_csv(source_filepath, dest_folder, split_file_prefix, records_per_file):
    """Split a CSV file on disk into multiple CSVs with a fixed number of records."""
    if records_per_file <= 0:
        raise Exception("records_per_file must be > 0")

    with open(source_filepath, "r", newline="", encoding="utf-8") as source:
        reader = csv.reader(source)
        headers = next(reader)
        file_idx = 0
        records_exist = True

        while records_exist:
            i = 0
            target_filename = f"{split_file_prefix}_{file_idx}.csv"
            target_filepath = os.path.join(dest_folder, target_filename)

            # newline='' to avoid blank lines on Windows
            with open(target_filepath, "w", newline="", encoding="utf-8") as target:
                writer = csv.writer(target)

                while i < records_per_file:
                    if i == 0:
                        writer.writerow(headers)
                    try:
                        writer.writerow(next(reader))
                        i += 1
                    except StopIteration:
                        records_exist = False
                        break

            if i == 0:
                # only wrote the header, so delete that file
                os.remove(target_filepath)

            file_idx += 1


def remove_blank_rows(in_directory, out_directory):
    """Copy CSVs from in_directory to out_directory while removing completely blank rows."""
    os.makedirs(out_directory, exist_ok=True)
    extension = ".csv"

    for item in os.listdir(in_directory):
        if not item.endswith(extension):
            continue

        src_path = os.path.join(in_directory, item)
        dst_path = os.path.join(out_directory, item)

        with open(src_path, "r", newline="", encoding="utf-8") as in_file, open(
            dst_path, "w", newline="", encoding="utf-8"
        ) as out_file:
            writer = csv.writer(out_file)
            for row in csv.reader(in_file):
                if row:
                    writer.writerow(row)


INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>CSV Splitter</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f3f4f6; margin:0; padding:0; }
      .page { max-width: 720px; margin: 40px auto; background:#ffffff; padding:24px 32px; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,0.06); }
      h1 { margin-top:0; font-size:1.7rem; color:#111827; }
      p { color:#4b5563; }
      .field { margin-bottom:16px; }
      label { display:block; font-weight:600; margin-bottom:4px; color:#111827; }
      input[type="file"], input[type="number"] {
        width:100%; padding:8px 10px; border-radius:8px; border:1px solid #d1d5db; box-sizing:border-box;
      }
      input[type="number"] { max-width: 220px; }
      button {
        background:#2563eb; color:white; border:none; border-radius:999px; padding:10px 22px;
        font-weight:600; cursor:pointer; display:inline-flex; align-items:center; gap:6px;
      }
      button:hover { background:#1d4ed8; }
      .hint { font-size:0.85rem; color:#6b7280; }
      .messages { margin-bottom:16px; }
      .msg { padding:8px 10px; border-radius:8px; font-size:0.9rem; margin-bottom:6px; }
      .msg.error { background:#fee2e2; color:#991b1b; }
      .msg.success { background:#dcfce7; color:#14532d; }
    </style>
  </head>
  <body>
    <div class="page">
      <h1>CSV Splitter &amp; Cleaner</h1>
      <p>Upload a large CSV file and get back a ZIP containing smaller CSV chunks (with blank rows removed).</p>

      <div class="messages">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="msg {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
      </div>

      <form method="post" action="{{ url_for('process') }}" enctype="multipart/form-data">
        <div class="field">
          <label for="file">Input CSV file</label>
          <input type="file" id="file" name="file" accept=".csv" required />
          <div class="hint">The first row is treated as the header.</div>
        </div>

        <div class="field">
          <label for="records_per_file">Rows per output file</label>
          <input type="number" id="records_per_file" name="records_per_file" min="1" value="700000" required />
          <div class="hint">Same logic as your script: each chunk includes the header row.</div>
        </div>

        <button type="submit">
          Split &amp; Download ZIP
        </button>
      </form>
    </div>
  </body>
  </html>
"""


@app.get("/")
def index():
    return render_template_string(INDEX_TEMPLATE)


@app.post("/process")
def process():
    uploaded = request.files.get("file")
    if not uploaded or uploaded.filename == "":
        flash("Please choose a CSV file to upload.", "error")
        return redirect(url_for("index"))

    if not uploaded.filename.lower().endswith(".csv"):
        flash("Only .csv files are supported in this UI.", "error")
        return redirect(url_for("index"))

    try:
        records_per_file = int(request.form.get("records_per_file", "700000"))
        if records_per_file <= 0:
            raise ValueError
    except ValueError:
        flash("Rows per output file must be a positive integer.", "error")
        return redirect(url_for("index"))

    # Use temporary directories so we don't touch your real folders.
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, "input.csv")
        split_dir = os.path.join(tmp_dir, "split")
        cleaned_dir = os.path.join(tmp_dir, "cleaned")
        os.makedirs(split_dir, exist_ok=True)

        # Save the uploaded file to disk
        uploaded.save(input_path)

        # Split the file (same algorithm as your script)
        prefix = os.path.splitext(os.path.basename(uploaded.filename))[0]
        split_csv(input_path, split_dir, prefix, records_per_file)

        # Remove blank rows from each split file
        remove_blank_rows(split_dir, cleaned_dir)

        # Package all cleaned CSVs into a single ZIP in memory
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(os.listdir(cleaned_dir)):
                if not name.endswith(".csv"):
                    continue
                file_path = os.path.join(cleaned_dir, name)
                # Store in ZIP under just the filename (no temp paths)
                zf.write(file_path, arcname=name)

        memory_file.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        download_name = f"processed_{timestamp}.zip"

        return send_file(
            memory_file,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/zip",
        )


if __name__ == "__main__":
    # Run the Flask dev server
    app.run(debug=True)
