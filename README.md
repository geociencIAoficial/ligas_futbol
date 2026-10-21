# Selecciones DB

Base SQLite con las convocatorias y participaciones de las selecciones masculinas, a partir del Mundial 2026, para estudiar el recambio generacional.

## Fuente

Todo sale de Wikipedia, a través de su API oficial. Es gratis, no pide registro ni llave, y el contenido está bajo licencia CC BY-SA 4.0: si publicas datos derivados, cita a Wikipedia y compártelos bajo la misma licencia.

| Dato | Página |
|---|---|
| Listas de 26 del Mundial (dorsal, posición, fecha de nacimiento, caps, goles, club) | *2026 FIFA World Cup squads* |
| Alineaciones, cambios y tarjetas de cada partido, de donde se calculan los minutos | Páginas de cada grupo (*2026 FIFA World Cup Group A* … *L*) y *2026 FIFA World Cup knockout stage* |
| Convocatorias posteriores (cada fecha FIFA) | Sección *Current squad* de cada selección |
| Liga de cada club | Infobox del artículo del club |

No se toca Transfermarkt, Sofascore ni FotMob, porque sus términos prohíben la extracción automatizada.

## Uso

```bash
pip install -r requirements.txt
python selecciones.py init                  # pide tu correo una sola vez
python selecciones.py mundial               # 48 listas
python selecciones.py partidos --muestra    # 104 partidos con minutos
python selecciones.py ligas                 # liga de cada club (~1 minuto)
python selecciones.py reporte               # recambio_mundial.xlsx
python selecciones.py snapshot --ventana 2026-10
python selecciones.py ligas                 # solo consulta los clubes nuevos
python selecciones.py reporte --ventana 2026-10   # recambio_2026-10.xlsx
```

## El Excel

- **Leyenda**: qué significa cada código y color.
- **Recambio** (solo con `--ventana`): retención, similitud, edades y nombres de quién sale y entra, por selección.
- **Criterios**: cómo se definió cada categoría y en cuál quedó cada selección y cada club.
- **Top jugadores**: los que más minutos jugaron, en general y filtrados por categoría (clubes top 10, selecciones élite, ambas cosas, fuera de las cinco grandes ligas...).
- **Categorías**: cruce entre la categoría del club y la de la selección, en jugadores, minutos y porcentaje.
- **Ligas**: jugadores que aporta cada liga (y de qué categoría de selección son), minutos por ronda, fase de grupos, eliminatorias, total y porcentaje del Mundial.
- **Clubes**: por cada club, su categoría, su liga, los minutos que jugaron sus futbolistas en cada jornada del Mundial (Jornada 1 a 3, dieciseisavos, octavos… final), el total y de qué selecciones son esos jugadores. Ordenada de más a menos minutos.
- **Top clubes por jornada**: los 15 clubes con más minutos en cada jornada, con el nombre, la selección y los minutos de cada jugador.
- **Jugadores**: la lista completa con selección, club, liga, categorías y minutos por jornada. De ella salen las fórmulas de las demás hojas.
- **Una hoja por selección**: cada fila es un jugador en orden alfabético y cada columna un partido (en orden de fecha) o una convocatoria sin partidos cargados. Cada celda dice `T 90'` (titular), `S 24'` (entró de cambio), `Banca`, `No conv.` o `Sin datos`. Las columnas PJ, Titular, Cambio, Banca y Minutos son fórmulas, y el encabezado tiene filtro para ordenar.

Los partidos que no son del Mundial se asocian a la convocatoria de su mismo mes: un partido del 10/10/2026 se compara contra la lista `2026-10`. Por eso conviene etiquetar las ventanas con el formato AAAA-MM.

El correo se guarda en `config.json`. Wikipedia pide que quien consulta su API deje un contacto; no es una cuenta.

`--muestra` imprime la alineación del primer partido de cada página para que la compares a ojo con Wikipedia. Al final, el comando avisa si algún partido no quedó con 11 titulares por lado.

## Partidos fuera del Mundial

