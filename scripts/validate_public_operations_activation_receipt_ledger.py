#!/usr/bin/env python3
"""Validate an append-only public-operations activation receipt ledger."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path
SHA=re.compile(r"^[0-9a-f]{40}$"); DIGEST=re.compile(r"^[0-9a-f]{64}$"); SAFE=re.compile(r"^[A-Za-z0-9._/-]+$")
TOP={"schema","schema_version","entries","ledger_digest"}
ENTRY={"sequence","receipt_id","candidate_sha","decision","activation_mode","receipt_path","receipt_sha256","authorization_digest","issued_at","previous_entry_digest","entry_digest"}
FORBIDDEN=("password","secret","token","api_key","private_key","credential")
def _scan(v):
    if isinstance(v,dict):
        for k,n in v.items():
            if any(x in k.lower() for x in FORBIDDEN): raise ValueError(f"forbidden secret-like key: {k}")
            _scan(n)
    elif isinstance(v,list):
        for n in v:_scan(n)
def _path(v):
    if not isinstance(v,str) or not SAFE.fullmatch(v) or v.startswith("/") or ".." in v.split("/"): raise ValueError("receipt path is unsafe")
    return v
def _entry_digest(entry):
    payload={k:entry[k] for k in ENTRY if k!="entry_digest"}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _ledger_digest(entries):
    return hashlib.sha256(json.dumps([e["entry_digest"] for e in entries],separators=(",",":")).encode()).hexdigest()
def validate_ledger(value,root):
    if not isinstance(value,dict) or set(value)!=TOP: raise ValueError("top-level keys do not match contract")
    _scan(value)
    if value["schema"]!="lionsforge.public-operations-activation-receipt-ledger" or value["schema_version"]!=1: raise ValueError("schema is invalid")
    entries=value["entries"]
    if not isinstance(entries,list): raise ValueError("entries must be a list")
    seen=set(); prior="0"*64; previous_time=None
    for index,entry in enumerate(entries,1):
        if not isinstance(entry,dict) or set(entry)!=ENTRY: raise ValueError(f"entry {index} keys do not match contract")
        if entry["sequence"]!=index: raise ValueError("sequence is not contiguous")
        rid=entry["receipt_id"]
        if not isinstance(rid,str) or len(rid)<8 or rid in seen: raise ValueError("receipt_id is invalid or duplicated")
        seen.add(rid)
        if not isinstance(entry["candidate_sha"],str) or not SHA.fullmatch(entry["candidate_sha"]): raise ValueError("candidate_sha is invalid")
        for field in ("receipt_sha256","authorization_digest","previous_entry_digest","entry_digest"):
            if not isinstance(entry[field],str) or not DIGEST.fullmatch(entry[field]): raise ValueError(f"{field} is invalid")
        if entry["previous_entry_digest"]!=prior: raise ValueError("ledger chain is broken")
        if entry["decision"] not in {"GO","NO-GO"}: raise ValueError("decision is invalid")
        if entry["activation_mode"] not in {"NONE","CONTROLLED-BETA","GENERAL-AVAILABILITY"}: raise ValueError("activation_mode is invalid")
        if entry["decision"]=="NO-GO" and entry["activation_mode"]!="NONE": raise ValueError("NO-GO requires activation mode NONE")
        try: issued=datetime.fromisoformat(entry["issued_at"].replace("Z","+00:00"))
        except Exception as exc: raise ValueError("issued_at is invalid") from exc
        if issued.tzinfo is None or (previous_time and issued<previous_time): raise ValueError("issued_at ordering is invalid")
        previous_time=issued
        p=root/_path(entry["receipt_path"])
        if not p.is_file() or p.is_symlink(): raise ValueError("receipt file is missing or unsafe")
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry["receipt_sha256"]: raise ValueError("receipt digest mismatch")
        receipt=json.loads(raw)
        for field in ("receipt_id","candidate_sha","decision","activation_mode","authorization_digest","issued_at"):
            if receipt.get(field)!=entry[field]: raise ValueError(f"receipt {field} mismatch")
        if entry["entry_digest"]!=_entry_digest(entry): raise ValueError("entry digest mismatch")
        prior=entry["entry_digest"]
    if value["ledger_digest"]!=_ledger_digest(entries): raise ValueError("ledger digest mismatch")
    return {"result":"VALID","entry_count":len(entries),"ledger_digest":value["ledger_digest"]}
def main():
    p=argparse.ArgumentParser(); p.add_argument("ledger"); p.add_argument("--repository-root",default="."); p.add_argument("--output"); a=p.parse_args()
    try:
        result=validate_ledger(json.loads(Path(a.ledger).read_text()),Path(a.repository_root).resolve())
        if a.output: Path(a.output).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        print(json.dumps(result,sort_keys=True)); return 0
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        print(f"activation receipt ledger validation failed: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
