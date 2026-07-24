// Resonate — VS Code connector.
// Turns your coding activity (time at work, unresolved errors, the code you're wrestling with)
// into a short context the Resonate engine understands, then surfaces the right verse in the
// status bar margin with a rich hover. No screen-scraping of other apps — only signals VS Code
// already exposes to extensions.

const vscode = require("vscode");
const http = require("http");

let statusBar;
let timer;
let lastSaveTs = Date.now();
let lastReflectTs = 0;

function cfg() {
  const c = vscode.workspace.getConfiguration("resonate");
  return {
    engineUrl: c.get("engineUrl", "http://127.0.0.1:8765"),
    translation: c.get("translation", "KJV"),
    cadenceMinutes: c.get("cadenceMinutes", 20),
    enabled: c.get("enabled", true),
  };
}

function postResonate(text, cb) {
  const { engineUrl, translation } = cfg();
  const body = JSON.stringify({ text, user_id: "vscode", targets: ["vscode"], translation });
  let u;
  try {
    u = new URL(engineUrl);
  } catch (e) {
    return cb(e);
  }
  const req = http.request(
    {
      hostname: u.hostname,
      port: u.port || 80,
      path: "/resonate",
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
      // Live mode runs several Gloo calls + a YouVersion fetch per reflect (~10-15s); the old
      // 4s ceiling aborted mid-response and showed "engine offline". Generous timeout for live.
      timeout: 25000,
    },
    (res) => {
      let data = "";
      res.on("data", (d) => (data += d));
      res.on("end", () => {
        try {
          cb(null, JSON.parse(data));
        } catch (e) {
          cb(e);
        }
      });
    }
  );
  req.on("error", cb);
  req.on("timeout", () => req.destroy(new Error("timeout")));
  req.write(body);
  req.end();
}

function errorCount() {
  let n = 0;
  for (const [, diags] of vscode.languages.getDiagnostics()) {
    n += diags.filter((d) => d.severity === vscode.DiagnosticSeverity.Error).length;
  }
  return n;
}

// Translate IDE telemetry into a sentence the engine can read emotionally.
function buildContext() {
  const ed = vscode.window.activeTextEditor;
  const lang = ed ? ed.document.languageId : "code";
  const mins = Math.max(0, Math.round((Date.now() - lastSaveTs) / 60000));
  const errs = errorCount();
  let s = `I've been working in ${lang} for ${mins} minute${mins === 1 ? "" : "s"} straight`;
  if (errs > 0) s += `, and I'm stuck on ${errs} error${errs === 1 ? "" : "s"} I can't fix`;
  s += ".";
  if (ed && !ed.selection.isEmpty) {
    const sel = ed.document.getText(ed.selection).trim().slice(0, 200);
    if (sel) s += ` I'm wrestling with this: ${sel}`;
  }
  return s;
}

function reflect(manual) {
  const ed = vscode.window.activeTextEditor;
  const text =
    manual && ed && !ed.selection.isEmpty ? ed.document.getText(ed.selection) : buildContext();
  postResonate(text, (err, result) => {
    if (err) {
      statusBar.text = "✝ engine offline";
      statusBar.tooltip = "Start the Resonate engine:  python scripts/serve.py";
      if (manual) vscode.window.showWarningMessage("Resonate engine not reachable. Run: python scripts/serve.py");
      return;
    }
    const v = result.rendered && result.rendered.vscode && result.rendered.vscode[0];
    if (!v) {
      statusBar.text = "✝ Resonate";
      statusBar.tooltip = "No verse surfaced for this moment.";
      if (manual) vscode.window.showInformationMessage("Resonate: nothing pressing right now — keep going.");
      return;
    }
    statusBar.text = v.statusText;
    const md = new vscode.MarkdownString(v.tooltipMarkdown);
    statusBar.tooltip = md;
    lastReflectTs = Date.now();
    if (manual) {
      vscode.window.showInformationMessage(`${v.reference} (${v.translation}) — ${v.bridge}`);
    }
  });
}

function tick() {
  const { enabled, cadenceMinutes } = cfg();
  if (!enabled || cadenceMinutes <= 0) return;
  if (Date.now() - lastReflectTs >= cadenceMinutes * 60000) reflect(false);
}

function activate(context) {
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.text = "✝ Resonate";
  statusBar.tooltip = "Click for a verse for this moment";
  statusBar.command = "resonate.reflect";
  statusBar.show();
  context.subscriptions.push(statusBar);

  context.subscriptions.push(vscode.commands.registerCommand("resonate.reflect", () => reflect(true)));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(() => (lastSaveTs = Date.now())));

  timer = setInterval(tick, 60000);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });
}

function deactivate() {
  if (timer) clearInterval(timer);
}

module.exports = { activate, deactivate };
