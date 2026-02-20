# Logto: Machine-to-Machine (M2M) Apps, Roles, and Access Tokens

Machine-to-machine (M2M) authentication is used when an application (not a user) needs to call protected resources directly (service-to-service), typically without any UI or user interaction.

Since Logto uses RBAC for access control, you must assign **M2M roles** (containing the required permissions) to your **M2M application** before it can obtain an access token for a given resource.

## Common use cases

1. **Accessing Logto Management API**
   - Assign an M2M role that includes the required permissions for the built-in **Logto Management API** resource.
2. **Accessing your own API resource**
   - Assign an M2M role that includes permissions from your custom API resource(s).

You can assign M2M roles either during M2M app creation or later on the app detail page.

## Basics: requesting an M2M access token

An M2M app requests an access token from the token endpoint via `client_credentials`:

- Endpoint: `POST {issuer}/token` (e.g. `https://<tenant>.logto.app/oidc/token`)
- Auth: HTTP Basic Auth, where:
  - `username` = App ID
  - `password` = App Secret
- Body (form-url-encoded):
  - `grant_type=client_credentials`
  - `resource=<resource-indicator-you-want-to-access>`
  - `scope=<space-delimited-scopes>`

### Example: cURL

```bash
LOGTO_ISSUER="https://<tenant>.logto.app/oidc"
APP_ID="<your-app-id>"
APP_SECRET="<your-app-secret>"

RESOURCE="https://<tenant>.logto.app/api" # e.g. Logto Management API resource indicator
SCOPE="all"                               # e.g. Management API uses scope "all"

curl -sS -X POST "${LOGTO_ISSUER}/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic $(printf '%s' "${APP_ID}:${APP_SECRET}" | base64 | tr -d '\r\n')" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "resource=${RESOURCE}" \
  --data-urlencode "scope=${SCOPE}"
```

### Example: Node.js (fetch)

```js
// Note: include a trailing slash so URL resolution keeps the "/oidc/" path.
const logtoIssuer = 'https://<tenant>.logto.app/oidc/';
const tokenEndpoint = new URL('token', logtoIssuer).toString();
const appId = process.env.LOGTO_M2M_APP_ID;
const appSecret = process.env.LOGTO_M2M_APP_SECRET;

export async function fetchM2MAccessToken({ resource, scope }) {
  const basic = Buffer.from(`${appId}:${appSecret}`).toString('base64');

  const res = await fetch(tokenEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      Authorization: `Basic ${basic}`,
    },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      resource,
      scope, // space-delimited string, e.g. "read write"
    }).toString(),
  });

  if (!res.ok) throw new Error(`Token request failed: ${res.status} ${await res.text()}`);

  const json = await res.json();
  return json.access_token;
}
```

## Using the access token

Logto returns `token_type: "Bearer"`, so send the token in your API requests like this:

```http
Authorization: Bearer <access_token>
```

### Example: call Logto Management API

```bash
ACCESS_TOKEN="<granted-access-token>"
curl -sS \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://<tenant>.logto.app/api/applications"
```

## Notes

- Ensure your M2M app has been assigned M2M roles that include the permissions you request via `scope`.
- For many tenants, Logto provides a pre-configured role for Management API access (commonly named similar to “Logto Management API access”).
- Logto M2M tokens do not represent a user; the JWT `sub` will be the App ID.
