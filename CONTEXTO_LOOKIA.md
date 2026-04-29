# CONTEXTO PROYECTO LOOKIA
> Pegar este archivo al inicio de cada sesión con Claude para retomar sin repetir contexto.

---

## ¿Qué es Lookia?
App de recomendación de outfits basada en personalidad, ocasión, mood, actividad y clima.
Desarrollada en Python + Streamlit. La usuaria no es programadora, aprendió con IA.

---

## Estructura de archivos

```
proyecto app/
├── app.py                  # UI principal (4 tabs)
├── models.py               # Clases: Garment, OutfitFeedback, UsedOutfit
├── constants.py            # Listas: categorías, colores, estilos, etc.
├── storage.py              # (legacy) Guardar/cargar JSON local — ya no se usa en producción
├── storage_cloud.py        # Operaciones CRUD contra Supabase (prendas, feedback, outfits, imágenes)
├── supabase_client.py      # Cliente Supabase + get_supabase_for_user(access_token)
├── auth_ui.py              # Pantalla de login/registro con Supabase Auth
├── weather.py              # Conexión OpenWeather (actual + pronóstico semanal)
├── migrate_local_data.py   # Script one-shot: sube JSON locales a Supabase (no va a producción)
├── requirements.txt        # streamlit, pillow, pandas, requests, python-dotenv, supabase
├── closet.json             # (legacy) Clóset local — ya migrado a Supabase
├── feedback.json           # (legacy) Feedback local — ya migrado a Supabase
├── used_outfits.json       # (legacy) Outfits usados locales — ya migrados a Supabase
├── .env                    # Variables de entorno (NO subir a GitHub)
├── .gitignore              # Incluye .env, __pycache__, wardrobe_images/
├── engine/
│   ├── recommender.py      # Motor principal + explain_outfit_score
│   ├── outfit_generation.py # generate_outfits + generate_outfits_from_selected_garment + generate_week_plan
│   ├── occasion_rules.py   # Reglas por ocasión + get_weather_tag
│   ├── category_rules.py   # Bonus/penalty por categoría de prenda
│   ├── scoring_components.py # dress_score, weather_score, mood_bonus, etc.
│   ├── compatibility.py    # Compatibilidad de colores, estilos y patrones
│   ├── history_utils.py    # Penalización por repetición de prendas
│   ├── user_profile.py     # Perfil automático desde feedback
│   └── selection_utils.py  # Helpers de selección
└── utils/
    ├── garment_utils.py    # Detectores de prendas (is_shoe_heel, is_bottom_skirt, etc.)
    └── attribute_inference.py # Inferencia de atributos desde nombre de prenda
```

---

## Variables de entorno (.env)
```
OPENWEATHER_API_KEY=tu_clave_aqui
LOOKIA_CITY=Punta Arenas
SUPABASE_URL=https://pkojtqwatctncuerilub.supabase.co
SUPABASE_KEY=sb_publishable_...          # anon/publishable key
SUPABASE_SERVICE_KEY=eyJ...              # service_role key (solo para scripts locales)
```
En Streamlit Cloud (rama version-sana) agregar también en Secrets:
```
LOOKIA_ENV = "production"
```

---

## Tabs de la app
1. **🌤️ Hoy** — Recomendador principal con clima real, ajustes manuales y prenda forzada
2. **👕 Mi clóset** — Galería de prendas con edición y análisis de inconsistencias
3. **➕ Agregar prenda** — Subida múltiple (hasta 5 fotos) + formulario individual
4. **📅 Planificador semanal** — Outfits para la semana evitando repetir prendas

---

## Orden de prioridad del motor
1. Ocasión
2. Clima
3. Mood
4. Actividad
5. Ajustes manuales

## Filosofía del motor
- El motor sugiere y advierte, pero la usuaria decide (botón "Mostrar de todos modos")
- Las recomendaciones son tan buenas como el clóset que las alimenta
- Flexibilidad sobre rigidez — nunca bloquear sin dar opción de forzar
- El motor no impone criterios estéticos — si la usuaria tiene una prenda, es porque la usa
- El feedback entrena el motor para personalizar según el estilo real de la usuaria
- Cada cambio en su lugar — las reglas van en el archivo que corresponde según arquitectura

---

## Estado del repositorio
- Rama activa de desarrollo: **main** (local, debug visible)
- Rama testers: **version-sana** (Streamlit Cloud, `LOOKIA_ENV=production`, debug oculto)
- Ambas ramas deben estar siempre sincronizadas (idénticas en código)
- Flujo correcto: desarrollar en main → push → mergear a version-sana → push
- Comando para correr la app: `python -m streamlit run app.py`
- Retomar Claude Code: `claude --resume [session_id]` o simplemente `claude` en la carpeta
- **SIEMPRE verificar que .env no esté en el commit antes de hacer push**

## Infraestructura Supabase
- **Proyecto:** `pkojtqwatctncuerilub` (Supabase)
- **Auth:** Supabase Auth (email/password). `auth_ui.py` maneja login/registro/logout.
- **Base de datos:** PostgreSQL en Supabase. Tablas: `garments`, `outfit_feedback`, `used_outfits`. Todas con RLS habilitado por `user_id`.
- **Storage:** Bucket `garment-images`. Ruta: `{user_id}/{image_name}`. Imágenes públicas, subida autenticada con `access_token`.
- **Cliente:** `supabase_client.py` — `get_supabase()` para operaciones de DB, `get_supabase_for_user(access_token)` para uploads de Storage.
- **Migración datos locales:** `migrate_local_data.py` — ejecutar una sola vez con `python migrate_local_data.py USER_ID`. Usa `SUPABASE_SERVICE_KEY` para bypassear RLS.
- **Tabla `ignored_badges`:** `(id, user_id, garment_id, created_at)` con RLS. Persistencia real de badges ignorados en galería.

---

## Notas técnicas importantes
- La app ya usa Supabase — JSON locales son legacy, no se leen en producción
- `wardrobe_images/` y `__pycache__/` no van al repositorio (están en `.gitignore`)
- Claude Code tiende a incluir .env en commits — siempre verificar antes del push
- `supabase-py 2.3.5` instalado localmente (versiones más nuevas fallan en Python 3.14 por dependencia `pyiceberg`)
- En Streamlit Cloud se instala la versión de `requirements.txt` — verificar compatibilidad si se cambia la versión

## ⚠️ Pendiente urgente
- **Moderación de fotos en subida:** actualmente no hay filtro de contenido en las imágenes subidas por usuarios. Implementar moderación para bloquear nudes, menores, contenido inapropiado antes de guardar en Supabase Storage. Opciones: API de moderación (AWS Rekognition, Google Vision, Anthropic), o revisión manual inicial.

---

## Historial de cambios por sesión

### Sesión 1 — abril 2026
**Seguridad**
- ✅ API key movida de `app.py` a `.env`
- ✅ `.gitignore` creado con `.env`
- ✅ Ciudad hardcodeada movida a `.env` como `LOOKIA_CITY`

