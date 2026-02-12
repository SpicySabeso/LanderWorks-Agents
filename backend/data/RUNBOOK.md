🧠 DENTAL AGENT – COMANDOS ESENCIALES (VS Code / Windows)
1️⃣ Activar entorno virtual (venv)

👉 Siempre lo primero antes de ejecutar nada.

.\.venv\Scripts\Activate.ps1


Si no existe el venv (solo una vez):

python -m venv venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

2️⃣ Lanzar el backend / agente (FastAPI)

Desde la raíz del proyecto:

uvicorn backend.main:app --reload --port 8000


Resultado esperado:

API viva en http://localhost:8000

Logs en tiempo real en la terminal

3️⃣ Probar el agente en local (sin WhatsApp)

Si tienes endpoint tipo /chat:

curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"sender":"test-local","user":"Hola"}'


(O usa Postman / Thunder Client si prefieres GUI)

4️⃣ Exponer el backend con Cloudflare Tunnel (IMPRESCINDIBLE)

👉 Esto es lo que permite que Twilio llame a tu localhost.

Arrancar Cloudflare (cada vez que pruebas)
cloudflared tunnel --url http://localhost:8000


Salida clave (ejemplo):

https://seems-boxes-asn-servers.trycloudflare.com


⚠️ Ese dominio cambia cada vez.
Ese es el que tienes que copiar en Twilio.

5️⃣ URL correcta para Twilio WhatsApp Webhook

En Twilio → WhatsApp → Sandbox / Number → WHEN A MESSAGE COMES IN

https://TU-TUNEL.trycloudflare.com/whatsapp-twilio


Ejemplo real:

https://seems-boxes-asn-servers.trycloudflare.com/whatsapp-twilio


👉 Método: POST
👉 Guardar cambios

6️⃣ Ver base de datos (leads + handoffs)

Abrir SQLite:

sqlite3 .\backend\data\leads.db


Ver tablas:

.tables


Ver últimos handoffs:

SELECT * FROM handoffs ORDER BY id DESC LIMIT 10;


Salir:

.exit

7️⃣ Resetear estados / sesiones (si algo se queda pillado)

Si tienes función cleanup_sessions() se ejecuta sola, pero si no:

👉 Borra sesiones manualmente:

DELETE FROM sessions;


👉 O borra un sender concreto:

DELETE FROM sessions WHERE sender = 'test_final-1';

