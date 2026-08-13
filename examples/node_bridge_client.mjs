import { spawn } from 'node:child_process';
import readline from 'node:readline';

// Any Node/Electron/agent application can keep COSMOS alive as a helper process.
const cosmos = spawn('cosmos-media', ['bridge', '--stdio'], {
  stdio: ['pipe', 'pipe', 'inherit'],
});

const lines = readline.createInterface({ input: cosmos.stdout });
const pending = new Map();

lines.on('line', (line) => {
  const message = JSON.parse(line);
  const waiter = pending.get(String(message.id));
  if (!waiter) return;
  pending.delete(String(message.id));
  if (message.ok) waiter.resolve(message.result);
  else waiter.reject(new Error(message.error?.message || 'COSMOS bridge error'));
});

let nextId = 1;
function call(op, payload = {}) {
  const id = String(nextId++);
  const request = { id, op, ...payload };
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    cosmos.stdin.write(JSON.stringify(request) + '\n');
  });
}

try {
  console.log('capabilities:', await call('capabilities'));
  const plan = await call('plan', {
    prompt: 'a luminous city growing around an impossible world tree',
    count: 6,
  });
  console.log('selected branch:', plan.selected);

  const image = await call('image', {
    prompt: plan.selected.prompt,
    context: 'continue the same world with coherent architecture and light',
    width: 1280,
    height: 720,
    output: 'out/node-bridge-native.png',
  });
  console.log('generated:', image);
} finally {
  cosmos.stdin.end();
}