**Motor**
- ✅ Ajustes manuales de clima activados
- ✅ Interior + frío: fuerza al menos 1 outfit sin outerwear
- ✅ 24-25°C: mantiene opción de midlayer liviana
- ✅ `generate_outfits_from_selected_garment` reescrita para igualar lógica de `generate_outfits`
- ✅ Filtro `is_too_similar` relajado
- ✅ Gorro/beanie bloqueado en gala y matrimonio

**UI**
- ✅ Score eliminado de la UI (reemplazado por modo debug con toggle)
- ✅ Explicaciones con más variedad de lenguaje
- ✅ Tip de pantys con falda + frío/lluvia

---

### Sesión 2 — abril 2026
**Motor**
- ✅ Tacos penalizados con lluvia (+35) y mood cómodo (+50) en `practicality_penalty`
- ✅ `practicality_penalty` recibe `mood` como parámetro
- ✅ Vestido elegante bloqueado en trabajo + mood cómodo
- ✅ Pantalón buzo bloqueado en cita (salvo mood urbano)
- ✅ Zapatillas deporte bloqueadas en cita (salvo mood urbano)
- ✅ Mini/short bloqueados con temp <= 9°
- ✅ `garment_allowed_for_occasion` recibe `mood` y `temp`
- ✅ `occasion_rules.py` reordenado por ocasión

**UI**
- ✅ Tip de pantys extendido a short con frío/lluvia

---

### Sesiones 3–13 — abril 2026
*(ver historial completo en versiones anteriores del archivo)*

---

### Sesión 14 — abril 2026

**Inferencia de atributos**
- ✅ `infer_attributes_from_subcategory` — nueva función en `utils/attribute_inference.py` que aplica reglas deterministas por subcategoría para warmth, dress_level, sexiness y style
- ✅ Inferencia cruzada integrada en `infer_attributes_from_name` — complementa atributos None con reglas por subcategoría
- ✅ Keywords de jockey/gorra/cap/visera agregados a inferencia de categoría accessory y subcategoría gorro
- ✅ dress_level "relajado" agregado para subcategoría gorro en inferencia cruzada
- ✅ Re-inferencia de categoría y subcategoría al escribir nombre en formulario (`on_change=_reinfer_category_from_name`)
- ✅ dress_level, sexiness y waterproof ahora se aplican desde inferred en formulario individual
- ✅ sexiness se lee de inferred en bulk upload (antes hardcodeado a 0)
- ✅ warmth visible para one_piece en formulario de edición
- ✅ `infer_from_filename` eliminada (era código muerto)
- ✅ `wardrobe_images/` agregado a .gitignore y removido del tracking

**UI**
- ✅ "sport" → "Deporte" en toda la UI visible (STYLE_LABELS_ES en constants.py, format_func en selectboxes, mensajes de advertencia)

---

### Sesión 15 — abril 2026

**Motor — ocasión matrimonio (mejora mayor)**

Contexto: para matrimonio "relajado" el motor mostraba poleras y mocasines como primera opción. Se rediseñó la lógica para que los vestidos elegantes/cóctel dominen siempre los primeros 2 slots, con top+bottom arreglado como tercera opción.

**`engine/occasion_rules.py`**
- ✅ Hard block botines y botas para matrimonio/gala (a nivel de prenda individual)
- ✅ Hard block mocasines para matrimonio/gala

**`engine/scoring_components.py`**
- ✅ Penalty 999 para botas con vestido elegante/cóctel (irrompible)
- ✅ Boost -160 para vestidos elegante/cóctel en matrimonio
- ✅ Boost -60 para vestido casual en matrimonio

**`engine/outfit_generation.py`** (aplicado en `generate_outfits` y `generate_outfits_from_selected_garment`)
- ✅ one_piece candidatos ordenados por elegancia: vestido_elegante/cóctel primero, casual después
- ✅ Tops filtrados a `style: elegante/formal` + `dress_level: arreglado/elegante` cuando hay vestidos disponibles
- ✅ Bottoms filtrados a `style: elegante/formal` + `dress_level: arreglado/elegante`, excluyendo buzo/jogger/legging/short_casual/jeans
- ✅ Shoes filtrados: excluye mocasín, botín, bota, zapatilla_urbana, zapatilla_deporte
- ✅ `is_too_similar` relajado para one_piece en matrimonio/gala (permite 2 vestidos distintos)
- ✅ Reordenamiento `final_outfits`: vestidos al frente, 2 slots reservados para vestidos si hay ≥2 disponibles
- ✅ Loop de diversidad forzado: primeros 2 slots reservados para vestidos cuando hay ≥2 disponibles

**Supabase — datos**
- ✅ `aros` y `collar corazon dorado` actualizados: `dress_level: arreglado`, `style: elegante`

---

### Sesión 16 — abril 2026

**Motor — matrimonio mood urbano**

- ✅ Excepciones de calzado para matrimonio mood urbano en occasion_rules.py: botines y botas permitidos si dress_level in ["flexible", "arreglado", "elegante"]; mocasines permitidos sin restricción de dress_level; zapatilla_urbana permitida si dress_level in ["arreglado", "elegante"]
- ✅ Filtros de candidatos en outfit_generation.py (generate_outfits y generate_outfits_from_selected_garment): tops y bottoms aceptan estilo urbano además de elegante/formal en matrimonio mood urbano
- ✅ Filtros de candidatos: shoes en matrimonio mood urbano excluye solo zapatilla_deporte y zapatilla_urbana sin dress_level alto; permite zapatilla_urbana con dress_level arreglado/elegante
- ✅ Reordenamiento final desactivado para matrimonio mood urbano — outfits ordenados por score natural sin forzar vestidos al frente
- ✅ scoring_components.py: taco_alto penalizado +50 en matrimonio mood urbano; botin/zapato/mocasin bonificados -40; zapatilla_urbana arreglada/elegante bonificada -40
- ✅ Filtros de tops en matrimonio mood urbano exigen dress_level in ["arreglado", "elegante"] — tops flexible excluidos aunque tengan estilo urbano
- ✅ Loop inline de tops también actualizado con dress_level

**Prendas agregadas al clóset para pruebas**
- Camisa formal oscura (navy/negro) con secondary_styles urbano
- Pantalón vestir negro con secondary_styles urbano y elegante
- Zapato derby negro con secondary_styles urbano y elegante
- Zapatilla elegante crema con dress_level arreglado y style urbano
- Pantalón crema urbano con secondary_styles elegante y urbano

---

### Sesión 17 — abril 2026

**Motor — matrimonio mood urbano (continuación)**

- ✅ Pool de candidatos one_piece para matrimonio mood urbano ampliado: incluye prendas con style == "urbano" o "urbano" in secondary_styles, independiente de su subcategoría — en generate_outfits y generate_outfits_from_selected_garment
- ✅ Vestido urbano elegante agregado al clóset como one_piece vestido_casual, style urbano, secondary_styles [casual, elegante, formal], dress_level arreglado, warmth caluroso

