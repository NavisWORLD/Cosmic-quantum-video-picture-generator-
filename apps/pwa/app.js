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

function setModeFields() {
  videoFields.style.display = mode.value === 'video' ? 'block' : 'none';
  storyFields.style.display = mode.value === 'storybook' ? 'block' : 'none';
}
mode.addEventListener('change', setModeFields);
setModeFields();

async function jsonFetch(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }
  if (!response.ok) throw new Error(data.detail || data.raw || `HTTP ${response.status}`);
  return data;
}

function publicUrl(filePath) {
  const normalized = String(filePath || '').replaceAll('\\', '/');
  const marker = '/out/';
  const index = normalized.lastIndexOf(marker);
  if (index >= 0) return normalized.slice(index);
  if (normalized.startsWith('out/')) return '/' + normalized;
  return null;
}

function showPreview(kind, data) {
  preview.innerHTML = '';
  if (kind === 'image') {
    const url = publicUrl(data.output);
    if (url) preview.innerHTML = `<img alt="Generated COSMOS image" src="${url}?t=${Date.now()}" />`;
  } else if (kind === 'video') {
    const url = publicUrl(data.output);
    if (url) preview.innerHTML = `<video controls playsinline src="${url}?t=${Date.now()}"></video>`;
  } else if (kind === 'storybook') {
    const url = publicUrl(`${data.output_dir}/page-001.png`);
    if (url) preview.innerHTML = `<img alt="Storybook page one" src="${url}?t=${Date.now()}" />`;
  }
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
  } catch (error) {
    status.innerHTML = `<span class="pill">engine offline: ${error.message}</span>`;
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
        output: `out/pwa-image-${now}.png`,
      };
    } else if (mode.value === 'video') {
      endpoint = '/v1/video';
      payload = {
        prompt: prompt.value.trim(),
        context: context.value,
        duration: Number(duration.value),
        output: `out/pwa-video-${now}.mp4`,
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
refreshStatus();

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
