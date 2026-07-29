#!/usr/bin/env python3
"""Validate activation records bound to public-operations evidence manifests."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
SHA_RE=re.compile(r"^[0-9a-f]{40}$"); DIGEST_RE=re.compile(r"^[0-9a-f]{64}$"); SAFE=re.compile(r"^[A-Za-z0-9._/-]+$")
TOP={"schema","schema_version","candidate_sha","decision","activation_mode","manifest_path","manifest_sha256","aggregate_evidence_sha256","authorization_owner_role","independent_approver_role","authorized_at"}
FORBIDDEN=("password","secret","token","api_key","private_key","credential")
def _scan(v):
    if isinstance(v,dict):
        for k,n in v.items():
            if any(t in k.lower() for t in FORBIDDEN): raise ValueError(f"forbidden secret-like key: {k}")
            _scan(n)
    elif isinstance(v,list):
        for n in v:_scan(n)
def _text(v,label):
    if not isinstance(v,str) or len(v.strip())<3 or v.strip().upper() in {"TBD","TODO","PENDING","UNKNOWN","N/A"}: raise ValueError(f"{label} is incomplete")
    return v.strip()
def _path(v):
    if not isinstance(v,str) or not SAFE.fullmatch(v): raise ValueError("manifest path is invalid")
    if v.startswith("/") or ".." in v.split("/"): raise ValueError("manifest path is unsafe")
    return v
def _aggregate(m):
    e=m.get("evidence")
    if not isinstance(e,list): raise ValueError("manifest evidence is invalid")
    rows=[{"type":i.get("type"),"path":i.get("path"),"sha256":i.get("sha256"),"required_decision":i.get("required_decision")} for i in e if isinstance(i,dict)]
    if len(rows)!=len(e): raise ValueError("manifest evidence item is invalid")
    raw=json.dumps(sorted(rows,key=lambda i:str(i["type"])),sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()
def validate_record(v,root,expected_candidate=None):
    if not isinstance(v,dict) or set(v)!=TOP: raise ValueError("top-level keys do not match contract")
    _scan(v)
    if v["schema"]!="lionsforge.public-operations-activation-binding" or v["schema_version"]!=1: raise ValueError("schema is invalid")
    c=v["candidate_sha"]
    if not isinstance(c,str) or not SHA_RE.fullmatch(c): raise ValueError("candidate_sha is invalid")
    if expected_candidate and c!=expected_candidate: raise ValueError("candidate does not match expected candidate")
    d=v["decision"]; mode=v["activation_mode"]
    if d not in {"GO","NO-GO"}: raise ValueError("decision must be GO or NO-GO")
    if mode not in {"NONE","CONTROLLED-BETA","GENERAL-AVAILABILITY"}: raise ValueError("activation_mode is invalid")
    if d=="NO-GO" and mode!="NONE": raise ValueError("NO-GO requires activation mode NONE")
    if d=="GO" and mode=="NONE": raise ValueError("GO requires an activation mode")
    owner=_text(v["authorization_owner_role"],"authorization_owner_role"); approver=_text(v["independent_approver_role"],"independent_approver_role")
    if owner==approver: raise ValueError("authorization roles must be separated")
    try: t=datetime.fromisoformat(_text(v["authorized_at"],"authorized_at").replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("authorized_at is invalid") from exc
    if t.tzinfo is None or t>datetime.now(timezone.utc): raise ValueError("authorized_at must be timezone-aware and not future")
    p=_path(v["manifest_path"]); md=v["manifest_sha256"]; ad=v["aggregate_evidence_sha256"]
    if not isinstance(md,str) or not DIGEST_RE.fullmatch(md): raise ValueError("manifest_sha256 is invalid")
    if not isinstance(ad,str) or not DIGEST_RE.fullmatch(ad): raise ValueError("aggregate_evidence_sha256 is invalid")
    target=root/p
    if not target.is_file() or target.is_symlink(): raise ValueError("manifest file is missing or unsafe")
    raw=target.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=md: raise ValueError("manifest digest mismatch")
    m=json.loads(raw)
    if m.get("candidate_sha")!=c: raise ValueError("manifest candidate mismatch")
    if m.get("decision")!=d: raise ValueError("manifest decision mismatch")
    if _aggregate(m)!=ad: raise ValueError("aggregate evidence digest mismatch")
    return {"candidate_sha":c,"decision":d,"activation_mode":mode,"result":"VALID"}
def main():
    p=argparse.ArgumentParser(); p.add_argument("record"); p.add_argument("--repository-root",default="."); p.add_argument("--expected-candidate"); p.add_argument("--output"); a=p.parse_args()
    try:
        r=validate_record(json.loads(Path(a.record).read_text()),Path(a.repository_root).resolve(),a.expected_candidate)
        if a.output: Path(a.output).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
        print(json.dumps(r,sort_keys=True)); return 0
    except (OSError,json.JSONDecodeError,ValueError) as e:
        print(f"activation binding validation failed: {e}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