**Pruebas completadas matrimonio + normal**

- ✅ URBANO 8°C sin lluvia — OK
- ✅ URBANO 8°C con lluvia — OK
- ✅ URBANO 33°C calor — OK

---

### Sesión 18 — abril 2026

**Motor — matrimonio mood urbano 24-25°C (fix midlayer)**

Problema: a 24-25°C el bloque `if temp >= 24` filtraba midlayer a `warmth == "caluroso"` únicamente, y todos los blazers del clóset tienen `warmth: medio`. Además, el branch `outerwear_required` consume el flujo con un `continue` sin iterar midlayer cuando el pool de outerwear está vacío (como ocurre a esa temperatura).

**`engine/outfit_generation.py`** (aplicado en `generate_outfits` y `generate_outfits_from_selected_garment`)
- ✅ Bloque `if temp >= 24`: para `matrimonio+urbano` filtra midlayer a `subcategory == "blazer"` con `[:1]`; resto de ocasiones mantiene `warmth == "caluroso"` con `[:2]`
- ✅ Dentro del branch `if outerwear_required:`, antes del `continue`: agrega iteración de midlayer (blazer) sin outerwear cuando `occasion == "matrimonio" and mood == "urbano" and temp >= 24` — necesario porque outerwear está en `optional` (no `required`) pero el pool queda vacío a esa temperatura, y el `continue` cortaba el flujo antes de llegar al bloque normal de midlayer

**`engine/scoring_components.py`**
- ✅ En `practicality_penalty`: blazer como midlayer en `matrimonio` a 24°+ recibe penalty 999 si hay `one_piece` con `warmth != "caluroso"` — bloquea vestido+blazer salvo que el vestido sea ligero

**Prendas agregadas al clóset**
- ✅ `blazer manga corta morado urbano` — subcategory: blazer, warmth: caluroso, style: urbano, dress_level: arreglado, secondary_styles: [elegante, formal]

**Pruebas completadas**
- ✅ URBANO 24-25°C — blazer aparece en outfit 1 con top+bottom, bloqueado con one_piece de warmth medio

**Deuda técnica registrada**
- ⬜ `generate_outfits_from_selected_garment` — equiparar TODAS las reglas de `generate_outfits` en una pasada dedicada (incluye fix matrimonio+urbano+calor y cualquier otra divergencia acumulada)

---

### Sesión 19 — abril 2026

