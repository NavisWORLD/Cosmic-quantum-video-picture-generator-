const $ = (id) => document.getElementById(id);
const mode = $('mode');
const prompt = $('prompt');
const context = $('context');
const duration = $('duration');
const pages = $('pages');
const go = $('go');
const result = $('result');
const preview = $('preview');
const status = $('status');
const videoFields = $('videoFields');
const storyFields = $('storyFields');
const contextFields = $('contextFields');
const editFields = $('editFields');
const mediaFile = $('mediaFile');
const sourcePreview = $('sourcePreview');
const modelSelect = $('modelSelect');
const modelNote = $('modelNote');
const strength = $('strength');
const strengthValue = $('strengthValue');
const negativePrompt = $('negativePrompt');
const preserveSubject = $('preserveSubject');
const preserveAudio = $('preserveAudio');
const audioCheck = $('audioCheck');
const actionHelp = $('actionHelp');
const engineUrl = $('engineUrl');
const saveEngine = $('saveEngine');
const useSameOrigin = $('useSameOrigin');
const connectionInfo = $('connectionInfo');
const shareOutput = $('shareOutput');

let lastOutputUrl = null;
let sourceObjectUrl = null;
let modelPayload = null;

function isHttpOrigin() {
  return location.protocol === 'http:' || location.protocol === 'https:';
}

function currentEngineBase() {
  const saved = (localStorage.getItem('cosmosEngineUrl') || '').trim().replace(/\/$/, '');
  if (saved) return saved;
  if (isHttpOrigin()) return '';
  return 'http://127.0.0.1:8788';
}

function displayEngineBase() {
  const base = currentEngineBase();
  return base || `${location.protocol}//${location.host}`;
}

function apiUrl(path) {
  return `${currentEngineBase()}${path}`;
}

function isEditMode() {
  return mode.value === 'edit-image' || mode.value === 'edit-video';
}

function setModeFields() {
  const editing = isEditMode();
  const editVideo = mode.value === 'edit-video';
  editFields.hidden = !editing;
  contextFields.style.display = editing ? 'none' : 'block';
  videoFields.style.display = mode.value === 'video' ? 'block' : 'none';
  storyFields.style.display = mode.value === 'storybook' ? 'block' : 'none';
  audioCheck.style.display = editVideo ? 'flex' : 'none';
  mediaFile.accept = mode.value === 'edit-image'
    ? 'image/png,image/jpeg,image/webp'
    : mode.value === 'edit-video'
      ? 'video/mp4,video/quicktime,video/webm,.m4v'
      : 'image/png,image/jpeg,image/webp,video/mp4,video/quicktime,video/webm,.m4v';
  go.textContent = editing ? 'EDIT // REWRITE THIS MEDIA' : 'GENERATE // CONTINUE THE TIMELINE';
  actionHelp.innerHTML = editing
    ? 'COSMOS stores the upload under an opaque asset ID, advances Synaptic continuity, and records the chosen model plus the renderer that actually changed the media.'
    : 'For one hour enter <strong>3600</strong>. COSMOS renders bounded chunks, checkpoints the creative state, and stitches the timeline.';
  if (editing) refreshModels();
}
mode.addEventListener('change', setModeFields);
setModeFields();

strength.addEventListener('input', () => {
  strengthValue.textContent = Number(strength.value).toFixed(2);
});

async function jsonFetch(path, options = {}) {
  const response = await fetch(apiUrl(path), options);
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }
  if (!response.ok) throw new Error(data.detail || data.raw || `HTTP ${response.status}`);
  return data;
}

async function refreshModels() {
  try {
    const data = await jsonFetch('/v1/models');
    modelPayload = data;
    const previous = modelSelect.value;
    modelSelect.innerHTML = '';
    for (const model of data.models || []) {
      const option = document.createElement('option');
      option.value = model.id;
      option.textContent = `${model.label}${model.id === data.default_model ? ' · default' : ''}`;
      option.disabled = model.available === false;
      modelSelect.appendChild(option);
    }
    const preferred = [...modelSelect.options].some((option) => option.value === previous && !option.disabled)
      ? previous
      : data.default_model || 'cosmos-main';
    modelSelect.value = preferred;
    updateModelNote();
  } catch (error) {
    modelNote.textContent = `Could not load model registry: ${error.message}`;
  }
}

