# 🔗 Configuración Railway (Backend) + Vercel (Frontend)

Guía completa para conectar tu backend en Railway con tu frontend en Vercel.

---

## 🎯 Arquitectura

```
┌──────────────────┐         HTTPS          ┌──────────────────┐
│   Vercel         │ ──────────────────────> │   Railway        │
│   (Frontend)     │   API Requests         │   (Backend)      │
│                  │                         │                  │
│  React/Next.js   │ <────────────────────── │   FastAPI        │
└──────────────────┘    JSON Responses       └──────────────────┘
      ↓                                              ↓
  .vercel.app                              .railway.app
```

---

## 📋 Paso 1: Configurar Railway (Backend)

### 1.1 Generar Dominio Público

En Railway Dashboard → Tu Proyecto → **Settings** → **Networking**:

1. Click en **"Generate Domain"**
2. Railway te asigna: `https://invoice-rpa-bot-production.up.railway.app`
3. ✅ **Copia esta URL** - la necesitarás para Vercel

**Importante:** Este dominio es permanente y no cambia entre redeploys.

### 1.2 Configurar Variables de Entorno

En Railway → **Variables**, actualiza `FRONTEND_URL`:

```env
# ANTES de deployar el frontend (solo local)
FRONTEND_URL=http://localhost:3000

# DESPUÉS de deployar en Vercel (actualizar)
FRONTEND_URL=https://tu-app.vercel.app,http://localhost:3000

# Si tienes múltiples frontends o dominios personalizados
FRONTEND_URL=https://tu-app.vercel.app,https://tuempresa.com,http://localhost:3000
```

**Nota:** Soporta múltiples URLs separadas por comas.

### 1.3 Variables Completas en Railway

```env
# === Database ===
DATABASE_URL=${{Postgres.DATABASE_URL}}

# === Auth ===
SECRET_KEY=tu-secret-key-aleatorio
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# === Cloudinary ===
CLOUDINARY_CLOUD_NAME=tu-cloud-name
CLOUDINARY_API_KEY=tu-api-key
CLOUDINARY_API_SECRET=tu-api-secret

# === CORS - Actualizar después de deploy en Vercel ===
FRONTEND_URL=https://tu-app.vercel.app,http://localhost:3000

# === App ===
DEBUG=false
MAX_UPLOAD_SIZE_MB=10
```

### 1.4 Verificar Deploy

```bash
# Health check
curl https://invoice-rpa-bot-production.up.railway.app/health

# Documentación API
https://invoice-rpa-bot-production.up.railway.app/api/docs
```

---

## 🚀 Paso 2: Deployar Frontend en Vercel

### 2.1 Preparar Frontend (React/Next.js)

**Estructura recomendada:**
```
invoice-rpa-bot-frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # Axios/Fetch setup
│   ├── config/
│   │   └── env.ts             # Variables de entorno
│   └── ...
├── .env.local                  # Local dev
├── .env.production            # Production (no subir a git)
└── package.json
```

**Ejemplo `src/config/env.ts`:**
```typescript
export const config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  // o para Next.js:
  // apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
}
```

**Ejemplo `src/api/client.ts`:**
```typescript
import axios from 'axios'
import { config } from '../config/env'

const apiClient = axios.create({
  baseURL: config.apiUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Para cookies/auth
})

// Interceptor para agregar JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default apiClient
```

### 2.2 Variables de Entorno en Vercel

En Vercel Dashboard → Tu Proyecto → **Settings** → **Environment Variables**:

#### Para Vite (React):
```env
Name: VITE_API_URL
Value: https://invoice-rpa-bot-production.up.railway.app
Environment: Production, Preview, Development
```

#### Para Next.js:
```env
Name: NEXT_PUBLIC_API_URL
Value: https://invoice-rpa-bot-production.up.railway.app
Environment: Production, Preview, Development
```

**Importante:** Variables que empiezan con `VITE_` o `NEXT_PUBLIC_` son accesibles en el cliente.

### 2.3 Deploy en Vercel

**Opción 1: Via GitHub (Recomendado)**
```bash
# 1. Push a GitHub
git add .
git commit -m "Ready for Vercel deployment"
git push origin main

# 2. En Vercel Dashboard
# - Connect GitHub repo
# - Vercel auto-detecta framework (Vite/Next.js)
# - Agrega variables de entorno
# - Deploy
```

**Opción 2: Via Vercel CLI**
```bash
npm i -g vercel
vercel login
vercel
```

### 2.4 Obtener URL de Vercel

Después del deploy, Vercel te da:
- **Preview:** `tu-app-git-main-username.vercel.app`
- **Production:** `tu-app.vercel.app`

✅ **Copia esta URL** - necesitas actualizarla en Railway.

---

## 🔄 Paso 3: Actualizar CORS en Railway

Ahora que tienes la URL de Vercel, actualiza Railway:

### En Railway → Variables:
```env
# Actualizar FRONTEND_URL con la URL real de Vercel
FRONTEND_URL=https://tu-app.vercel.app,http://localhost:3000
```

### Redeploy Railway

Railway re-deployará automáticamente al detectar el cambio de variables.

**Verificar CORS:**
```bash
# Desde tu frontend en Vercel, debería funcionar:
curl -X OPTIONS \
  https://invoice-rpa-bot-production.up.railway.app/api/auth/login \
  -H "Origin: https://tu-app.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

---

## 🧪 Paso 4: Testing End-to-End

### 4.1 Test Local → Railway
```typescript
// En tu frontend local (http://localhost:3000)
import apiClient from './api/client'

