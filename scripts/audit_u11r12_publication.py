"""Read the staged Git blobs before publication, without altering the index."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = ROOT/args.output
    names = subprocess.check_output(["git","diff","--cached","--name-only","--diff-filter=A","-z"],cwd=ROOT).decode("utf-8").split("\0")
    names = [name for name in names if name and name != args.output]
    if not names or any(not (name.startswith("results/annual/U11R12-") or name.startswith("instructions/studies/U11R12-input-shortage-proxy/") or name in
            {"run_input_shortage_proxy.py","src/input_shortage_proxy.py","tests/test_input_shortage_proxy.py",
             "scripts/freeze_input_shortage_proxy.py","scripts/audit_input_shortage_proxy.py","scripts/audit_u11r12_publication.py"}) for name in names):
        raise ValueError("Unexpected staged new-file scope")
    modified = subprocess.check_output(["git","diff","--cached","--name-only","--diff-filter=M","-z"],cwd=ROOT).decode("utf-8").split("\0")
    expected_modified = {".gitattributes","instructions/RUNLOG.md","instructions/STATUS.md","instructions/sequence_status_v02.md","instructions/specs/roadmap.md"}
    if set(filter(None,modified)) != expected_modified:
        raise ValueError("Unexpected staged existing-file scope")
    raw = subprocess.check_output(["git","cat-file","--batch"],input=("\n".join(":"+name for name in names)+"\n").encode("utf-8"),cwd=ROOT)
    offset, digests, sizes = 0, {}, {}
    for name in names:
        end = raw.index(b"\n",offset)
        _,kind,length = raw[offset:end].split()
        if kind != b"blob": raise ValueError("Non-blob index target")
        length = int(length)
        content = raw[end+1:end+1+length]
        if len(content) != length or raw[end+1+length:end+2+length] != b"\n": raise ValueError("Truncated batch")
        offset = end+2+length
        working = (ROOT/name).read_bytes()
        if content != working: raise ValueError("Index/working bytes differ: "+name)
        if length >= 100*1024*1024: raise ValueError("GitHub file size limit: "+name)
        digests[name],sizes[name] = sha(content),length
    if offset != len(raw): raise ValueError("Unexpected batch suffix")
    run = ROOT/"results/annual/U11R12-v01"
    manifest = json.loads((run/"run_manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT/"results/annual/U11R12-v01-independent-audit.json").read_text(encoding="utf-8"))
    if not audit["passed"] or audit["run_manifest_sha256"] != sha((run/"run_manifest.json").read_bytes()) or manifest["status"] != "complete" or manifest["verdict"] != "refuted":
        raise ValueError("Scientific audit identity mismatch")
    pinned = {"results/annual/U11R12-v01/run_manifest.json":audit["run_manifest_sha256"],
              "instructions/studies/U11R12-input-shortage-proxy/freeze.json":manifest["freeze_sha256"]}
    pinned.update({"results/annual/U11R12-v01/"+name:digest for name,digest in manifest["artifacts"].items()})
    for collection in (manifest["freeze"]["sha256"],manifest["source_sha256"]):
        for name,digest in collection.items():
            if name in digests: pinned[name] = digest
    for name,digest in pinned.items():
        if digests.get(name) != digest: raise ValueError("Pinned index evidence mismatch: "+name)
    report = dict(passed=True,scope="staged new files excluding this report; five explicitly mutable existing docs/attributes",
                  new_files_checked=len(digests),pinned_index_hashes=len(pinned),max_new_file_bytes=max(sizes.values()),
                  total_new_bytes=sum(sizes.values()),run_manifest_sha256=audit["run_manifest_sha256"],
                  scientific_verdict=manifest["verdict"],new_solver_calls=0,
                  publication_script_sha256=sha(Path(__file__).read_bytes()),index_sha256=digests)
    with output.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write("\n")
    print(json.dumps({k:v for k,v in report.items() if k != "index_sha256"},ensure_ascii=False))


if __name__ == "__main__":
    main()
