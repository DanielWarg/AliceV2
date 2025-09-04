# Security & Privacy Policy

## 🛡️ Security Overview

Alice v2 tar säkerhet, integritet och transparens på största allvar. Denna policy beskriver hur vi arbetar med säkerhet, GDPR-efterlevnad och AI Act-krav.

## 🚨 Reporting Security or Privacy Issues

**Rapportera aldrig säkerhetsproblem som publika GitHub-issues.**

Kontakta istället:

- **Email**: [daniel@postboxen.se](mailto:daniel@postboxen.se)
- **Svarstid**: Inom 24 timmar

Vid behov kan kryptering med PGP erbjudas.

### Vad som ska inkluderas i en rapport

- Detaljerad beskrivning av problemet
- Steg för reproduktion
- Bedömning av potentiell påverkan
- Eventuella förslag på lösning
- Kontaktinformation

### Vår responsprocess

1. Bekräftelse av mottagande inom 24h
2. Utredning inom 72h
3. Fixutveckling enligt prioritet
4. Koordinerad disclosure med rapportören
5. Erkännande om så önskas

---

## 🔒 Security Measures

### Guardian System (deterministisk säkerhet)

- Hårdkodade trösklar (RAM, CPU, temp, batteri)
- Automatisk brownout och fallback
- Rate limiting: max 3 kills/30min
- Ingen AI-inblandning i säkerhetsloopar

### Webhook Security (n8n)

- HMAC-SHA256 signaturer med timestamp (`X-Alice-Timestamp`, `X-Alice-Signature`)
- Tillåten tidsdrift: ±300s
- Replay-skydd: Redis SETNX med TTL 600s
- Secret: `ALICE_WEBHOOK_HMAC_SECRET`

### API Security

- Alla endpoints kräver giltig API-nyckel (`X-API-Key`)
- Rollbaserad åtkomst: Admin, User, Service, Monitor

### Network Security

- Intern nätverksisolering i Docker/K8s
- Rate limiting:
  – API: 100 req/min per nyckel
  – Voice: 10 WebSocket-anslutningar per IP
  – Guardian health: 1000 req/min

---

## 🔐 GDPR Compliance

### Principer

- **Data minimization**: Endast nödvändig data lagras
- **Purpose limitation**: Data används enbart för AI-assistentens funktioner
- **Storage limitation**: Session memory (Redis) raderas automatiskt efter 7 dagar
- **User control**: Användare kan radera minne omedelbart med `POST /memory/forget` (<1s)
- **Privacy by design**: Local-first, inget lämnar enheten utan aktivt samtycke

### Data Classification

- **Public**: Systemstatus, Guardian state
- **Internal**: Prestandamått, felkoder
- **Restricted**: Konversationer, röstdata
- **Secret**: API-nycklar, tokens

### Logging & PII

- PII (t.ex. email, personnummer) maskas i loggar
- Ingen röst eller text sparas permanent utan samtycke
- Strukturerad JSONL-loggning med trace-ID

---

## 🤖 AI Transparency (AI Act)

Alice v2 följer EU:s AI-förordning (AI Act) genom:

- **Transparens**: HUD visar alltid vilken modell som används (lokal eller OpenAI)
- **Opt-in för moln**: `cloud_ok` krävs innan något skickas till externa API:er
- **User confirmation**: Planner bekräftar tool-calls med användaren innan exekvering
- **Audit logs**: Alla AI-beslut loggas i `data/telemetry/` för spårbarhet
- **Explainability**: Intent + route badges i UI gör systemets beslut begripliga

---

## 📋 Security Monitoring

### Threat Detection

- Misslyckad autentisering → rate limiting + alert
- Ovanliga trafikmönster → blockering
- Guardian triggers → automatiskt skydd
- Exfiltreringsförsök → avvikelsedetektering

### Security Metrics

- `authentication_failure`
- `rate_limit_exceeded`
- `guardian_emergency_triggered`
- `memory_consent_violation`

### Audit Logging Example

```json
{
  "timestamp": "2025-09-03T19:22:00Z",
  "event": "authentication_failure",
  "source_ip": "192.168.1.50",
  "endpoint": "/api/chat",
  "reason": "invalid_api_key"
}
```

---

## 🛠️ Secure Development

### Python

- Typanoteringar på alla funktioner
- Pydantic för validering
- `secrets` för nycklar
- `ruff`, `mypy`, `pytest` för kvalitet

### TypeScript

- Zod för inputvalidering
- DOMPurify för HTML-sanering
- ESLint + Prettier för kodstil

### Dependencies

- `safety check`, `bandit` för Python
- `npm audit`, `yarn audit` för Node.js
- `docker scout cves` för images
- Kritiska sårbarheter patchas inom 24h

---

## ⚡ Incident Response

**P0**: Data breach → omedelbar isolering och rapportering
**P1**: Auth bypass → fix inom 24h
**P2**: DoS → mitigering inom 72h
**P3**: Mindre konfigurationsfel → fix i nästa release

---

## 📞 Contact

### Security Team

- **Primary**: [daniel@postboxen.se](mailto:daniel@postboxen.se)

### External Resources

- **CERT-SE**: Computer Emergency Response Team Sweden
- **Police**: Cybercrime division (if criminal activity)
- **Legal**: Data protection authority (for GDPR incidents)

---

**Senast uppdaterad**: 2025-09-03
