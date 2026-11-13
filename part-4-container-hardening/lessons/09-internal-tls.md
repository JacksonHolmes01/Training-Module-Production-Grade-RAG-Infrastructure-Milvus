# Lesson 9: Layer 5: Encrypted, Verified Traffic Between Services

Since Part 3, every request to Milvus needs a user name and password. But those requests travel over the private Docker network as **plain HTTP**. Milvus's login is sent as `Authorization: Bearer rag_reader:<password>`, so anyone who can watch that traffic sees the password itself, along with every document the chatbot retrieves.

"It never leaves the Docker network" is a reasonable argument on one laptop. It is a weak one in production, where services run on different machines, networks are shared, and an attacker inside any container on the network could watch or alter traffic.

---

## See the current state

With Layers 1 to 4 on, send the reader's login to Milvus over plain HTTP from inside the API container:

```bash
bin/harden.sh 4
docker exec rag-api python -c "
import httpx
pw = open('/run/secrets/milvus_reader_password').read().strip()
r = httpx.post('http://milvus:19530/v2/vectordb/collections/list', json={'dbName': 'tenant_lab'},
               headers={'Authorization': 'Bearer rag_reader:' + pw})
print(r.status_code, r.text)"
```

```
200 {"code":0,"data":["docs"]}
```

Milvus accepts it, and the password crossed the network in plain text.

---

## The certificates

`bin/setup_secrets.sh` created a small **private certificate authority** (CA) and used it to sign a certificate for Milvus:

```bash
openssl verify -CAfile secrets/tls_ca.crt secrets/milvus_server.crt
openssl x509 -in secrets/milvus_server.crt -noout -text | grep -A1 "Alternative Name"
```

```
secrets/milvus_server.crt: OK
            X509v3 Subject Alternative Name:
                DNS:milvus
```

- The CA is the thing the API **trusts**. Anything the CA signed is accepted
- Milvus's certificate is valid for the name `milvus`, which is exactly the hostname the API connects to
- `secrets/tls_ca.key` (the CA's private key) is never mounted into any container. Whoever holds it can create certificates the API would trust

---

## Read the layer

Open `hardening/05-internal-tls.yml`.

### Milvus turns on TLS

Milvus reads its TLS settings from the same kind of file as its login settings. `setup_secrets.sh` wrote a second copy, `secrets/milvus_user_tls.yaml`, with three additions:

```yaml
common:
  security:
    tlsMode: 1          # the server proves who it is; clients still log in with a password
proxy:
  http:
    port: 19531         # the REST API gets a port of its own
tls:
  serverPemPath: /run/secrets/milvus_server_crt
  serverKeyPath: /run/secrets/milvus_server_key
  caPemPath: /run/secrets/tls_ca_crt
```

Layer 5 mounts that file instead of the plain one:

```yaml
  milvus:
    volumes: !override
      - milvus_data:/var/lib/milvus
      - ./secrets/milvus_user_tls.yaml:/milvus/configs/user.yaml:ro
```

### Why the port changes

Milvus has two front doors: gRPC (used by its Python SDK) and REST (used by this lab). Normally they share port 19530. The first version of this layer just turned on `tlsMode`, and Milvus refused to start:

```
proxy server(http) and external grpc server share the same port, tls mode must be 0
```

Milvus only encrypts its REST API when it has a port of its own. So the REST API moves to **19531**, and both ports now speak only TLS. Reading the startup error, instead of guessing, is how you find details like this.

### The API verifies Milvus

```yaml
  ingestion-api:
    environment:
      MILVUS_URL: "https://milvus:19531"
      MILVUS_CA_CERT: /run/secrets/tls_ca_crt
```

`ingestion-api/app/db.py` passes `MILVUS_CA_CERT` to the HTTP client as the **only** certificate authority it trusts. `milvus-init` gets the same two settings.

| Client setting | Encrypted? | Checks the certificate? | Checks the hostname? |
|---|:-:|:-:|:-:|
| `http://` (Layers 0 to 4) | no | no | no |
| `https://`, certificate checking turned off | yes | no | no |
| `https://`, trusting only the lab CA (this layer) | yes | yes | yes |

Only the last row stops an attacker who can intercept traffic from pretending to be the database. Encryption without verification just means you have an encrypted conversation with whoever answered.

### What about etcd and MinIO?

Their traffic with Milvus stays unencrypted in this lab. They sit on the `milvus-deps` network, which only Milvus joins (Part 3), so the API, NGINX, and the UI cannot even see it. That is a deliberate trade-off, not an oversight: in production, where they may run on other machines, they need TLS too.

---

## Apply it

```bash
bin/harden.sh 5
bin/smoke_test.sh
```

## Verify the connection is encrypted and verified

Make four requests from inside the API container:

```bash
docker exec rag-api python -c "
import httpx
pw = open('/run/secrets/milvus_reader_password').read().strip()
h = {'Authorization': 'Bearer rag_reader:' + pw}
for url, v, label in [('http://milvus:19531', True, 'plain http :19531'),
                      ('http://milvus:19530', True, 'plain http :19530'),
                      ('https://milvus:19531', '/run/secrets/tls_ca_crt', 'https, lab CA'),
                      ('https://milvus:19531', True, 'https, public CAs')]:
    try:
        r = httpx.post(url + '/v2/vectordb/collections/list', json={'dbName': 'tenant_lab'}, headers=h, verify=v, timeout=5)
        print(f'{label:<18} {r.status_code} {r.text}')
    except Exception as e:
        print(f'{label:<18} refused: {str(e)[:70]}')
"
```

```
plain http :19531  refused: [Errno 104] Connection reset by peer
plain http :19530  refused: [Errno 104] Connection reset by peer
https, lab CA      200 {"code":0,"data":["docs"]}
https, public CAs  refused: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable
```

- **Plain HTTP is refused on both ports.** The password never travels unencrypted again
- **The lab CA works.** This is what the API and `bin/milvus.sh` use
- **A public CA does not.** No outside authority vouches for this certificate, and none should

## Verify an impostor is refused (expected to fail)

Hostname checking matters too. Connect to the same Milvus, with the right CA, but by its IP address instead of its name:

```bash
IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' rag-milvus | awk '{print $1}')
docker exec rag-api python -c "
import httpx
try:
    httpx.post('https://$IP:19531/v2/vectordb/collections/list', json={}, verify='/run/secrets/tls_ca_crt', timeout=5); print('CONNECTED (bad)')
except Exception as e:
    print('refused:', str(e)[:110])
"
```

```
refused: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: IP address mismatch, certificate is not valid for '172.18.0.4'
```

The certificate says `milvus`, so the client refuses anything else, even the right server under a different name. An attacker with a certificate for some other name gets the same answer.

## Audit

```bash
python3 bin/audit.py
```

The score does not change: TLS is not on the checklist, because the checklist looks at containers, not connections. Not everything important fits on one scorecard.

Next: [Layer 6: Scan and Pin Your Images](10-scan-and-pin.md)
