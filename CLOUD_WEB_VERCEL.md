# Web privada en Vercel con Turso

La importación histórica a Turso terminó el 25/09/2026 con `status: ok` y el
hash `86db032b1fb814a4122034d160cb18bfade00de34858e6a97bc2f5b0ebce4c6a`.
El destino verificó 13.786 publicaciones, 328 fechas de cobertura, 1.324
textos extraídos históricamente de PDF y 599 resúmenes completos.

## Alcance del piloto web

`api/index.py` expone una aplicación WSGI para Vercel. El sitio consulta Turso
en cada petición, muestra hasta 50 publicaciones por página, permite filtrar
por período, relevancia, tipo y texto, exporta la página a CSV y descarga borradores
`.eml` de un solo día con hasta 25 publicaciones resumidas. El `.eml` se
construye en memoria y no incluye adjuntos. Los enlaces de fuente apuntan al
BORA. El sitio no escribe en Turso ni ejecuta la consulta diaria ni Gemini.

El acceso admite los tres usuarios configurados. Las contraseñas se guardan
como hashes PBKDF2; una cookie firmada expira a las 12 horas. Las acciones
de ingreso usan un token temporal ligado a una cookie. Las acciones privadas
validan un token CSRF ligado a la sesión. Las respuestas privadas llevan
`Cache-Control: no-store`.
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

La configuración `vercel.json` reescribe `/` a la función Python. Vercel
instala dependencias desde `pyproject.toml`; `libsql` figura allí para Linux,
mientras el extra `cloud` permite instalarlo también en Windows para pruebas.
`.vercelignore` y
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

En un proyecto recién creado, Vercel CLI 60.0.1 asignó el primer despliegue a
Production aun sin `--prod`; ese despliegue inicial se retiró porque no tenía
las variables Preview. El primer formulario de Preview rechazó el POST del
navegador; se sustituyó la comprobación de cabeceras por el token del
formulario. Tras un `503` al cargar publicaciones, se añadió la dependencia
`libsql` al runtime Linux y un registro de errores sin valores secretos. La
primera Preview funcional está en
`https://epe-boletin-preview-iufemfs6t-ame-bbfb.vercel.app`. Los siguientes
`vercel deploy` sin `--prod` crean nuevas Previews.

Vercel Authentication protege esa URL de Preview. Para que los otros usuarios
puedan abrirla sin pertenecer al equipo de Vercel, ir a **Deployments**, abrir
la Preview y usar **Share → Anyone with the link**. Compartir ese enlace sólo
con los usuarios autorizados; después cada uno debe ingresar su usuario y
contraseña de la aplicación. Véase la
[guía de enlaces compartibles](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection/sharable-links).

Verificar que el acceso sin sesión sólo muestre el formulario, que los tres
usuarios puedan entrar, que los filtros y el CSV coincidan con Turso y que el
`.eml` se abra como borrador sin adjuntos. Comprobar también que las URLs
oficiales lleven al BORA.

La ejecución diaria, respaldo automatizado y despliegue de producción siguen
pendientes. La configuración de Vercel no debe apuntar a la carpeta de
operación local de Windows.

## Punto de reanudación tras el reinicio (25/09/2026)

El usuario abrió la Preview actual e inició sesión como `USUARIO_1`. Su captura
mostró las tres publicaciones del 24/09/2026, lo que confirmó el inicio de
sesión y la lectura de Turso desde Vercel. Se retiraron las tres Previews
anteriores que habían fallado; `vercel list` mostró solamente la URL actual,
con estado `Ready` y entorno `Preview`. Las pruebas de ingreso con `USUARIO_2`
y `USUARIO_3`, CSV, enlaces BORA y descarga de `.eml` aún no fueron confirmadas
por el usuario.

**Próxima tarea principal:** el usuario señaló que la web desplegada no es
idéntica a la que se había armado localmente. Comparar la Preview con la
interfaz local de `src/epe_boletin/web.py`, `web_views.py`, `web_ui.py`,
`PRODUCT.md`, `DESIGN.md` y `estilo_web_v2.md`. Recuperar en la web de Vercel
la experiencia y funciones esperadas, respetando que el proceso diario,
Gemini, archivos locales y acciones administrativas aún requieren decidir
una arquitectura de ejecución fuera de la función de consulta. Acordar con el
usuario las diferencias concretas si alguna no surge del código o de la
comparación visual. Después validar y desplegar una nueva Preview. Conservar
esta Preview funcional como referencia hasta que la nueva esté verificada.