Las páginas de la Nations League y de otros torneos usan el mismo formato de alineaciones, así que puedes pasarlas a mano:

```bash
python selecciones.py partidos --paginas "2026–27_UEFA_Nations_League_A" --competicion "UEFA NL 2026-27"
```

El nombre exacto de la página es el que aparece en la URL de Wikipedia, después de `/wiki/`. Muchos amistosos no tienen alineaciones en Wikipedia; para esos, la fuente gratuita más completa que queda son las propias federaciones.

## Tablas

- `selecciones`, `jugadores`, `clubes`
- `listas`: una convocatoria publicada (`mundial-2026`, `2026-10`, …) con su nota de origen
- `convocados`: quién estuvo en cada lista, con su club, caps y goles en ese momento
- `partidos` (con su ronda: grupo, octavos, etc.) y `participaciones`: titular o suplente, minuto de entrada y salida, minutos jugados, amarillas y expulsión

Los jugadores se identifican por su artículo de Wikipedia, así que la misma persona queda unida entre listas y partidos sin necesidad de cruzar nombres.

## Limitaciones conocidas

- Los minutos se calculan sobre 90 (o 120 con prórroga); el tiempo añadido no se cuenta. Un jugador que entra en el 90+3 queda con 1 minuto.
- Wikipedia no da calificaciones ni estadísticas por jugador (pases, tiros, etc.).
- La sección *Current squad* la editan voluntarios. Hay que correr `snapshot` en cada ventana, porque Wikipedia sobrescribe la sección. Revisa `listas.nota` para saber para qué partidos fue la convocatoria.
- La liga sale del infobox del club. Si un club no tiene artículo o infobox queda como "(sin dato)"; `ligas` lista cuáles son.
- Las ligas no se traducen: aparecen con el nombre del artículo de Wikipedia en inglés (Premier League, La Liga, Liga MX...).

## Categorías

Las categorías de selecciones y clubes son una clasificación propia, definida al inicio de `selecciones.py` en `CAT_SELECCIONES` y `CAT_CLUBES`. Puedes mover equipos de una a otra editando esas listas; el reporte las recalcula cada vez.

- Selecciones: 1 Élite, 2 Segunda línea, 3 Buen equipo, 4 Resto.
- Clubes: 1 Top 10 mundial, 2 Top segunda línea, 3 Importante (incluye automáticamente a todo club de primera división de las cinco grandes ligas), 4 Resto.

## Clasificación mundial de clubes

Tabla de posiciones de la temporada en curso para unas 45 primeras divisiones de las seis confederaciones, también desde Wikipedia.

```bash
python selecciones.py tablas                    # baja la tabla de cada liga (~2 minutos)
python selecciones.py tablas --ligas "Liga MX"  # solo algunas
python selecciones.py panel                     # genera panel.html; se abre con doble clic
```

El panel funciona sin internet y tiene cuatro filtros: mundo, confederación, país (una liga) y personalizado. En el personalizado puedes agregar hasta 10 ligas completas, equipos sueltos de cualquier liga, o ambas cosas. Todas las columnas se ordenan de menor a mayor y al revés con un clic. El rendimiento es puntos obtenidos entre 3 por partido jugado, y el panel tiene un mínimo de partidos (5 por defecto) para que quien lleva un solo partido no encabece la tabla.

Las ligas están en `LIGAS_TXT`, en `clasificacion.py`. Cada línea lleva el patrón del título del artículo de Wikipedia. Si `tablas` avisa que una liga quedó sin tabla, corrige ahí su título. Solo se incluye la primera división de cada país, y los puntos son los de la tabla de Wikipedia (incluyen sanciones).

## App para el celular (GitHub Pages)

`python selecciones.py web` crea la carpeta `docs/` con una app instalable (PWA): `index.html`, ícono, manifiesto y service worker. Con la app instalada, la última clasificación se ve aunque no haya internet.