function updateModelNote() {
  if (!modelPayload) return;
  const selected = (modelPayload.models || []).find((item) => item.id === modelSelect.value);
  if (!selected) return;
  const controller = selected.controller_repo ? ` · controller ${selected.controller_repo}` : '';
  modelNote.textContent = `${selected.label} · renderer ${selected.active_renderer}${controller}. ${selected.description || ''}`;
}
modelSelect.addEventListener('change', updateModelNote);

function publicUrl(filePath) {
  const normalized = String(filePath || '').replaceAll('\\', '/');
  if (/^https?:\/\//i.test(normalized)) return normalized;
  const marker = '/out/';
  const index = normalized.lastIndexOf(marker);
  let relative = null;
  if (index >= 0) relative = normalized.slice(index);
  else if (normalized.startsWith('out/')) relative = '/' + normalized;
  if (!relative) return null;
  const base = currentEngineBase();
  return `${base}${relative}`;
}

function showPreview(kind, data) {
  preview.innerHTML = '';
  lastOutputUrl = null;
  shareOutput.hidden = true;
  const imageKind = kind === 'image' || kind === 'edit-image';
  const videoKind = kind === 'video' || kind === 'edit-video';
  if (imageKind) {
    const url = publicUrl(data.output);
    if (url) {
      preview.innerHTML = `<img alt="COSMOS image output" src="${url}?t=${Date.now()}" />`;
      lastOutputUrl = url;
    }
  } else if (videoKind) {
    const url = publicUrl(data.output);
    if (url) {
      preview.innerHTML = `<video controls playsinline src="${url}?t=${Date.now()}"></video>`;
      lastOutputUrl = url;
    }
  } else if (kind === 'storybook') {
    const url = publicUrl(`${data.output_dir}/page-001.png`);
    if (url) {
      preview.innerHTML = `<img alt="Storybook page one" src="${url}?t=${Date.now()}" />`;
      lastOutputUrl = url;
    }
  }
  shareOutput.hidden = !lastOutputUrl;
}

async function refreshStatus() {
  try {
    const data = await jsonFetch('/v1/status');
    const edit = data.editing || {};
    status.innerHTML = [
      `<span class="pill ok">engine online</span>`,
      `<span class="pill">provider ${data.provider}</span>`,
      `<span class="pill">model ${edit.default_model || 'cosmos-main'}</span>`,
      `<span class="pill">edit ${edit.renderer || 'native'}</span>`,
      `<span class="pill">quantum ${data.quantum.mode}</span>`,
      `<span class="pill">state step ${data.state.step_index}</span>`,
    ].join('');
    connectionInfo.textContent = `Connected to ${displayEngineBase()} · ${data.engine || 'COSMOS Media'} · provider ${data.provider} · default model ${edit.default_model || 'cosmos-main'}`;
    return true;
  } catch (error) {
    status.innerHTML = `<span class="pill bad">engine offline: ${error.message}</span>`;
    connectionInfo.textContent = `Could not reach ${displayEngineBase()}: ${error.message}`;
    return false;
  }
}

function renderSourcePreview(file) {
  if (sourceObjectUrl) URL.revokeObjectURL(sourceObjectUrl);
  sourceObjectUrl = null;
  sourcePreview.innerHTML = '';
  if (!file) return;
  sourceObjectUrl = URL.createObjectURL(file);
  if (file.type.startsWith('image/')) {
    sourcePreview.innerHTML = `<img alt="Uploaded source image" src="${sourceObjectUrl}" />`;
  } else if (file.type.startsWith('video/') || /\.(mp4|mov|webm|m4v)$/i.test(file.name)) {
    sourcePreview.innerHTML = `<video controls playsinline src="${sourceObjectUrl}"></video>`;
  } else {
    sourcePreview.textContent = file.name;
  }
}
mediaFile.addEventListener('change', () => renderSourcePreview(mediaFile.files?.[0]));

async function uploadSelectedMedia() {
  const file = mediaFile.files?.[0];
  if (!file) throw new Error('Choose an image or video to edit first.');
  const form = new FormData();
  form.append('file', file, file.name);
  return jsonFetch('/v1/uploads', { method: 'POST', body: form });
}

async function runEdit() {
  const text = prompt.value.trim();
  if (!text) throw new Error('Add an edit prompt first.');
  result.textContent = 'Uploading source media…';
  const asset = await uploadSelectedMedia();
  result.textContent = `Uploaded ${asset.original_name}. Editing…`;
  const kind = mode.value === 'edit-image' ? 'image' : 'video';
  const payload = {
    asset_id: asset.asset_id,
    prompt: text,
    negative_prompt: negativePrompt.value.trim(),
    model: modelSelect.value || 'cosmos-main',
    strength: Number(strength.value),
    preserve_subject: preserveSubject.checked,
  };
  if (kind === 'video') payload.preserve_audio = preserveAudio.checked;
  return jsonFetch(`/v1/edit/${kind}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function generate() {
  go.disabled = true;
  result.textContent = isEditMode() ? 'Preparing edit…' : 'Generating…';
  preview.innerHTML = '';
  const now = Date.now();
  try {
    if (isEditMode()) {
      const data = await runEdit();
      result.textContent = JSON.stringify(data, null, 2);
      showPreview(mode.value, data);
      await refreshStatus();
      return;
    }

    let endpoint;
    let payload;
    if (mode.value === 'image') {
      endpoint = '/v1/image';
      payload = {
        prompt: prompt.value.trim(),
        context: context.value,
        output: `out/app-image-${now}.png`,
      };
    } else if (mode.value === 'video') {
      endpoint = '/v1/video';
      payload = {
        prompt: prompt.value.trim(),
        context: context.value,
        duration: Number(duration.value),
        output: `out/app-video-${now}.mp4`,
      };
    } else if (mode.value === 'storybook') {
      endpoint = '/v1/storybook';
      payload = {
        title: prompt.value.trim() || 'COSMOS Storybook',
        context: context.value || prompt.value,
        pages: Number(pages.value),
        output_dir: `out/storybook-${now}`,
      };
    } else {
      endpoint = '/v1/branch-search';
      payload = { prompt: prompt.value.trim(), count: 6 };
    }
    if (!payload.prompt && mode.value !== 'storybook') throw new Error('Add a prompt first.');
    if (mode.value === 'storybook' && !payload.context.trim()) throw new Error('Add source context for the storybook.');
    const data = await jsonFetch(endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    result.textContent = JSON.stringify(data, null, 2);
    showPreview(mode.value, data);
    await refreshStatus();
  } catch (error) {
    result.textContent = `ERROR\n${error.message}`;
  } finally {
    go.disabled = false;
  }
}

go.addEventListener('click', generate);

saveEngine.addEventListener('click', async () => {
  const value = engineUrl.value.trim().replace(/\/$/, '');
  if (value) localStorage.setItem('cosmosEngineUrl', value);
  else localStorage.removeItem('cosmosEngineUrl');
  engineUrl.value = currentEngineBase();
  await refreshStatus();
  await refreshModels();
});

useSameOrigin.addEventListener('click', async () => {
  localStorage.removeItem('cosmosEngineUrl');
  engineUrl.value = isHttpOrigin() ? '' : currentEngineBase();
  await refreshStatus();
  await refreshModels();
});

shareOutput.addEventListener('click', async () => {
  if (!lastOutputUrl) return;
  try {
    if (navigator.share) {
      await navigator.share({ title: 'COSMOS Media', text: 'Created or edited with COSMOS Media', url: lastOutputUrl });
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(lastOutputUrl);
      connectionInfo.textContent = 'Output URL copied to clipboard.';
    }
  } catch (_) {
    // User cancellation is not an application error.
  }
});

engineUrl.value = currentEngineBase();
refreshStatus();
refreshModels();

if ('serviceWorker' in navigator && isHttpOrigin()) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
