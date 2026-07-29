#!/usr/bin/env python3
"""Validate replay-resistant public-operations activation receipts."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
SHA_RE=re.compile(r"^[0-9a-f]{40}$"); DIGEST_RE=re.compile(r"^[0-9a-f]{64}$"); ID_RE=re.compile(r"^[A-Za-z0-9._-]{8,96}$"); SAFE=re.compile(r"^[A-Za-z0-9._/-]+$")
TOP={"schema","schema_version","candidate_sha","decision","activation_mode","binding_path","binding_sha256","aggregate_evidence_sha256","receipt_id","issuer_role","issued_at","expires_at","authorization_digest"}
FORBIDDEN=("password","secret","token","api_key","private_key","credential")
def _scan(v):
    if isinstance(v,dict):
        for k,n in v.items():
            if any(t in k.lower() for t in FORBIDDEN): raise ValueError(f"forbidden secret-like key: {k}")
            _scan(n)
    elif isinstance(v,list):
        for n in v:_scan(n)
def _path(v):
    if not isinstance(v,str) or not SAFE.fullmatch(v): raise ValueError("binding path is invalid")
    if v.startswith("/") or ".." in v.split("/"): raise ValueError("binding path is unsafe")
    return v
def _time(v,label):
    if not isinstance(v,str): raise ValueError(f"{label} is invalid")
    try:t=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError as e: raise ValueError(f"{label} is invalid") from e
    if t.tzinfo is None: raise ValueError(f"{label} must be timezone-aware")
    return t
def _auth_digest(binding_sha,candidate,decision,mode,aggregate,receipt_id,issuer,issued,expires):
    payload={"binding_sha256":binding_sha,"candidate_sha":candidate,"decision":decision,"activation_mode":mode,"aggregate_evidence_sha256":aggregate,"receipt_id":receipt_id,"issuer_role":issuer,"issued_at":issued,"expires_at":expires}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def validate_record(v,root,expected_candidate=None,ledger=None,now=None):
    if not isinstance(v,dict) or set(v)!=TOP: raise ValueError("top-level keys do not match contract")
    _scan(v)
    if v["schema"]!="lionsforge.public-operations-activation-receipt" or v["schema_version"]!=1: raise ValueError("schema is invalid")
    c=v["candidate_sha"]
    if not isinstance(c,str) or not SHA_RE.fullmatch(c): raise ValueError("candidate_sha is invalid")
    if expected_candidate and c!=expected_candidate: raise ValueError("candidate does not match expected candidate")
    d=v["decision"]; mode=v["activation_mode"]
    if d not in {"GO","NO-GO"}: raise ValueError("decision is invalid")
    if mode not in {"NONE","CONTROLLED-BETA","GENERAL-AVAILABILITY"}: raise ValueError("activation_mode is invalid")
    if d=="NO-GO" and mode!="NONE": raise ValueError("NO-GO requires activation mode NONE")
    if d=="GO" and mode=="NONE": raise ValueError("GO requires an activation mode")
    rid=v["receipt_id"]
    if not isinstance(rid,str) or not ID_RE.fullmatch(rid): raise ValueError("receipt_id is invalid")
    if ledger and rid in ledger: raise ValueError("receipt_id is already present in ledger")
    issuer=v["issuer_role"]
    if not isinstance(issuer,str) or len(issuer.strip())<3: raise ValueError("issuer_role is incomplete")
    issued=_time(v["issued_at"],"issued_at"); expires=_time(v["expires_at"],"expires_at")
    current=now or datetime.now(timezone.utc)
    if issued>current: raise ValueError("issued_at cannot be future")
    if expires<=issued: raise ValueError("expires_at must be after issued_at")
    if d=="GO" and expires<=current: raise ValueError("GO receipt is expired")
    p=_path(v["binding_path"]); bs=v["binding_sha256"]; ag=v["aggregate_evidence_sha256"]; ad=v["authorization_digest"]
    for value,label in ((bs,"binding_sha256"),(ag,"aggregate_evidence_sha256"),(ad,"authorization_digest")):
        if not isinstance(value,str) or not DIGEST_RE.fullmatch(value): raise ValueError(f"{label} is invalid")
    target=root/p
    if not target.is_file() or target.is_symlink(): raise ValueError("binding file is missing or unsafe")
    raw=target.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=bs: raise ValueError("binding digest mismatch")
    b=json.loads(raw)
    for key,expected in (("candidate_sha",c),("decision",d),("activation_mode",mode),("aggregate_evidence_sha256",ag)):
        if b.get(key)!=expected: raise ValueError(f"binding {key} mismatch")
    owner=b.get("authorization_owner_role")
    if d=="GO" and issuer==owner: raise ValueError("GO receipt issuer must be separated from authorization owner")
    expected=_auth_digest(bs,c,d,mode,ag,rid,issuer,v["issued_at"],v["expires_at"])
    if expected!=ad: raise ValueError("authorization digest mismatch")
    return {"candidate_sha":c,"decision":d,"activation_mode":mode,"receipt_id":rid,"result":"VALID"}
def main():
    p=argparse.ArgumentParser(); p.add_argument("record"); p.add_argument("--repository-root",default="."); p.add_argument("--expected-candidate"); p.add_argument("--ledger"); p.add_argument("--output"); a=p.parse_args()
    try:
        ledger=None
        if a.ledger:
            value=json.loads(Path(a.ledger).read_text()); ledger={x["receipt_id"] for x in value if isinstance(x,dict) and isinstance(x.get("receipt_id"),str)}
        r=validate_record(json.loads(Path(a.record).read_text()),Path(a.repository_root).resolve(),a.expected_candidate,ledger)
        if a.output: Path(a.output).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
        print(json.dumps(r,sort_keys=True)); return 0
    except (OSError,json.JSONDecodeError,ValueError) as e:
        print(f"activation receipt validation failed: {e}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())