1. Sube el proyecto a un repositorio de GitHub (el `.gitignore` deja fuera la base, la caché y tu `config.json`).
2. En el repositorio: Settings, Secrets and variables, Actions, New repository secret. Nombre `WIKI_CONTACTO`, valor tu correo (Wikipedia pide un contacto al consultar su API).
3. Settings, Pages: Source = Deploy from a branch, rama `main`, carpeta `/docs`.
4. Pestaña Actions, "Actualizar clasificación", Run workflow. La primera corrida crea `docs/` y tarda unos 3 minutos. Después se actualiza sola cada día.
5. Abre `https://TU-USUARIO.github.io/NOMBRE-DEL-REPO/` en el celular. En Android: menú de Chrome, Instalar app. En iPhone: Safari, Compartir, Añadir a pantalla de inicio.

Si prefieres no usar Actions, corre `tablas` y `web` en tu computadora y sube la carpeta `docs/` con un commit.

### APK para Android (opcional)

La app ya se instala desde Chrome (Instalar app) y se comporta como una app nativa. El APK sirve si quieres pasarla como archivo o subirla a Google Play. No se genera en este proyecto: se arma con PWABuilder a partir de la dirección de GitHub Pages.

1. Con la app ya publicada y abierta en `https://TU-USUARIO.github.io/NOMBRE-DEL-REPO/`, entra a pwabuilder.com y pega esa dirección.
2. PWABuilder revisa el manifiesto y el service worker. Elige Package for stores, Android.
3. Pon el identificador del paquete (por ejemplo `com.tunombre.clubes`), el nombre de la app y deja la opción de crear una firma nueva.
4. Descarga el ZIP. Trae el `.apk` (para instalar a mano), el `.aab` (para Play Store) y el archivo de firma `signing.keystore` con su contraseña. Guarda esos dos últimos: sin ellos no podrás publicar actualizaciones.
5. Pasa el `.apk` al celular y ábrelo. Android pedirá permiso para instalar desde esa fuente.

Para que la app abra sin la barra de dirección de Chrome, el dominio debe servir `/.well-known/assetlinks.json` (PWABuilder lo incluye en el ZIP). Con un sitio de proyecto (`usuario.github.io/repo`) eso solo es posible si ese archivo está en la raíz de `usuario.github.io`, es decir, en un repositorio llamado `usuario.github.io`. Si no, la app funciona igual pero muestra la barra.

### Ligas con página en Wikipedia en español

Algunas ligas (Costa Rica, Panamá, Guatemala, Honduras, Chile, Uruguay, Paraguay, Ecuador, Sudáfrica, Emiratos y Catar) no tienen todavía artículo de la temporada en inglés, pero sí en español. En `LIGAS_TXT` esas páginas llevan el prefijo `es:`, por ejemplo `es:Campeonato de {s} {y} (Costa Rica)`, y el programa las consulta en es.wikipedia.org. Detalles:

- Panamá y Paraguay prueban primero el Clausura del año y, si todavía no tiene partidos, usan el Apertura.
- En Uruguay y Ecuador, la página trae varias tablas; el programa toma la tabla anual o acumulada de 2026 (`LIGAS_PREFER`) y descarta las de descenso y promedios.
- Las tablas en español se reconocen por encabezados como Equipo, PJ, PG, PE, PP, GF, GC y Pts.

### Si una liga sigue sin tabla

`tablas` imprime, bajo cada liga sin tabla, el motivo de cada título probado: "no existe" (el título está mal o el artículo no se ha creado) o "existe pero no se reconoció la tabla" (el título está bien y falla el lector). Corrige el título en `LIGAS_TXT`. Mientras tanto puedes llenar `datos_manuales.csv` (columnas `liga,equipo,pj,g,e,p,gf,gc,pts`; `pts` puede ir vacío y se calcula como 3 por victoria más empates). El nombre de la liga debe ser exactamente el de `LIGAS_TXT`, por ejemplo `Liga Nacional (Honduras)`. Las filas del CSV reemplazan a las de Wikipedia para esa liga en cada corrida, así que bórralas cuando la liga ya salga de Wikipedia.