**UI — tab3 Agregar prenda**
- ✅ Sección "Agregar fotos" renombrada a "Subida rápida" con caption descriptivo
- ✅ Sección "Agregar prenda manualmente" renombrada a "Agregar con formulario" con caption
- ✅ Orden del formulario: foto → nombre → caption inferencia → categoría → resto de campos
- ✅ Campo "Nombre de la prenda" destacado con fondo rosado (#fff0f3) y caption de inferencia arriba del input
- ✅ Mensaje de confirmación "Tu prenda quedó guardada" movido al final del formulario (via session_state + st.success post-rerun)
- ✅ Validación: impedir guardar prenda sin foto ni nombre, mostrar warning inline
- ✅ Inferencia de estilo principal desde nombre (infer_style_from_name en attribute_inference.py)

**UI — tab2 Mi clóset**
- ✅ Botón eliminar con confirmación via st.popover en formulario de editar prenda
- ✅ Botón eliminar directo en tarjeta de galería — descartado, pendiente migración a React
- ✅ Sección de estadísticas agregada al final del tab: título con fondo rosado, métricas (prendas, outfits registrados, estilo dominante), prendas más usadas y ocasiones más frecuentes

**Motor — matrimonio elegante**
- ✅ Fix diversidad de vestidos: matrimonio_forced ahora fuerza vestidos distintos en slots 1 y 2
- ✅ Fix vestidos elegantes/cóctel con calor: exentos de penalización warmth en matrimonio a temp >= 26 si warmth != "frio"
- ✅ Penalización zapato derby en matrimonio mood no urbano (+80)
- ✅ midlayer (blazer) agregado a optional de matrimonio en occasion_rules.py
- ✅ Filtro de midlayer en matrimonio: solo blazers elegantes/formales con dress_level arreglado/elegante, pool [:3]
- ✅ Fix blazer a 24°+: excepción para blazer caluroso aunque vestido sea warmth medio
- ✅ Fix flujo midlayer con one_piece en matrimonio elegante a todas las temperaturas
- ✅ max_same_midlayer = 1 cuando 24 <= temp <= 25, top_n en el resto — con tracking en matrimonio_forced
- ✅ midlayer vaciado cuando temp > 25 en matrimonio elegante

**Pruebas matrimonio elegante completadas**
- ✅ 5° sin lluvia — OK
- ✅ 5° con lluvia — OK (tip paraguas correcto)
- ✅ 31° calor — OK (vestidos dominan, fix warmth funcionando)
- ✅ 24-25° — OK (1 blazer caluroso aparece en 1 slot)
- ⬜ 16° — PENDIENTE: blazer negro y blazer gris tienen dress_level: flexible, no pasan filtro → corregir a arreglado en Supabase, luego verificar que los 3 outfits tengan blazer

### Sesión 20 — abril 2026

**Motor — matrimonio mood elegante**

- ✅ Blazers elegantes/formales filtrados en pool de midlayer para todos los rangos de temperatura (16°, 13°, <13°)
- ✅ max_same_shoes = 1 para matrimonio elegante
- ✅ max_same_midlayer = 1 cuando hay más de 1 blazer disponible en matrimonio elegante
- ✅ Boost -350 a vestidos elegantes/cóctel en matrimonio mood elegante (scoring_components.py)
- ✅ matrimonio_forced desactivado para mood elegante — vestidos dominan por scoring
- ✅ _max_forced_vestidos = 2 solo para moods que no sean urbano ni elegante
- ✅ Rotación de blazers y tacos funcionando a 16°C

**Pendiente matrimonio elegante (retomar desde cero próxima sesión)**
- ⬜ 3 vestidos en los 3 slots — el forzado rompe la rotación, el boost solo no es suficiente en todos los escenarios. Buscar enfoque distinto.
- ⬜ 1 abrigo elegante rotando en umbral 15-18°C — el trench domina scoring y aparece en todos los combos. Requiere penalización específica en scoring_components.py + lógica de pool.
- ⬜ Compatibilidad de colores — penalizar outfits con 4+ colores sin eje cromático claro (ej. vestido azul + tacos rojos + blazer blanco + abrigo café + pañuelo negro)
- ⬜ Continuar matriz de pruebas: 22-23°C, mood sexy, mood cómodo

---

### Sesión 21 — abril 2026

**Motor — matrimonio elegante (refactor completo)**

Problema raíz identificado: el motor genérico no podía garantizar vestidos en todos los slots 
para matrimonio elegante porque blusa+falda con buenos scores individuales superaban el boost 
de vestidos a temperaturas templadas. Después de múltiples intentos de parches, se decidió 
crear una función dedicada y separada.

**`engine/outfit_generation.py`**
- ✅ Nueva función `_generate_matrimonio_elegante` — maneja exclusivamente 
  `occasion == "matrimonio" and mood == "elegante"` con lógica propia y simple
- ✅ Base fija: vestido elegante/cóctel + taco alto/bajo o sandalia elegante. Siempre.
- ✅ Capas según temperatura:
  - `> 25°C` → vestido + tacos, sin capas
  - `24-25°C` → 1 blazer caluroso/medio en slot 0, resto sin blazer
  - `20-23°C` → 2 outfits con blazer, 1 sin blazer (slot 2 omite)
  - `13-19°C` → blazer elegante en todos los slots, sin abrigo
  - `< 13°C` → blazer elegante + abrigo elegante/formal en todos los slots
- ✅ Pool de abrigos filtrado: solo subcategory abrigo/trench con style no sport/urbano/casual
- ✅ Sin impermeable casual en matrimonio elegante (lluvia → mismo abrigo elegante + tip paraguas)
- ✅ Rotación por índice `i % len(pool)` — vestido distinto, taco distinto, blazer distinto por slot
- ✅ `random.shuffle(vestidos)` para variar orden entre tandas
- ✅ Llama a `outfit_score` real para scoring final
- ✅ Integrada en `generate_outfits` y `generate_outfits_from_selected_garment`
- ✅ `selected_garment` compatible (vestido/tacos/blazer/abrigo/accesorio) → úsarlo como base
- ✅ `selected_garment` incompatible (pantalón, etc.) → retorna `[], []` → UI muestra warning
- ✅ Limpieza de toda la lógica matrimonio elegante del motor genérico (bloques continue 
  en fallbacks, bloque vestido+blazer 13-23°C, ramas de temperatura específicas, 
  matrimonio_forced restaurado a `mood not in ["urbano", "elegante"]`)
- ✅ Sin vestidos elegantes en clóset → fallback automático al motor genérico en lugar de 
  retornar vacío (filosofía: nunca dejar a la usuaria sin opciones)
- ✅ Sin calzado elegante → retorna [], [] con mensaje de categoría faltante

**`engine/scoring_components.py`**
- ✅ Boost vestidos elegantes/cóctel en matrimonio restaurado a -160 (era -350 para elegante)
- ✅ Penalización zapato derby en matrimonio no urbano subida a 999 (hard block)

**`app.py`**
- ✅ Verificación de compatibilidad para matrimonio elegante con selected_garment:
  si la prenda no es vestido/tacos/blazer/abrigo/accesorio → warning "no es la elección 
  típica" + activa botón "Mostrar de todos modos"
- ✅ Al presionar "Mostrar de todos modos" con prenda incompatible → bypasea 
  `_generate_matrimonio_elegante` y usa motor genérico completo

**Matriz de pruebas completada y aprobada**
- ✅ 5°C sin lluvia
- ✅ 8°C sin lluvia  
- ✅ 10°C sin lluvia
- ✅ 9°C con lluvia
- ✅ 12°C sin lluvia
- ✅ 14°C sin lluvia
- ✅ 16°C sin lluvia
- ✅ 14°C con lluvia
- ✅ 17°C sin lluvia
- ✅ 18°C sin lluvia
- ✅ 20°C sin lluvia
- ✅ 22°C sin lluvia
- ✅ 23°C sin lluvia
- ✅ 24°C sin lluvia
- ✅ 25°C sin lluvia
- ✅ 28°C sin lluvia
- ✅ 31°C sin lluvia

---

### Sesión 22 — abril 2026

**UI — app.py**
- ✅ Emoji 💪 agregado al botón "Mostrar de todos modos"
- ✅ Emoji 📅 y `type="primary"` agregado al botón "Generar semana"
- ✅ Label `"Nombre de la prenda"` en `st.text_input` que tenía string vacío (eliminaba warning de accesibilidad)

**Motor — diagnóstico y refactor engine/outfit_generation.py**

Diagnóstico completo realizado sobre `generate_outfits` y `generate_outfits_from_selected_garment`: código muerto por dispatch matrimonio+elegante, ramas elif duplicadas, edge case lluvia+calor sin manejar, `is_too_similar` divergente entre funciones, y varias inconsistencias de mood.

- ✅ `mood in ["urbano", "elegante"]` reemplazado por `mood in ["urbano", "sexy"]` en 5 ocurrencias (L341, L650, L669, L1170, L1376) — matrimonio+sexy ahora tiene acceso a midlayer con lógica equivalente a urbano
- ✅ Rama `elif temp >= 22 and not rain` duplicada eliminada en ambas funciones — rango 16–23°C sin lluvia unificado en una sola rama
- ✅ Rama `elif rain and temp >= 16` agregada antes del `else` final en ambas funciones — corrige edge case donde lluvia con calor caía al pool de frío extremo (midlayer[:1] no frío + outerwear[:2])
- ✅ `is_too_similar` en `generate_outfits_from_selected_garment` sincronizada con versión de `generate_outfits`: agregadas regla fuerte `same_bottom_type + same_shoes_type`, regla suave `same_top + same_shoes`, y declaración de `same_one_piece`
- ✅ En **ambas** versiones de `is_too_similar`: agregadas reglas `same_top and same_one_piece` y `same_one_piece and same_shoes` (antes `same_one_piece` estaba declarado pero nunca usado)
- ✅ Rama muerta `mood == "elegante"` eliminada de `max_same_midlayer` — colapsado a expresión simple
- ✅ `mood not in ["urbano", "elegante"]` corregido a `mood != "urbano"` (L864)

**Pendientes anotados (no tocar aún)**
- ⚠️ Sort+shuffle inconsistente en `_generate_matrimonio_elegante` (sort de vestidos destruido por shuffle inmediato)
- ⚠️ Riesgo de recursión infinita si no hay vestidos en `_generate_matrimonio_elegante` (fallback llama a `generate_outfits` con mood="elegante" que volvería a llamar a `_generate_matrimonio_elegante`)
- ⚠️ Cardigan/midlayer repetido en múltiples outfits — problema de rotación

**Próxima sesión**
- Rondas de pruebas: matrimonio+sexy, matrimonio+cómodo, gala y deporte (todos los moods, todas las temperaturas)
- Post-pruebas: merge main → version-sana
- Post-merge: refactor `generate_outfits_from_selected_garment` (lógica duplicada con `generate_outfits`)

---

### Sesión 23 — abril 2026

**Motor — matrimonio mood cómodo (implementación completa)**

Contexto: el motor no tenía lógica propia para matrimonio+cómodo. Las prendas caían en el `else` genérico de elegante/sexy/relajado, el scoring con `mood_bonus` penalizaba prendas formales/elegantes, y no había filtros específicos de calzado ni one_piece para este mood.

**`engine/outfit_generation.py`** (aplicado en `generate_outfits` y `generate_outfits_from_selected_garment`)
- ✅ Bloque `elif mood == "comodo":` propio para one_piece en matrimonio: lista blanca `["vestido_casual", "enterito"]` — excluye vestido_elegante y vestido_coctel del pool
- ✅ Bloque `elif mood == "comodo":` propio para top/bottom en matrimonio: solo elegante/formal (sin urbano), dress_level arreglado/elegante/flexible
- ✅ Bloque `elif mood == "comodo":` propio para shoes en matrimonio: bloquea taco_alto y zapatilla_deporte; pool tomado del ranking completo `ranked["shoes"]` (no del slice); un representante por subcategoría via `_seen_subs`; `random.shuffle` para variar entre tandas
- ✅ `max_same_shoes = 1` para matrimonio+cómodo (forzar variedad de calzado por outfit)
- ✅ Bloques inline de tops y bottoms en loops: condición ampliada a `mood in ["urbano", "comodo"]` para el `else` permisivo; ambos moods aceptan dress_level flexible en el `else`
- ✅ Forzado de vestidos desactivado para cómodo: `mood not in ["urbano", "comodo"]` en bloques de reordenamiento final y matrimonio_forced

**`engine/occasion_rules.py`**
- ✅ Zapatilla_urbana arreglada/elegante permitida para `mood in ["urbano", "comodo"]`
- ✅ Botín y bota permitidos para `mood in ["urbano", "comodo"]` con cualquier dress_level (relajado a elegante)
- ✅ Mocasín permitido para `mood in ["urbano", "comodo"]`
- ✅ Excepción en `blocked_by_occasion`: dress_level "relajado" no bloquea shoes botin/bota/zapato/mocasin cuando `occasion == "matrimonio" and mood == "comodo"`

**`engine/scoring_components.py`**
- ✅ `mood_bonus` recibe `occasion: str = ""` como parámetro
- ✅ Branch `if mood == "comodo" and occasion == "matrimonio":` en mood_bonus: strong = ["formal", "elegante"], soft = dress_level arreglado/flexible
- ✅ `practicality_penalty`: bloque matrimonio+comodo penaliza taco_alto (+80) y vestido_elegante/vestido_coctel (+70)
- ✅ Hard block zapato derby (`penalty += 999`) ampliado a `mood not in ["urbano", "comodo"]` — zapato derby permitido en matrimonio+cómodo

**`engine/recommender.py`**
- ✅ Las 5 llamadas a `mood_bonus` actualizadas a `mood_bonus(g, mood, occasion=occasion)`

**Estado WIP**
- ⚠️ PENDIENTE: resultados aún pueden mostrar demasiado zapato derby y zapatilla elegante en algunos clósets — ajuste fino de scores pendiente
- ⚠️ PENDIENTE FUTURO: agregar ballerinas como subcategoría de shoes (calzado cómodo por excelencia para matrimonio)

---

### Sesión 24 — abril 2026

**Motor — matrimonio mood cómodo (fixes y validación completa)**

- ✅ occasion_rules.py: matrimonio ya no está exento de outerwear obligatorio con lluvia (solo gala queda exento)
- ✅ outfit_generation.py: filtro de impermeables para matrimonio+lluvia — excluye style sport y dress_level relajado
- ✅ outfit_generation.py: midlayer permitido en loop one_piece para matrimonio+cómodo (agregado "comodo" a la excepción)
- ✅ outfit_generation.py: bloque else de temperatura no corta midlayer pool cuando occasion == "matrimonio"
- ✅ outfit_generation.py: _force_mid_outer generalizado a todos los moods de matrimonio a temp ≤ 12° (antes solo cómodo)
- ✅ outfit_generation.py: _force_mid_outer aplicado también en bloques outer+acc y mid+acc para evitar escapes
- ✅ scoring_components.py: impermeables no penalizados en matrimonio cuando llueve
- ✅ category_rules.py: boost +35 a blazer en matrimonio+cómodo con temp ≤ 15°
- ✅ _generate_matrimonio_elegante: filtra outfits con score <= -999 antes de retornar
- ✅ max_same_midlayer = 1 para matrimonio+cómodo cuando hay 2+ blazers disponibles

**Diagnóstico completo ejecutado post-fixes**
- ✅ Blazer consistente en todos los moods a temp ≤ 15° (relajado sin forzado — esperado)
- ✅ Blazer+abrigo en todos los moods a temp ≤ 12°
- ✅ Outerwear consistente en todos a temp ≤ 10°
- ✅ Variedad de calzado y outerwear en los 3 slots
- ✅ Impermeable elegante con lluvia (no sport/relajado)
- ✅ Cómodo 3°/7° produce 2 outfits con armario sintético — esperado, en producción hay más prendas

**Pendiente**
- ⬜ Pruebas reales en app con clóset de Punta Arenas — matrimonio+cómodo varias temperaturas
- ⬜ Gala — sin validar en ningún mood
- ⬜ Merge main → version-sana cuando matrimonio esté confirmado estable

---

### Sesión 25 — abril 2026 — Fixes matrimonio + preparación gala

**Fixes aplicados y mergeados a main:**
- Fix B1: shuffle antes de sort en `_generate_matrimonio_elegante` para variar vestidos entre tandas
- Fix B2: fallback cuando `result` queda vacío (no solo cuando no hay vestidos) → usa `mood="sexy"` como fallback
- Fix C1: `max_same_midlayer` escalonado para matrimonio (1 con 3+ blazers, 2 con 2 blazers, top_n con 1)
- Fix C2: pool de midlayer ampliado a `[:4]` para matrimonio a 16°+ (antes `[:1]` bloqueaba variedad)
- Fix C3: `max_same_one_piece=1` para evitar repetir vestidos entre outfits
- Fix C4: threshold permisivo 0.20 para matrimonio (vs 0.35 general)
- Fix C5: hard block zapato derby y mocasín en matrimonio+sexy (`occasion_rules.py` y `scoring_components.py`)
- Fix C6: corregir doble conteo de shoes/midlayer/outerwear_usage en bloque matrimonio_forced
- Fix C7: relajar `_outerwear_limit` en tercera pasada para matrimonio
- Fix C8: `_outerwear_limit` relajado permite enterito aparecer con tacos en sexy+5°

**Estado matrimonio:** todos los moods generan 3 outfits en temperaturas normales. Limitación aceptada: urbano+5° repite vestido casual (solo hay uno en el clóset para ese mood/temp).

**Próxima ocasión: GALA**

Diseño acordado:
- Moods permitidos: elegante, sexy, cómodo (con restricciones), urbano (excepción especial)
- Moods bloqueados: relajado
- Solo one_piece: vestido_elegante y vestido_coctel (sin enterito, sin vestido_casual)
- Excepción urbano: permite vestido_coctel + zapatilla_urbana con dress_level arreglado/elegante + blazer elegante obligatorio. Sin top+bottom.
- Calzado: solo tacos y sandalias elegantes (sin derby, sin mocasín, sin zapatilla_deporte)
- Abrigo: solo elegante (abrigo de gala, trench) — sin parka, sin impermeable
- Sin fallback a top+bottom — si no hay vestido elegante/cóctel, mostrar mensaje directo

---

### Sesión actual (abril 2026) — Gala implementada y validada

**`engine/outfit_generation.py`**
- ✅ `_generate_gala` — función dedicada para `occasion == "gala"`, análoga a `_generate_matrimonio_elegante`
- ✅ Pools: `vestido_elegante` / `vestido_coctel` obligatorio. Sin top+bottom, sin enterito, sin midlayer
- ✅ Calzado por mood: elegante/sexy → taco_alto, taco_bajo, sandalia; cómodo → taco_bajo, sandalia; urbano → tacos + zapatilla_urbana arreglada/elegante
- ✅ Outerwear por mood: elegante/sexy/cómodo → `abrigo/chaqueta/bolero` con estilo elegante o formal, sin impermeable; urbano → además permite `trench` sin restricción de estilo
- ✅ Sandalia pre-filtrada del pool cuando `temp <= 10` (evita que consuma un slot con score -999)
- ✅ Loop `for i in range(top_n)` — siempre intenta 3 outfits ciclando vestidos disponibles (fix: antes usaba `range(min(top_n, len(vestidos)))`)
- ✅ `abrigos_todos` reinsertado después del sort cuando hay `selected_garment` outerwear — garantiza que aparezca en primer slot (bug pendiente: solo outfit 1, no los 3; ver pendientes)
- ✅ `selected_garment` trench rechazado si `mood != "urbano"` → retorna `[], []`
- ✅ mood `relajado` bloqueado al inicio de la función
- ✅ Dispatched desde `generate_outfits` cuando `occasion == "gala"`
- ✅ Boost vestido_coctel primero en `sexy` y `urbano` mediante sort estable

**`engine/occasion_rules.py`**
- ✅ Excepción `zapatilla_urbana` extendida de `occasion == "matrimonio"` a `occasion in ["matrimonio", "gala"]`
- ✅ Bloque `zapato` (subcategory) agregado: bloqueado en matrimonio/gala salvo `mood in ["urbano", "comodo"]`

**`engine/scoring_components.py`**
- ✅ Boost gala para vestido_elegante/coctel (`penalty -= 180`)
- ✅ Boost `sexy` extendido a gala, salida nocturna y cita

**`app.py`**
- ✅ Bloque compatibilidad `selected_garment` para gala: acepta vestido/calzado/abrigo+chaqueta+bolero/accesorio; trench solo en urbano
- ✅ Warning específico para trench forzado en mood no-urbano: `"no va con gala {mood}"`
- ✅ Warning gala sin vestidos distingue mood relajado vs. sin prenda elegante en clóset
- ✅ "Mostrar de todos modos" visible en gala incluso sin `selected_garment`

**`constants.py`**
- ✅ `bolero` agregado a `SUBCATEGORY_OPTIONS["outerwear"]` y `SUBCATEGORY_LABELS_ES`
- ✅ Aliases de color femeninos: blanca, negra, roja, rosada, morada, amarilla

**`utils/attribute_inference.py`**
- ✅ `"bolero": ["bolero"]` agregado a `subcategory_keywords["outerwear"]`

**Matriz de validación gala completada (37 casos)**
- ✅ Casos 1–9: relajado bloqueado, elegante/sexy/cómodo/urbano a distintas temperaturas y lluvia
- ✅ Casos 10–28: temperaturas extremas, lluvia, calzado específico, outerwear bolero/chaqueta, accesorios, prenda forzada
- ✅ Casos 29–37: trench excluido en elegante/sexy/cómodo, permitido en urbano; prenda forzada trench; bolero; clima extremo
- ✅ False positive #21 identificado: chaqueta de cuero (style=casual) detectada por check sin filtro de estilo → no hay fix de producción

**⚠️ Bug pendiente — prenda forzada outerwear en gala**
Cuando `selected_garment` es un outerwear (abrigo, chaqueta, bolero), la lógica actual lo reinserta al frente del pool después del sort, pero el loop `abrigos[i % len(abrigos)]` cicla por todo el pool. Resultado: solo aparece en outfit 1. Fix requerido: cuando hay `selected_garment` outerwear, restringir `abrigos = [selected_garment]` o forzar en cada iteración del loop.

---

### Sesión 26 — abril 2026 — mood formal + fixes outerwear trabajo + mejoras inferencia

**`constants.py`**
- ✅ `"formal"` agregado a `MOOD_OPTIONS`; `"formal"` eliminado de `ACTIVITY_OPTIONS` → ahora `["normal", "caminar", "entrenar"]`
- ✅ `"lunares"` agregado a `PATTERN_OPTIONS`

**`engine/scoring_components.py`**
- ✅ `mood_map["formal"]` agregado en `mood_bonus()`: strong → elegante/formal, soft → urbano
- ✅ Jeans penalty extendido a `mood in ["elegante", "sexy", "formal"]`
- ✅ Falda boost extendido a `mood in ["elegante", "sexy", "formal"]`
- ✅ Taco boost `-40` para `mood == "formal"` en `practicality_penalty()`
- ✅ `activity_bonus()`: bloque `activity == "formal"` eliminado de `activity_bonus()`

**`engine/occasion_rules.py`**
- ✅ Firma extendida con `activity: str = ""`
- ✅ Regla global: `mood == "formal"` bloquea prendas con estilo sport (excepto shoes/accessory)
- ✅ Regla global: `activity == "caminar"` bloquea sandalia
- ✅ `work+comodo`: `one_piece` con `dress_level in ["elegante", "arreglado"]` bloqueado

**`engine/category_rules.py`**
- ✅ `shoe_context_penalty()`: condición +14 extendida a `mood in ["elegante", "formal"]` para tacos en trabajo

**`engine/outfit_generation.py`**
- ✅ Filtro formal shoes: bloquea converse y zapatilla_deporte; bloquea zapatilla_urbana sin estilo elegante/formal salvo `occasion in ["casual", "deporte"]`
- ✅ `max_same_shoes_heel`: escape condition (opción B) para formal — limita a 1 heel outfit solo si hay ≥2 non-heel
- ✅ `max_same_outerwear`: escape condition para no-rain — limita a 1 solo si hay ≥2 outerwear candidatas
- ✅ Filtro outerwear 13–15°: `_allow_cold` extendido a `mood in ["elegante", "formal", "comodo"]`; filtro trabajo abrigos elegantes sin secondary "formal" aplicado antes del `[:4]`
- ✅ Filtro outerwear frío extremo (else): mismo filtro de trabajo abrigos elegantes sin secondary "formal"
- ✅ Pool inicial outerwear ampliado a `[:8]` antes del filtro de temperatura

**`engine/recommender.py`**
- ✅ `explain_outfit_score()`: eliminado texto "Funciona bien para la actividad 'normal'" del random.choice

**`app.py`**
- ✅ Actividades disponibles condicionales: `caminar` solo en moods relajado/urbano/cómodo o casual/deporte; `entrenar` solo en deporte — aplicado en recomendador principal y planificador
- ✅ `_reinfer_from_edit_name()`: re-inferencia completa al editar nombre (categoría, subcategoría, color, patrón, warmth, dress_level, sexiness) con on_change
- ✅ Widgets del formulario de edición leen desde `st.session_state` con fallback a `garment.*`

**`utils/attribute_inference.py`**
- ✅ Keywords `"lunares"` agregados: ["lunares", "lunar", "puntos", "polka", "polka dot", "dots"]
- ✅ `"poncho"` confirmado en `subcategory_keywords["outerwear"]`; agregado a `cold_keywords` y `warmth_map["poncho"] = "frio"`

**Bloque 7 completado:**
- ✅ 7.1 matrimonio + elegante — OK
- ✅ 7.2 gala + sexy — OK
- ✅ 7.3 trabajo + cómodo — OK (deuda menor: rotación de bottoms)
- ✅ 7.4 actividad "formal" nunca aparece en UI — OK
- ✅ 7.5 sin errores/crashes — OK

**⚠️ Deuda técnica prioritaria próxima sesión (primera parte)**
- 🎯 Rotación de bottoms — pantalón vestir negro y falda negra larga dominan en moods formales/elegantes, generando 1–2 outfits en lugar de 3

**Fixes adicionales sesión 26 (continuación)**

**`app.py`**
- ✅ `default_wardrobe()` eliminada — era código muerto legacy de antes de Supabase (160 líneas)
- ✅ Nombre de prenda capitalizado al guardar (`.strip().capitalize()`) en formulario agregar y editar
- ✅ `_reinfer_from_edit_name` actualiza también `edit_style_{garment.id}` — gap corregido
- ✅ Selectbox de estilo en edición lee desde `st.session_state` con fallback a `garment.style`

**`utils/attribute_inference.py`**
- ✅ Inferencia cruzada `dress_level` ← estilo — cuando `dress_level` queda `None` o `flexible` con estilo elegante/formal, se sube a `arreglado`
- ✅ Aliases de color ampliados — femeninos (dorada, plateada), chilenismos (naranjo, camel, arena, tostado, nude, palo de rosa, terracota→café, salmón→naranja, coral→rosado, turquesa→celeste, granate→burdeo, etc.)
- ✅ `"poncho"` agregado a `cold_keywords` y `warmth_map`

**`engine/occasion_rules.py`**
- ✅ Bloqueo prendas sport en mood formal implementado

**Supabase**
- ✅ Script `capitalize_garment_names.py` ejecutado — 156 nombres de prendas existentes capitalizados

**Limpieza de código muerto**
- ✅ `from unicodedata import category` eliminado de `recommender.py`
- ✅ `is_shoe_high_heel()` e `is_shoe_low_heel()` eliminadas de `garment_utils.py`
- ✅ Condiciones redundantes simplificadas en `occasion_rules.py` y `category_rules.py`
- ✅ Prints de debug eliminados de `outfit_generation.py` y `recommender.py`

---

## Sesión 27 — abril 2026

### Ocasión deporte — mejoras de calzado
- ✅ `occasion_rules.py`: bloqueo de calzado por actividad en deporte — entrenar solo `zapatilla_deporte`, caminar `zapatilla_deporte` + `zapatilla_urbana`, normal `zapatilla_deporte` + `zapatilla_urbana` básica (sin converse, sin elegante, sin `dress_level` arreglado/elegante)
- ✅ `recommender.py` (`rank_garments`): excepción en filtro sport para zapatilla urbana básica en deporte+normal — permite entrada al ranking sin style sport

### Gala — capa ligera 16–22°
- ✅ `outfit_generation.py` (`_generate_gala`): nuevo pool `capas_ligeras` para rango 16–22° — bolero (`midlayer`) o chaqueta (`outerwear`) con `style elegante` sin secondary casual/sport/urbano; `usar_abrigo` ajustado a `temp ≤ 15°`
- ✅ `constants.py`: `"bolero"` movido de `SUBCATEGORY_OPTIONS["outerwear"]` a `SUBCATEGORY_OPTIONS["midlayer"]`; label agregado en `SUBCATEGORY_LABELS_ES`

**⚠️ Deuda técnica prioritaria próxima sesión**
- 🎯 Rotación de categorías — implementar `bottom_usage` y mecanismo de diversidad forzada genérica para todas las categorías (bottom, midlayer, outerwear). Causa raíz de outfits con 1–2 resultados y prendas que nunca aparecen
- ⬜ Refactor `generate_outfits_from_selected_garment` — ~430 líneas duplicadas con `generate_outfits`. Sesión dedicada con batería de pruebas completa
- ⬜ Extraer `is_too_similar` a función standalone (cambio seguro, pendiente)
- ⬜ Extraer filtro accesorios duplicado en `_generate_matrimonio_elegante` y `_generate_gala` (cambio seguro, pendiente)
- ⬜ Rotación de bottoms — pantalón vestir negro y falda negra larga dominan en moods formales/elegantes
- ⬜ Outerwear faltante a temperaturas bajas con actividad caminar

---

### Sesión 28 — abril 2026

**Versión**
- ✅ `APP_VERSION = "1.0.0"` agregado en `app.py`; `st.caption(f"v{APP_VERSION}")` al final del sidebar

**Fix lluvia + calor (`engine/outfit_generation.py`)**
- ✅ Bug: cuando `rain=True` y `temp >= 24`, el bloque `elif temp >= 24` vaciaba outerwear sin considerar lluvia, dejando al usuario sin abrigo impermeable
- ✅ Fix: nuevo branch `if temp >= 24 and rain:` antes del `if temp >= 24:` — mantiene solo impermeables livianos (waterproof + warmth caluroso/medio), vacía midlayer; aplicado en `generate_outfits` y `generate_outfits_from_selected_garment`
- ✅ Tip en `app.py`: "Con este calor no necesitas abrigo, pero no olvides llevar paraguas" cuando `temp >= 24 and not has_any_outer`
- ✅ Umbral tip de falda/short cambiado de `temp <= 16` a `temp <= 20`

**Fixes accesorios (`engine/category_rules.py`)**
- ✅ `should_include_accessory`: bufanda bloqueada a `temp >= 18`; gorro de invierno bloqueado a `temp >= 18`; jockey bloqueado a `temp >= 22` (antes `>= 20 and not rain`)
- ✅ `accessory_relevance_penalty`: jockey bloqueado a `temp >= 22` (incondicionalmente); gorro invierno bloqueado a `temp >= 18` (incondicionalmente, antes incluía `and not rain`)
- ✅ `outerwear_context_penalty`: bloque `is_formal_coat` agregado — penaliza abrigo elegante/formal en deporte, casual relajado y ocasiones sin formalidad

**Nuevas subcategorías**
- ✅ `jardinera` (bottom): constants, labels, inferencia, attribute_inference, occasion_rules
- ✅ `camisón` (midlayer): constants, labels, inferencia, attribute_inference
- ✅ `ballarina` (shoes): constants, labels, inferencia, `is_shoe_ballet_flat()` en garment_utils, occasion_rules
- ✅ `polera_deporte` (top): constants, labels, inferencia, category_rules (bonus +12 en deporte, penalty +20 fuera de deporte/casual), occasion_rules (bloqueada fuera de deporte/casual)
- ✅ `impermeable_deporte` (outerwear): constants, labels, inferencia, category_rules (bonus en deporte/lluvia, penalty en elegante/formal), occasion_rules (bloqueado en matrimonio/gala/cita elegante/nocturna elegante)

**`engine/compatibility.py`**
- ✅ Vestido elegante/cóctel penaliza calzado que no sea elegante/formal: zapato/botín sin estilo elegante → -22; bota sin estilo elegante → -28

**`engine/category_rules.py` — `one_piece_context_bonus`**
- ✅ Boost vestido_elegante/coctel cambiado de incondicional (+25) a condicional: `occasion_match AND mood_match → +25`; `occasion_match AND mood not in ["comodo","relajado"] → +12`

**`engine/occasion_rules.py`**
- ✅ Trabajo + enterito: bloqueado salvo `mood == "sexy"`
- ✅ Trabajo + short/falda corta: umbral temperatura según mood — `24°` si relajado/cómodo, `27°` si otros
- ✅ Salida nocturna + polar: bloqueado cuando `mood == "elegante"`
- ✅ `impermeable_deporte`: bloqueado en matrimonio/gala; bloqueado en cita/nocturna/trabajo con mood elegante/formal/sexy
- ✅ `polera_deporte`: bloqueada fuera de deporte/casual
- ✅ `jardinera`: bloqueada con lluvia y temp ≤ 13°; bloqueada en matrimonio/gala si dress_level relajado/flexible
- ✅ `ballarina`: bloqueada en deporte y actividad entrenar; bloqueada con temp ≤ 8° (advertencia suave)
- ✅ `zapatilla_deporte` + `mood == "elegante"`: bloqueada fuera de deporte

**`utils/garment_utils.py`**
- ✅ `is_shoe_ballet_flat(garment)` nueva función — detecta ballarina por subcategoría y keywords en nombre

**`app.py` — Galería de prendas**
- ✅ Filtro "☔ Solo impermeables" (`filter_waterproof`) en galería
- ✅ Filtro "⚠️ Con alertas" (`filter_issues`) en galería — muestra solo prendas con inconsistencias no ignoradas
- ✅ Ignored badges migrados de `st.session_state[f"issue_ignored_{g.id}"]` (efímero) a `st.session_state.ignored_badges` (set cargado desde Supabase)
- ✅ 7 widgets del formulario de edición corregidos (style, pattern, category, subcategory, warmth, dress_level, sexiness): removidos parámetros `index=`/`value=` conflictivos con session_state; inicialización con `if key not in st.session_state`

**`storage_cloud.py`**
- ✅ `load_ignored_badges_cloud(user_id)` y `add_ignored_badge_cloud(user_id, garment_id)` agregadas — persisten badges ignorados en tabla Supabase `ignored_badges`

---

## Pendiente para próximas sesiones

### Motor — matrimonio ✅ completado
- ✅ mood sexy — validado en todas las temperaturas (sesión actual)
- ✅ mood cómodo — lógica implementada, ajuste fino aceptado como suficiente
- ✅ Actividad "formal" — pospuesto, no prioritario
- ✅ generate_outfits_from_selected_garment matrimonio elegante — aceptable en flujo "Mostrar de todos modos"

### Motor (general)
- ✅ matrimonio — todos los moods completados
- ✅ Gala — implementada y validada (37 casos)
- 🎯 **PRÓXIMO: Rotación de categorías (bottom_usage + diversidad forzada genérica)**
- ⬜ Deporte — todos los moods y temperaturas
- ⬜ matrimonio+cómodo — ajuste fino de scores (queda como deuda menor, no bloquea gala)
- ⬜ Compatibilidad de colores — penalizar outfits con 4+ colores sin eje cromático claro. 
  Revisar compatibility.py
- ⬜ taco_bajo → permitido en mood cómodo, penalizado en relajado
- ⬜ taco_alto → penalizado en cómodo, bloqueado en relajado
- ⬜ Calzado plano de trabajo para calor
- ⬜ Mayor diversidad de tops en mood urbano
- ⬜ Planificador — polera sin midlayer con frío extremo
- ⬜ Chaleco cuello V — genera combinaciones incoherentes
- ⚠️ Cardigan/midlayer repetido en múltiples outfits — problema de rotación pendiente

### Clóset
- ⬜ Verificar top leopardo (63) — agregar tag urbano en secondary_styles si corresponde
- ⬜ Agregar sandalias, ballerinas y chalas al clóset (subcategoría ballarina ya implementada)
- ⬜ Más bottoms livianos para calor

### UI
- ⬜ Formulario editar prenda — scroll automático o inline en galería
- ⬜ Tip de pantys: mostrar máximo una vez por tanda
- ✅ Persistencia del "Ignorar" en badge de inconsistencias — implementado con tabla Supabase `ignored_badges`
- ⬜ Ocasiones frecuentes del perfil ordenadas primero en selectbox del recomendador
- ⬜ Botón eliminar directo en tarjeta de galería — pendiente migración a React
- ⬜ Destacar boton de "mi perfil" y "qué es Lookia"
- ⬜ Pruebas completas en Claude in Chrome — instalar extensión primero

### Técnico
- ⬜ Moderación de fotos — bloquear nudes/menores/contenido inapropiado en subida (urgente)
- ⬜ Refactor `generate_outfits_from_selected_garment` — ~430 líneas duplicadas con `generate_outfits`
- ⚠️ Import `outfit_score` dentro de loop en `_generate_matrimonio_elegante` (L162) — ya importado en top del archivo
- ⚠️ Riesgo de recursión infinita en `_generate_matrimonio_elegante` cuando no hay vestidos — revisar si `engine.recommender.generate_outfits` tiene el dispatch matrimonio+elegante
- ⬜ Push a version-sana después de pruebas completas
- ⬜ UI definitiva — migrar de Streamlit a React o similar
- ⬜ Dividir app.py en módulos por tab
- ⬜ Renombrar dress_level "flexible" a "intermedio" en refactor futuro

### Funcionalidades nuevas
- 🎯 **PRÓXIMO: `chaleco_vestir`** — nueva subcategoría para midlayer (chaleco de tela/elegante, no deporte). Diseño aprobado, implementación pendiente.
- ⬜ Rotación de categorías — `bottom_usage` y mecanismo de diversidad forzada genérica para bottom/midlayer/outerwear
- ⬜ Estadísticas en tab "Mi clóset" — ya implementado básico, expandir
- ⬜ Integración IA Anthropic (PRIORITARIO): moderación de fotos + inferencia de atributos desde imagen en una sola llamada a Claude Haiku
- ⬜ Ocasiones frecuentes del perfil usadas para ordenar opciones en recomendador
- ⬜ Compatibilidad de colores — penalizar outfits con 4+ colores sin eje cromático claro