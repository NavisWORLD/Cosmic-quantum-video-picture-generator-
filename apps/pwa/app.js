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
const engineUrl = $('engineUrl');
const saveEngine = $('saveEngine');
const useSameOrigin = $('useSameOrigin');
const connectionInfo = $('connectionInfo');
const shareOutput = $('shareOutput');

let lastOutputUrl = null;

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

function setModeFields() {
  videoFields.style.display = mode.value === 'video' ? 'block' : 'none';
  storyFields.style.display = mode.value === 'storybook' ? 'block' : 'none';
}
mode.addEventListener('change', setModeFields);
setModeFields();

async function jsonFetch(path, options = {}) {
  const response = await fetch(apiUrl(path), options);
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }
  if (!response.ok) throw new Error(data.detail || data.raw || `HTTP ${response.status}`);
  return data;
}

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
  if (kind === 'image') {
    const url = publicUrl(data.output);
    if (url) {
      preview.innerHTML = `<img alt="Generated COSMOS image" src="${url}?t=${Date.now()}" />`;
      lastOutputUrl = url;
    }
  } else if (kind === 'video') {
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
    status.innerHTML = [
      `<span class="pill ok">engine online</span>`,
      `<span class="pill">provider ${data.provider}</span>`,
      `<span class="pill">quantum ${data.quantum.mode}</span>`,
      `<span class="pill">state step ${data.state.step_index}</span>`,
    ].join('');
    connectionInfo.textContent = `Connected to ${displayEngineBase()} · ${data.engine || 'COSMOS Media'} · provider ${data.provider}`;
    return true;
  } catch (error) {
    status.innerHTML = `<span class="pill bad">engine offline: ${error.message}</span>`;
    connectionInfo.textContent = `Could not reach ${displayEngineBase()}: ${error.message}`;
    return false;
  }
}

async function generate() {
  go.disabled = true;
  result.textContent = 'Generating…';
  preview.innerHTML = '';
  const now = Date.now();
  try {
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
});

useSameOrigin.addEventListener('click', async () => {
  localStorage.removeItem('cosmosEngineUrl');
  engineUrl.value = isHttpOrigin() ? '' : currentEngineBase();
  await refreshStatus();
});

shareOutput.addEventListener('click', async () => {
  if (!lastOutputUrl) return;
  try {
    if (navigator.share) {
      await navigator.share({ title: 'COSMOS Media', text: 'Created with COSMOS Media', url: lastOutputUrl });
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

if ('serviceWorker' in navigator && isHttpOrigin()) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
