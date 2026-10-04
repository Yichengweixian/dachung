"""Read the staged Git evidence; do not alter index/history or run solvers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args = p.parse_args()
    names = subprocess.check_output(["git","diff","--cached","--name-only","--diff-filter=A","-z"],cwd=ROOT).decode("utf-8").split("\0")
    names = [name for name in names if name and name != args.output]
    allowed = {"run_day_weight_accounting.py","src/day_weight_accounting.py","tests/test_day_weight_accounting.py",
               "scripts/freeze_day_weight_accounting.py","scripts/audit_day_weight_accounting.py","scripts/audit_u11r13_publication.py"}
    if not names or any(not (name in allowed or name.startswith("results/annual/U11R13-") or name.startswith("instructions/studies/U11R13-day-weight-accounting/")) for name in names):
        raise ValueError("Unexpected new staged-file scope")
    modified = subprocess.check_output(["git","diff","--cached","--name-only","--diff-filter=M","-z"],cwd=ROOT).decode("utf-8").split("\0")
    if set(filter(None,modified)) != {".gitattributes","instructions/STATUS.md","instructions/RUNLOG.md","instructions/sequence_status_v02.md","instructions/specs/roadmap.md"}:
        raise ValueError("Unexpected existing staged-file scope")
    raw = subprocess.check_output(["git","cat-file","--batch"],input=("\n".join(":"+name for name in names)+"\n").encode("utf-8"),cwd=ROOT)
    offset, digests, sizes = 0, {}, {}
    for name in names:
        end = raw.index(b"\n",offset)
        _,kind,length = raw[offset:end].split()
        if kind != b"blob": raise ValueError("Non-blob index record")
        length = int(length)
        content = raw[end+1:end+1+length]
        if len(content) != length or raw[end+1+length:end+2+length] != b"\n": raise ValueError("Truncated index blob")
        offset = end+2+length
        if content != (ROOT/name).read_bytes(): raise ValueError("Index/working byte mismatch: "+name)
        if length >= 100*1024*1024: raise ValueError("GitHub file too large: "+name)
        digests[name],sizes[name] = sha(content),length
    if offset != len(raw): raise ValueError("Unexpected batch suffix")
    folder = ROOT/"results/annual/U11R13-v01"
    m = json.loads((folder/"run_manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT/"results/annual/U11R13-v01-independent-audit.json").read_text(encoding="utf-8"))
    if not audit["passed"] or audit["run_manifest_sha256"] != sha((folder/"run_manifest.json").read_bytes()) or m["status"] != "complete" or m["verdict"] != "supported" or m["cases"] or m["details"]["new_solver_calls"] != 0:
        raise ValueError("Scientific audit identity mismatch")
    pinned = {"results/annual/U11R13-v01/run_manifest.json":audit["run_manifest_sha256"],
              "instructions/studies/U11R13-day-weight-accounting/freeze.json":m["freeze_sha256"]}
    pinned.update({"results/annual/U11R13-v01/"+name:digest for name,digest in m["artifacts"].items()})
    for entries in (m["freeze"]["sha256"],m["source_sha256"]):
        for name,digest in entries.items():
            if name in digests: pinned[name] = digest
    for name,digest in pinned.items():
        if digests.get(name) != digest: raise ValueError("Frozen evidence index mismatch: "+name)
    report = dict(passed=True,new_files_checked=len(digests),pinned_index_hashes=len(pinned),max_new_file_bytes=max(sizes.values()),
                  total_new_bytes=sum(sizes.values()),new_solver_calls=0,retrospective=True,
                  scope="All staged new files except this report; existing changes limited to five mutable docs/attributes",
                  run_manifest_sha256=audit["run_manifest_sha256"],publication_script_sha256=sha(Path(__file__).read_bytes()),index_sha256=digests)
    with (ROOT/args.output).open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write("\n")
    print(json.dumps({k:v for k,v in report.items() if k != "index_sha256"},ensure_ascii=False))


if __name__ == "__main__":
    main()
