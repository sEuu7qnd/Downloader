# Downloader

Programa de escritorio para Windows que descarga **listas de reproducción completas** (y videos sueltos) de YouTube como **video** o **audio**, con interfaz gráfica y también por línea de comandos. Usa [yt-dlp](https://github.com/yt-dlp/yt-dlp) y ffmpeg por dentro.

- **Video:** MP4, WebM, MKV, AVI, MOV (de 360p a 2160p)
- **Audio:** MP3, Opus, M4A, AAC, FLAC, WAV, OGG
- Recuerda la carpeta, el formato, la calidad y las cookies entre sesiones
- En las listas, **omite lo que ya tienes descargado** y solo pide lo que falta

---

## Descargar

Ve a **[Releases → Downloader (última versión)](../../releases/latest)** y baja una de las dos versiones:

| Archivo | Cuándo usarlo |
|---|---|
| **`Downloader-carpeta-rapida.zip`** (recomendada) | Abre y cierra al instante. Extrae **todo** el `.zip` y abre `Downloader.exe` desde dentro de la carpeta, sin separarlo de los demás archivos. Puedes crear un acceso directo al `.exe`. |
| **`Downloader-un-solo-archivo.exe`** | Un único archivo, cómodo de mover o compartir. Tarda más en abrir y en cerrar, porque desempaca unos 100 MB cada vez. |

> Si no ves Releases, entra a la pestaña **Actions**, abre la última ejecución de *Compilar Downloader* y baja el archivo de la sección **Artifacts**.

### Antes de abrirlo

1. **Instala Deno** (recomendado). YouTube exige un entorno de JavaScript para entregar todos los formatos. En una ventana de CMD:
   ```
   winget install DenoLand.Deno
   ```
   También sirven Node.js o Bun. Si falta, el indicador de la esquina superior derecha mostrará **"Listo · falta Deno"** en ámbar.
2. **SmartScreen y antivirus.** El `.exe` no está firmado digitalmente. Windows puede mostrar un aviso azul (*Más información → Ejecutar de todos modos*) y algunos antivirus lo marcan por error (falso positivo, habitual en programas hechos con PyInstaller). Si quieres comprobar que el archivo no fue alterado, compara su huella:
   ```powershell
   Get-FileHash .\Downloader-carpeta-rapida.zip -Algorithm SHA256
   ```
   con la que aparece en las notas de la Release. Si prefieres no usar un binario, puedes [ejecutarlo desde el código](#ejecutar-desde-el-código).

---

## Uso

1. Abre `Downloader.exe`. Cuando el indicador de arriba a la derecha diga **Listo**, ya puedes descargar.
2. Elige la pestaña **Video** o **Audio**, el formato y la resolución o la calidad.
3. Pega uno o varios enlaces (uno por línea) de listas de reproducción o de videos.
4. Elige la carpeta de destino con **Examinar…** y pulsa **Descargar**.

El panel **Registro** muestra el avance, lo que se omite y los errores. **Cancelar** detiene la descarga.

### Formatos

| Video | Notas |
|---|---|
| **MP4** | H.264 + AAC, compatible con casi todo |
| **WebM** | VP9 + Opus |
| **MKV** | No recodifica: es el más rápido |
| **AVI** | Se recodifica (MPEG-4): es el más lento |
| **MOV** | H.264 + AAC; rápido hasta 1080p, por encima se recodifica |

| Audio | Notas |
|---|---|
| **MP3**, **AAC**, **OGG** | Tasa de bits a elegir: 128, 192, 256 o 320 kbps |
| **Opus**, **M4A** | Normalmente usan el audio original sin recodificar |
| **FLAC**, **WAV** | Sin pérdida, pero el origen ya viene comprimido: pesan mucho más sin ganar calidad |

### Línea de comandos

Sin argumentos se abre la ventana. Con enlaces funciona desde CMD o PowerShell:

```
Downloader.exe "URL_DE_LA_LISTA" -f mp3 -c 320
Downloader.exe "URL1" "URL2" -f mkv -r 720 -o C:\Videos
Downloader.exe "URL" --subcarpeta no
Downloader.exe --cookies C:\ruta\cookies.txt
```

| Opción | Qué hace |
|---|---|
| `-f`, `--formato` | `mp4 webm mkv avi mov mp3 opus m4a aac flac wav ogg` |
| `-r`, `--resolucion` | `360 480 720 1080 1440 2160` (video) |
| `-c`, `--calidad` | `128 192 256 320` (MP3, AAC, OGG) |
| `-o`, `--salida` | Carpeta de destino |
| `--subcarpeta si\|no` | Crear o no una subcarpeta con el nombre de la lista |
| `--cookies ARCHIVO` | Importa y guarda un `cookies.txt` |

Lo que no indiques se toma de lo último que usaste.

---

## Listas de reproducción

- **Subcarpeta:** por defecto crea una carpeta con el nombre de la lista y guarda dentro `001 - Título.ext`, `002 - …`. Si la carpeta que elegiste ya se llama como la lista, o ya contiene canciones de ella, la usa tal cual en vez de crear otra dentro. El interruptor **"Crear subcarpeta con el nombre de la lista"** lo desactiva.
- **Lo que ya existe se omite:** antes de descargar, compara los archivos de la carpeta con la lista (ignorando mayúsculas, símbolos y el ancho del número de posición). Solo se piden a YouTube las canciones que faltan, y es necesario que coincidan la carpeta y el formato (MP3 con MP3).
- **Tandas:** en listas grandes, **Límite por lote** (25 / 50 / 100 / Todo, por defecto 50) limita cuántas canciones baja cada vez. Al terminar avisa cuántas quedan; pulsa **Descargar** otra vez para continuar.
- **Ritmo:** con más de 15 canciones pendientes espera unos segundos entre una y otra para reducir el riesgo de bloqueo.
- **Registro de descargas:** en la carpeta de destino se crea `descargados_<formato>.txt` (por ejemplo `descargados_mp3.txt`). Si borraste una canción y quieres volver a bajarla, elimina ese archivo `.txt`: solo se volverán a descargar las que no estén en la carpeta.

---

## Cookies (opcional)

**Para listas y videos públicos no hacen falta**; de hecho conviene dejarlas apagadas. Solo se necesitan para listas privadas, videos con restricción de edad o contenido de tu cuenta.

| Visibilidad de la lista | ¿Cookies? |
|---|---|
| Pública o no listada | No |
| Privada, *Me gusta*, *Ver más tarde* | Sí (o cámbiala temporalmente a *No listada*) |

Cómo importarlas: en una **ventana privada** del navegador inicia sesión en YouTube, abre `youtube.com/robots.txt`, exporta las cookies en formato Netscape con una extensión, **cierra la ventana** y pulsa **Importar…** en la tarjeta *Cookies*. El interruptor **Usar al descargar** las activa o desactiva.

---

## Dónde guarda sus datos

En `%APPDATA%\Downloader`:

| Archivo | Contenido |
|---|---|
| `config.json` | Última carpeta, formato, resolución, calidad, subcarpeta y tanda |
| `cookies.txt` | Tus cookies importadas (contienen sesiones: no lo compartas) |

---

## Solución de problemas

| Síntoma | Qué hacer |
|---|---|
| **"YouTube pidió verificar que no eres un bot"** | Es la protección anti-bot de YouTube. Espera de 1 a 2 horas sin descargar, apaga las cookies si no las necesitas y usa tandas más pequeñas. Evita VPN y proxys. Tras 3 avisos seguidos el programa detiene la lista solo; al volver a pulsar **Descargar** continúa con lo que falte. |
| **"Listo · falta Deno"** | Instala Deno (`winget install DenoLand.Deno`), cierra el programa y ábrelo de nuevo. |
| **Faltan formatos o sale menos resolución de la pedida** | Casi siempre es lo mismo: falta Deno. |
| **"Video unavailable"** | El video pudo ser borrado o hacerse privado, o ser un bloqueo temporal. Esos videos no se bajan con cookies ni sin ellas. |
| **Quedaron archivos `.part` o `.ytdl`** | Son restos de una descarga cortada. Puedes borrarlos. |
| **Un archivo aparece repetido** | Puede pasar si un archivo se renombró o se movió y el programa no pudo reconocerlo. Borra la copia que sobre. |
| **Windows o el antivirus bloquean el `.exe`** | Ver [Antes de abrirlo](#antes-de-abrirlo). |
| **YouTube dejó de funcionar** | YouTube cambia seguido. Vuelve a compilar para traer la versión más reciente de yt-dlp (ver abajo). |

---

## Compilar tú mismo

### Con GitHub Actions (sin instalar nada)

El flujo `.github/workflows/build-exe.yml` compila las dos versiones en un servidor Windows y publica la Release **latest**. Se ejecuta solo al cambiar el código (`main.py`, `core.py`, `config.py`, `logs.py`, `gui/`) o el propio flujo, y a mano desde **Actions → Compilar Downloader → Run workflow**.

### En tu PC

Con Python 3.12 instalado (marca *Add python.exe to PATH*), haz doble clic en `crear_exe.bat`. Deja:

- `dist\Downloader\Downloader.exe` (versión rápida, con su carpeta)
- `dist-unico\Downloader.exe` (un solo archivo)

### Ejecutar desde el código

```
pip install -U "yt-dlp[default]" imageio-ffmpeg
python main.py
```

Si ffmpeg ya está en el PATH se usa ese; si no, el que trae `imageio-ffmpeg`. En Linux hace falta además `tkinter` (`sudo apt install python3-tk`).

---

## Estructura del repositorio

```
main.py                            # punto de entrada: línea de comandos o ventana
core.py                            # motor: formatos, comprobación de existentes, descargas
config.py                          # ajustes y cookies guardados en %APPDATA%\Downloader
logs.py                            # registro de depuración
gui/app.py                         # ventana principal (tkinter)
gui/widgets.py                     # botones, selectores, interruptores, tarjetas
requirements.txt
crear_exe.bat                      # compilación local en Windows
.github/workflows/build-exe.yml    # compilación y publicación automática
```

---

## Aviso legal

Úsalo solo con contenido propio, de dominio público, con licencia que lo permita o con autorización del titular. Respeta los términos de servicio de YouTube y las leyes de derechos de autor de tu país. El programa se ofrece tal cual, sin garantías.
