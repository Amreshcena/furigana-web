// ---------- hero subtitle demo cycle ----------

const demoPairs = [
  ['お前を救ってみせる', 'お前[おまえ]を救ってみせる[すくってみせる]'],
  ['異世界と仮定して', '異世界[いせかい]と仮定[かてい]して'],
  ['巨人が紛れ込んでいる', '巨人[きょじん]が紛れ込んでいる[まぎれこんでいる]'],
];

const demoEl = document.getElementById('demo-subtitle');
let demoIndex = 0;
let demoShowingPlain = true;

if (demoEl && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  setInterval(() => {
    demoEl.style.opacity = '0';
    setTimeout(() => {
      if (demoShowingPlain) {
        demoEl.textContent = demoPairs[demoIndex][1];
      } else {
        demoIndex = (demoIndex + 1) % demoPairs.length;
        demoEl.textContent = demoPairs[demoIndex][0];
      }
      demoShowingPlain = !demoShowingPlain;
      demoEl.style.opacity = '1';
    }, 350);
  }, 2400);
}

// ---------- upload flow ----------

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const fileListEl = document.getElementById('file-list');
const processBtn = document.getElementById('process-btn');
const statusEl = document.getElementById('status');

let queuedFiles = [];

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderFileList() {
  fileListEl.innerHTML = '';
  queuedFiles.forEach((file, i) => {
    const li = document.createElement('li');

    const name = document.createElement('span');
    name.textContent = file.name;

    const right = document.createElement('span');
    right.style.display = 'flex';
    right.style.alignItems = 'center';
    right.style.gap = '10px';

    const size = document.createElement('span');
    size.className = 'file-size';
    size.textContent = formatSize(file.size);

    const remove = document.createElement('button');
    remove.className = 'file-remove';
    remove.type = 'button';
    remove.setAttribute('aria-label', `Remove ${file.name}`);
    remove.textContent = '✕';
    remove.addEventListener('click', () => {
      queuedFiles.splice(i, 1);
      renderFileList();
    });

    right.append(size, remove);
    li.append(name, right);
    fileListEl.appendChild(li);
  });
  processBtn.disabled = queuedFiles.length === 0;
}

function addFiles(fileArray) {
  const srtFiles = fileArray.filter(f => f.name.toLowerCase().endsWith('.srt'));
  const skipped = fileArray.length - srtFiles.length;
  queuedFiles = queuedFiles.concat(srtFiles);
  renderFileList();
  if (skipped > 0) {
    setStatus(`Skipped ${skipped} file(s) that weren't .srt.`, 'error');
  }
}

function setStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = 'status' + (kind ? ` is-${kind}` : '');
}

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    fileInput.click();
  }
});

fileInput.addEventListener('change', () => {
  addFiles(Array.from(fileInput.files));
  fileInput.value = '';
});

['dragenter', 'dragover'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', (e) => {
  const files = Array.from(e.dataTransfer.files || []);
  addFiles(files);
});

processBtn.addEventListener('click', async () => {
  if (queuedFiles.length === 0) return;

  processBtn.disabled = true;
  setStatus(`Processing ${queuedFiles.length} file${queuedFiles.length > 1 ? 's' : ''}…`);

  const formData = new FormData();
  queuedFiles.forEach(f => formData.append('files', f, f.name));

  try {
    const res = await fetch('/api/process', { method: 'POST', body: formData });

    if (!res.ok) {
      let message = 'Something went wrong while processing those files.';
      try {
        const data = await res.json();
        if (data.error) message = data.error;
      } catch (_) {}
      setStatus(message, 'error');
      processBtn.disabled = false;
      return;
    }

    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : 'furigana_output.srt';

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    setStatus(`Done — ${filename} downloaded.`, 'success');
    queuedFiles = [];
    renderFileList();
  } catch (err) {
    setStatus('Network error — check your connection and try again.', 'error');
  } finally {
    processBtn.disabled = queuedFiles.length === 0;
  }
});
