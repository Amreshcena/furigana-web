import io
import os
import zipfile

from flask import Flask, render_template, request, send_file, jsonify

from furigana_core import process_srt_text, warm_up

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB upload cap

# Load the dictionary once at startup rather than on the first request,
# so the first visitor doesn't eat the ~1-2s load time.
warm_up()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files uploaded.'}), 400

    results = []
    for f in files:
        name = f.filename or 'subtitle.srt'
        if not name.lower().endswith('.srt'):
            continue
        try:
            raw = f.read().decode('utf-8')
        except UnicodeDecodeError:
            raw = f.read().decode('utf-8-sig', errors='replace')
        processed = process_srt_text(raw)
        out_name = name[:-4] + '.furigana.srt'
        results.append((out_name, processed))

    if not results:
        return jsonify({'error': 'No .srt files found in upload.'}), 400

    if len(results) == 1:
        name, content = results[0]
        buf = io.BytesIO(content.encode('utf-8'))
        buf.seek(0)
        return send_file(
            buf,
            mimetype='text/plain; charset=utf-8',
            as_attachment=True,
            download_name=name,
        )

    # Multiple files -> zip them up
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, content in results:
            zf.writestr(name, content.encode('utf-8'))
    zbuf.seek(0)
    return send_file(
        zbuf,
        mimetype='application/zip',
        as_attachment=True,
        download_name='furigana_subtitles.zip',
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
