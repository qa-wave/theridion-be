"""WS-Security: add security headers to SOAP envelopes."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/soap", tags=["ws-security"])


class SecurityConfig(BaseModel):
    type: str  # "UsernameToken" | "X509" | "SAML"
    username: str | None = None
    password: str | None = None
    certificate: str | None = None


class WsSecurityInput(BaseModel):
    wsdl_url: str
    operation: str
    args: dict = {}
    security: SecurityConfig
    endpoint_url: str | None = None
    envelope_xml: str | None = None


class WsSecurityOutput(BaseModel):
    ok: bool
    result: str | None = None
    fault: str | None = None


def _build_username_token(username: str, password: str) -> str:
    nonce = base64.b64encode(uuid.uuid4().bytes).decode()
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        '<wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/'
        'oasis-200401-wss-wssecurity-secext-1.0.xsd" '
        'xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/'
        'oasis-200401-wss-wssecurity-utility-1.0.xsd">'
        "<wsse:UsernameToken>"
        f"<wsse:Username>{username}</wsse:Username>"
        f"<wsse:Password>{password}</wsse:Password>"
        f"<wsse:Nonce>{nonce}</wsse:Nonce>"
        f"<wsu:Created>{created}</wsu:Created>"
        "</wsse:UsernameToken>"
        "</wsse:Security>"
    )


def _inject_header(envelope: str, header_xml: str) -> str:
    # Insert security header into SOAP Header element
    if "<soap:Header" in envelope or "<soapenv:Header" in envelope:
        for tag in ["<soap:Header>", "<soapenv:Header>", "<soap:Header/>", "<soapenv:Header/>"]:
            if tag in envelope:
                if tag.endswith("/>"):
                    replacement = tag.replace("/>", f">{header_xml}</{tag[1:-2]}>")
                else:
                    replacement = tag + header_xml
                return envelope.replace(tag, replacement, 1)
    # No Header element — insert before Body
    for body_tag in ["<soap:Body", "<soapenv:Body"]:
        if body_tag in envelope:
            ns = body_tag.split(":")[0][1:]
            header_block = f"<{ns}:Header>{header_xml}</{ns}:Header>"
            return envelope.replace(body_tag, header_block + body_tag, 1)
    return envelope


@router.post("/ws-security", response_model=WsSecurityOutput)
async def ws_security(body: WsSecurityInput) -> WsSecurityOutput:
    try:
        envelope = body.envelope_xml or (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            "<soap:Header/>"
            f"<soap:Body><{body.operation}>"
            + "".join(f"<{k}>{v}</{k}>" for k, v in body.args.items())
            + f"</{body.operation}></soap:Body></soap:Envelope>"
        )

        if body.security.type == "UsernameToken":
            sec_xml = _build_username_token(
                body.security.username or "",
                body.security.password or "",
            )
        elif body.security.type == "X509":
            cert = body.security.certificate or ""
            sec_xml = (
                '<wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/'
                'oasis-200401-wss-wssecurity-secext-1.0.xsd">'
                "<wsse:BinarySecurityToken "
                'EncodingType="http://docs.oasis-open.org/wss/2004/01/'
                'oasis-200401-wss-soap-message-security-1.0#Base64Binary" '
                'ValueType="http://docs.oasis-open.org/wss/2004/01/'
                f'oasis-200401-wss-x509-token-profile-1.0#X509v3">{cert}'
                "</wsse:BinarySecurityToken></wsse:Security>"
            )
        elif body.security.type == "SAML":
            sec_xml = (
                '<wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/'
                'oasis-200401-wss-wssecurity-secext-1.0.xsd">'
                "<saml:Assertion><!-- SAML stub --></saml:Assertion>"
                "</wsse:Security>"
            )
        else:
            return WsSecurityOutput(ok=False, fault=f"Unknown security type: {body.security.type}")

        envelope = _inject_header(envelope, sec_xml)
        url = body.endpoint_url or body.wsdl_url
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                content=envelope,
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": body.operation},
            )
        return WsSecurityOutput(ok=resp.status_code < 500, result=resp.text)
    except Exception as exc:
        return WsSecurityOutput(ok=False, fault=str(exc))