// Debería funcionar porque Railway permite localhost:3000
const response = await apiClient.get('/health')
console.log(response.data) // { status: "ok", ... }
```

### 4.2 Test Vercel → Railway
```typescript
// Deploy a Vercel y prueba desde https://tu-app.vercel.app

// Login
const login = await apiClient.post('/api/auth/login', {
  email: 'test@example.com',
  password: 'password123'
})

// Upload factura
const formData = new FormData()
formData.append('file', pdfFile)
const upload = await apiClient.post('/api/facturas/upload', formData)
```

### 4.3 Verificar en Browser Console

```javascript
// En https://tu-app.vercel.app
// Abre DevTools → Network

// Si falla con CORS error, verificar:
// 1. FRONTEND_URL en Railway incluye tu dominio Vercel
// 2. Railway re-deployó después de cambiar variables
// 3. No hay typos en la URL
```

---

## 🛠️ Configuración Avanzada

### Dominio Personalizado

**En Railway (Backend):**
1. Settings → Networking → Custom Domain
2. Agregar: `api.tuempresa.com`
3. Configurar CNAME en tu DNS → Railway te da el target

**En Vercel (Frontend):**
1. Settings → Domains
2. Agregar: `tuempresa.com` o `app.tuempresa.com`
3. Configurar DNS → Vercel te indica cómo

**Actualizar Variables:**
```env
# Railway
FRONTEND_URL=https://app.tuempresa.com,http://localhost:3000

# Vercel
VITE_API_URL=https://api.tuempresa.com
```

### Environments Múltiples

**Railway (Backend):**
- `production` branch → `main`
- `staging` branch → `develop`

**Vercel (Frontend):**
- Production → `main` branch
- Preview → PRs y otros branches

**Variables para Staging:**
```env
# Vercel → Environment Variables → Preview
VITE_API_URL=https://invoice-rpa-bot-staging.railway.app
```

---

## 🔐 Seguridad

### Headers de Seguridad

En Railway, tu backend ya tiene CORS configurado. Vercel agrega headers automáticamente:

```javascript
// vercel.json (opcional)
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        }
      ]
    }
  ]
}
```

### Variables Secretas

**Railway:**
- Accesibles en backend (no expuestas al cliente)
- Ejemplo: `DATABASE_URL`, `SECRET_KEY`, `CLOUDINARY_API_SECRET`

**Vercel:**
- Solo exponer lo necesario con `NEXT_PUBLIC_` o `VITE_`
- Mantener keys secretas en Vercel Environment Variables (sin prefix)
- Usar en API routes (Next.js) o serverless functions

---

## 📊 Monitoreo

### Railway Logs
```bash
railway logs --follow
```

### Vercel Logs
```bash
vercel logs tu-app
```

### Browser DevTools
- Network tab → Ver requests y responses
- Console → Ver errores CORS o network

---

## ❗ Troubleshooting

### Error: CORS blocked

**Síntomas:**
```
Access to XMLHttpRequest at 'https://...railway.app' from origin 'https://...vercel.app' 
has been blocked by CORS policy
```

**Solución:**
1. Verificar `FRONTEND_URL` en Railway incluye tu URL de Vercel
2. Railway re-deployó después del cambio
3. Limpiar caché del browser

### Error: Connection refused

**Síntomas:**
```
Failed to fetch
net::ERR_CONNECTION_REFUSED
```

**Solución:**
1. Verificar Railway backend está running: `/health`
2. Verificar `VITE_API_URL` en Vercel tiene la URL correcta
3. No incluir trailing slash: ❌ `https://api.com/` → ✅ `https://api.com`

### Error: 401 Unauthorized

**Solución:**
```typescript
// Verificar que el token JWT se envía correctamente
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

### Environment variables no funcionan

**Vercel:**
- ✅ Usar `NEXT_PUBLIC_` o `VITE_` prefix
- ✅ Re-build después de agregar variables
- ❌ No usar `process.env.MY_VAR` directamente en cliente

---

## ✅ Checklist Final

**Railway (Backend):**
- [ ] Dominio generado en Networking
- [ ] `FRONTEND_URL` incluye URL de Vercel
- [ ] Health check funciona: `/health`
- [ ] API Docs accesibles: `/api/docs`
- [ ] Database conectada

**Vercel (Frontend):**
- [ ] `VITE_API_URL` o `NEXT_PUBLIC_API_URL` configurada
- [ ] Build exitoso
- [ ] Frontend carga correctamente
- [ ] Requests al backend funcionan (ver Network tab)

**Integración:**
- [ ] Login funciona desde frontend
- [ ] Upload de archivos funciona
- [ ] No hay errores CORS en console
- [ ] Tokens JWT se guardan y envían correctamente

---

## 🎉 ¡Listo!

Tu stack completo está deployado:

```
Frontend: https://tu-app.vercel.app
Backend:  https://invoice-rpa-bot-production.railway.app
API Docs: https://invoice-rpa-bot-production.railway.app/api/docs
```

**Próximos pasos:**
1. Configurar CI/CD con GitHub Actions (opcional)
2. Agregar analytics (Vercel Analytics + Railway Metrics)
3. Configurar monitoreo de errores (Sentry)
4. Setup dominios personalizados

¿Necesitas ayuda? Revisa logs:
- **Railway:** `railway logs --follow`
- **Vercel:** `vercel logs`
