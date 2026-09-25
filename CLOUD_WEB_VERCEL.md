# Web privada en Vercel con Turso

La importación histórica a Turso terminó el 25/09/2026 con `status: ok` y el
hash `86db032b1fb814a4122034d160cb18bfade00de34858e6a97bc2f5b0ebce4c6a`.
El destino verificó 13.786 publicaciones, 328 fechas de cobertura, 1.324
textos extraídos históricamente de PDF y 599 resúmenes completos.

## Alcance del piloto web

`api/index.py` expone una aplicación WSGI para Vercel. El sitio consulta Turso
en cada petición, muestra hasta 50 publicaciones por página, permite filtrar
por fecha, relevancia y texto, exporta la página a CSV y descarga borradores
`.eml` de un solo día con hasta 25 publicaciones resumidas. El `.eml` se
construye en memoria y no incluye adjuntos. Los enlaces de fuente apuntan al
BORA. El sitio no escribe en Turso ni ejecuta la consulta diaria ni Gemini.

El acceso admite los tres usuarios configurados. Las contraseñas se guardan como hashes
PBKDF2; una cookie firmada expira a las 12 horas. Las acciones POST validan
origen y token CSRF. Las respuestas privadas llevan `Cache-Control: no-store`.
La contraseña, el token de Turso y el secreto de sesión no van al repositorio.

## Comprobación de sólo lectura contra Turso

En la misma sesión de PowerShell que contiene `TURSO_DATABASE_URL` y
`TURSO_AUTH_TOKEN`:

```powershell
Set-Location 'RUTA_DEL_WORKTREE'
.\.venv\Scripts\python.exe -m epe_boletin.cloud_web_preflight
```

La salida `status: ok` confirma las consultas de la vista y que se puede
construir un borrador en memoria. No imprime el contenido ni los secretos.
La ejecución del 25/09/2026 contra Turso respondió `latest_date: 2026-09-24`,
`visible_count: 3`, `page_rows: 3` y `draft: ok`.

## Preparar credenciales para tres personas

Generar un único JSON en PowerShell. `getpass` pide cada contraseña dos veces
sin mostrarla ni dejarla en el historial:

```powershell
.\.venv\Scripts\python.exe -m epe_boletin.cloud_auth --user USUARIO_1 --user USUARIO_2 --user USUARIO_3
```

Copiar la línea JSON completa a `EPE_WEB_USERS`, sin editar sus comillas ni
separadores. El código acepta cualquier cantidad positiva de usuarios.
Generar además un secreto de sesión aleatorio:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Guardar el valor como `EPE_WEB_SESSION_SECRET`. Mantener estos cuatro valores
como variables privadas de servidor en el entorno **Preview** de Vercel:

- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- `EPE_WEB_USERS`
- `EPE_WEB_SESSION_SECRET`

No configurar `GEMINI_API_KEY` en Vercel: la web no genera resúmenes. Esas
acciones quedarán en el proceso diario separado. Si se cambia un hash o el
secreto de sesión, las sesiones existentes dejan de funcionar.

## Despliegue de prueba desde Windows

La configuración `vercel.json` reescribe `/` a la función Python. El paquete
se instala desde `requirements.txt` con el extra `cloud`. `.vercelignore` y
`excludeFiles` excluyen la copia histórica, los archivos operativos, pruebas,
PDFs y `.eml` del bundle.

El repositorio GitHub público tiene 32 commits locales aún no publicados. Para
esta Preview se usa una carpeta de despliegue independiente y no se conecta
GitHub. Generarla desde la raíz del worktree:

```powershell
.\.venv\Scripts\python.exe scripts\build_vercel_preview.py --output tmp\vercel_preview_ready
```

El script sólo copia archivos `.py` del paquete y los cinco archivos de
entrada/configuración. Rechaza un destino que ya exista. El resultado queda
en `tmp/`, fuera de Git; nunca incluye la base depurada ni las credenciales.
Si se permite instalar programas, instalar [Node.js LTS para Windows](https://nodejs.org/en/download)
y abrir una nueva terminal. Luego instalar la
[CLI oficial de Vercel](https://vercel.com/docs/cli):

```powershell
npm.cmd install --global vercel
Set-Location 'RUTA_DEL_WORKTREE\tmp\vercel_preview_ready'
vercel.cmd login
vercel.cmd link
```

### Windows sin permisos para instalar Node.js

Descargar el [ZIP oficial de Node.js LTS para Windows x64](https://nodejs.org/dist/v24.21.0/node-v24.21.0-win-x64.zip)
en `Descargas`. El ZIP se extrae dentro de `tmp/` sin ejecutar un instalador.
Desde la raíz del worktree, en PowerShell:

```powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\node-v24.21.0-win-x64.zip" -DestinationPath 'tmp\node-portable'
$nodeDir = (Resolve-Path 'tmp\node-portable\node-v24.21.0-win-x64').Path
$env:Path = "$nodeDir;$env:Path"
& "$nodeDir\node.exe" --version
& "$nodeDir\npx.cmd" --yes vercel@latest --version
```

`npx` descarga la CLI a la caché del usuario, sin instalación global. Para
los pasos siguientes, usar `& "$nodeDir\npx.cmd" --yes vercel@latest` en lugar
de `vercel.cmd` y mantener abierta la misma sesión de PowerShell. Si el ZIP ya
se extrajo, no repetir `Expand-Archive`.

`vercel link` permite crear un proyecto nuevo. Elegir la cuenta propia y usar
la carpeta actual como raíz. No conectar un repositorio Git para este piloto.
En el panel del proyecto, cargar las cuatro variables enumeradas arriba sólo
para el entorno **Preview**. Después, desde esa misma carpeta:

```powershell
vercel.cmd deploy
```

Sin `--prod`, Vercel crea una Preview. Verificar que el acceso sin
sesión sólo muestre el formulario, que los tres usuarios puedan entrar, que los
filtros y el CSV coincidan con Turso y que el `.eml` se abra como borrador sin
adjuntos. Comprobar también que las URLs oficiales lleven al BORA.

La ejecución diaria, respaldo automatizado y despliegue de producción siguen
pendientes. La configuración de Vercel no debe apuntar a la carpeta de
operación local de Windows.

Referencias: [runtime Python de Vercel](https://vercel.com/docs/functions/runtimes/python),
[configuración `vercel.json`](https://vercel.com/docs/project-configuration/vercel-json).