El 25/09/2026 se creó una segunda Preview con la interfaz local adaptada:
`https://epe-boletin-preview-2hk1504kq-ame-bbfb.vercel.app` (deployment
`dpl_C6dVUmKMGbWTeHSzGzt3SF7EY7H1`, estado `Ready`). Reutiliza los estilos
y el selector de período de la web local. Incluye las vistas Día, Histórico y
Fallas, cinco métricas, filtros por período/relevancia/tipo/texto, calendario,
filas con análisis y fuentes, densidad y selección contextual. El proceso
diario, la generación de resúmenes y los PDF locales aún no tienen ejecución
ni almacenamiento web; se muestran únicamente enlaces oficiales disponibles.
El usuario ingresó en esa Preview y confirmó las tres publicaciones reales.
Las pruebas locales también verificaron calendario, selección, CSV y descarga
del `.eml` con datos de prueba. Tras ajustar la fecha de Buenos Aires y añadir
fallas de publicaciones se creó la Preview final de esta revisión:
`https://epe-boletin-preview-minkza09h-ame-bbfb.vercel.app` (deployment
`dpl_FSDRh7CBcSthDoFtWFes1qGix24i`, estado `Ready`). La petición anónima
respondió HTTP 200 con formulario de acceso. El usuario confirmó que se ve
igual a la web local y señaló dos funciones faltantes: **Consultar ahora** y
**Generar resumen**. Conservar la primera Preview funcional y la confirmada
durante la habilitación de estas acciones.

El worktree contiene cambios locales preexistentes en documentos, scripts y
`tests/test_web_workflows.py`; no descartarlos ni sobrescribirlos. El bundle
de Vercel está en `tmp/vercel_preview_ready` y Node portable en
`tmp/node-portable/node-v24.21.0-win-x64`. No se necesita mantener abierta
la sesión actual de PowerShell para que la Preview siga funcionando.

El 25/09/2026 se desplegó una Preview de la interfaz con ambas acciones y
estado de solicitudes:
`https://epe-boletin-preview-f8oy6ocmw-ame-bbfb.vercel.app`
(deployment `dpl_8koY1g6GcwF73KPFFtqQZgp1NDUW`, estado `Ready`). La
petición anónima respondió HTTP 200 con el formulario. En esa versión los
botones dependían de GitHub Actions y quedaron deshabilitados. Después se
decidió ejecutar las acciones desde Vercel para cumplir con el inicio inmediato
y evitar usar Actions como backend de la aplicación.

Referencias: [runtime Python de Vercel](https://vercel.com/docs/functions/runtimes/python),
[configuración `vercel.json`](https://vercel.com/docs/project-configuration/vercel-json).

## Acciones manuales: consultar y resumir

La interfaz registra cada solicitud en `cloud_jobs` (esquema Turso 3). Un POST
autenticado inicia el trabajo en una función Python de Vercel, con tiempo máximo
de cinco minutos. La página muestra el estado y recarga al concluir. Dos clics
sobre el mismo objetivo mientras está pendiente comparten la solicitud. El
primer POST válido migra Turso de la versión 2 a la 3. Conviene correr antes
el comando de migración, con las variables Turso configuradas en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m epe_boletin.turso_setup --init
```

Las cuatro variables existentes de Turso y autenticación siguen en Preview.
Agregar allí `GEMINI_API_KEY` como **Secret**, con una clave de un proyecto de
Gemini API en **Free Tier** sin facturación activada. Después desplegar una
Preview nueva; las variables no se incorporan retroactivamente a despliegues
anteriores. La consulta de BORA funciona sin esta quinta variable; el botón
de resumen queda deshabilitado hasta configurarla.

Verificación: elegir una fecha sin cobertura y pulsar **Consultar ahora**;
la solicitud debe pasar de pendiente a en curso y completada, y mostrar la
cobertura/publicaciones. Elegir una publicación relevante sin resumen y
pulsar **Generar resumen**; al completar, debe aparecer el texto y habilitarse
la selección para el correo. Si falla, revisar los logs de Vercel; la web
muestra el estado y permite un nuevo intento. No se ejecutan tareas periódicas
en este cambio.

El plan Hobby de Vercel incluye funciones gratuitas dentro de sus límites y
Gemini 3.5 Flash-Lite tiene Free Tier sujeto a cuota. Un día excepcionalmente
grande o un servicio externo lento puede superar los cinco minutos de Vercel;
en ese caso la solicitud debe fallar y se podrá reintentar.

El 25/09/2026 se publicó la Preview con ejecución inmediata en Vercel:
`https://epe-boletin-preview-i0rlmqsbj-ame-bbfb.vercel.app`
(deployment `dpl_2TvTZQH4TdiUExx7asUie2b1NwrM`, estado `Ready`). El GET anónimo
respondió HTTP 200 con el formulario de acceso. La consulta de BORA puede
probarse tras ingresar; la generación de resúmenes requiere agregar la clave
Free Tier de Gemini al entorno Preview y desplegar de nuevo. No se validó aún
la acción real en Turso ni la respuesta de BORA desde Vercel.
