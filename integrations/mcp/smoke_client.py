"""Tiny MCP smoke client — spawns the server over real stdio and drives a session.
Proof the protocol plumbing works without needing Claude/ChatGPT attached."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "resonate_mcp.py")


def main():
    proc = subprocess.Popen([sys.executable, SERVER], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, encoding="utf-8")

    def call(method, params=None, rid=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if rid is not None:
            msg["id"] = rid
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        if rid is None:
            return None
        return json.loads(proc.stdout.readline())

    print("== initialize")
    r = call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                            "clientInfo": {"name": "smoke", "version": "0"}}, rid=1)
    print("  server:", r["result"]["serverInfo"], "| protocol:", r["result"]["protocolVersion"])
    call("notifications/initialized", {})

    r = call("tools/list", {}, rid=2)
    print("== tools/list:", [t["name"] for t in r["result"]["tools"]])

    def tool(name, args, rid):
        r = call("tools/call", {"name": name, "arguments": args}, rid=rid)
        out = json.loads(r["result"]["content"][0]["text"])
        return out

    print("== resonate_verse (emotional)")
    out = tool("resonate_verse", {"text": "I feel like I'm failing everyone and I can't keep up.",
                                  "user_id": "smoke"}, 3)
    print("  ->", out["kind"], "|", out.get("reference"), "|", (out.get("verse_text") or "")[:60])

    print("== resonate_verse (neutral -> silence)")
    out = tool("resonate_verse", {"text": "what's the capital of France?", "user_id": "smoke"}, 4)
    print("  ->", out["kind"], "|", out.get("message", "")[:70])

    print("== resonate_verse (crisis -> help, never a verse)")
    out = tool("resonate_verse", {"text": "honestly I do not want to live anymore",
                                  "user_id": "smoke"}, 5)
    print("  ->", out["kind"], "| has verse:", "verse_text" in out)

    print("== generate_story")
    out = tool("generate_story", {"text": "I'm completely exhausted and burned out lately.",
                                  "user_id": "smoke"}, 6)
    print("  ->", out["kind"], "|", out.get("title"), "|", (out.get("label") or "")[:60])

    print("== fetch_passage")
    out = tool("fetch_passage", {"usfm": "JHN.3.16"}, 7)
    print("  ->", out["kind"], "|", (out.get("text") or "")[:60], "| source:", out.get("source"))

    proc.stdin.close()
    proc.terminate()
    print("\nSMOKE OK")


if __name__ == "__main__":
    main()
