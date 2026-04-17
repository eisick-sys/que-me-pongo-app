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

---

## Notas técnicas importantes
- La app ya usa Supabase — JSON locales son legacy, no se leen en producción
- `wardrobe_images/` y `__pycache__/` no van al repositorio (están en `.gitignore`)
- Claude Code tiende a incluir .env en commits — siempre verificar antes del push
- El "Ignorar" de badges de advertencia en clóset solo persiste en session_state — al recargar vuelven a aparecer. Pendiente persistencia real en Supabase.
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

### Sesión 3 — abril 2026
**Subcategorías**
- ✅ bottom: `falda_corta`, `falda_midi`, `falda_larga`, `short_casual`, `short_elegante`
- ✅ one_piece: `vestido_casual`, `vestido_elegante`, `vestido_coctel`
- ✅ shoes: `zapatilla_urbana`, `zapatilla_deporte`, `taco_bajo`, `taco_alto`
- ✅ `SUBCATEGORY_LABELS_ES` con nombres en español
- ✅ `garment_utils.py` — detectores usan subcategory primero, nombre como fallback
- ✅ Nuevas funciones: `is_shoe_high_heel`, `is_shoe_low_heel`, `is_shoe_sport_sneaker`, `is_bottom_short`
- ✅ `attribute_inference.py` — inferencia específica antes que genérica, "stiletto" agregado
- ✅ 46+ prendas migradas con subcategoría correcta en `closet.json`

**Motor — variedad outerwear**
- ✅ Penalización de outerwear entre tandas aumentada de 10 a 24
- ✅ Control dinámico `max_same_outerwear` según cantidad de impermeables
- ✅ `weather_score` — outerwear impermeable retorna 15 con lluvia

---

### Sesión 4 — abril 2026
**UI — Subida múltiple de fotos**
- ✅ Nueva sección "📸 Agregar fotos" en tab ➕ Agregar prenda
- ✅ Subida de hasta 5 fotos a la vez (jpg, jpeg, png, webp)
- ✅ Atributos inferidos automáticamente desde nombre del archivo
- ✅ Resumen de prendas agregadas al terminar
- ✅ Formulario individual conservado como "➕ Agregar prenda manualmente"
- ✅ Formulario individual actualizado para aceptar webp también

**UI — Badge "Nueva"**
- ✅ `models.py` — campo `is_new: bool = False` agregado a Garment
- ✅ `storage.py` — carga `is_new` desde JSON (default False para prendas existentes)
- ✅ Prendas nuevas se guardan con `is_new=True`
- ✅ Badge "🆕 Nueva" visible en galería cuando `is_new=True`
- ✅ Al editar y guardar una prenda, `is_new` cambia a `False`

---

### Sesión 5 — abril 2026
**Motor — rotación de impermeables y garantía de 3 outfits**
- ✅ Bug resuelto: impermeables ya rotan con lluvia
- ✅ `scoring_components.py` — `weather_score` diferencia impermeables por warmth según temperatura
- ✅ `outfit_generation.py` — shuffle aleatorio de impermeables antes del slice [:4]
- ✅ `outfit_generation.py` — segunda pasada que relaja `is_too_similar` para garantizar 3 outfits
- ✅ Prints de debug eliminados

**Fixes varios**
- ✅ Color "verde oliva" eliminado — queda solo "verde olivo"
- ✅ COLOR_ALIASES corregido
- ✅ Formulario de accesorios: subcategoría oculta cuando categoría es "accessory"
- ✅ Subcategorías buzo/jogger agregadas a bottom
- ✅ 2 prendas migradas en closet.json con subcategoría buzo/jogger correcta

---

### Sesión 6 — abril 2026

**Bugs resueltos**
- ✅ **Tab 2 edición** — `st.selectbox` de patrón sin key y slider sexiness con key fija impedían editar prendas. Fix: `key=f"edit_pattern_{garment.id}"` y `key=f"edit_sexiness_{garment.id}"`
- ✅ **Tab 3 agregar** — atributos inferidos se sobreescribían en cada re-render. Fix: bandera `form_inferred_done` en session_state, se resetea al guardar
- ✅ **2 outfits con lluvia** — fallback de segunda pasada no respetaba `max_same_outerwear`. Fix: eliminar esa restricción en el fallback
- ✅ **Repetición de outerwear en tanda** — fallback tampoco respetaba `max_same_outerwear` en loop principal. Fix: agregar check faltante
- ✅ **Git** — merge de commit perdido `6f72a0f` (mejoras motor sesión anterior) incorporado a main. main y version-sana sincronizadas.

**Motor — mejoras**
- ✅ `max_accessory_outfits` aleatorio por tanda: `random.choice([1, 1, 2])` — accesorios en 1 o 2 outfits por tanda, nunca en los 3 (salvo matrimonio/gala)
- ✅ Boost colores vivos y prints en mood urbano (+4 animal_print/estampado/grafico, +3 colores vivos) en `mood_bonus`
- ✅ Bonus vestido_elegante/vestido_coctel en cita y salida nocturna (+25/+20) en `category_rules.py`
- ✅ Penalización calzado informal con vestido elegante (-30 mocasín/zapatilla/botín) en `compatibility.py`
- ✅ Boost calzado elegante en cita/salida nocturna (+35 taco_alto/taco_bajo/sandalia, -20 mocasín) en `category_rules.py`
- ✅ `max_same_shoes = 1` en cita/salida nocturna cuando hay 2+ zapatos elegantes — mejor rotación de tacos
- ✅ Penalización 4+ colores distintos en outfit (+35 en ocasiones elegantes, +20 resto) en `coherence_penalty`
- ✅ Bloqueo impermeables sport (dress_level relajado/flexible + style sport) en cita/salida nocturna/trabajo elegante y matrimonio/gala
- ✅ `generate_outfits_from_selected_garment` — propagación correcta de `mood` y `temp` al check de prendas del combo

**UI — mejoras**
- ✅ Mensaje informativo cuando se generan menos de 3 outfits
- ✅ Función `detect_garment_issues()` — detecta inconsistencias en atributos de prendas
- ✅ Badge ⚠️ en tarjetas de galería para prendas con posibles inconsistencias
- ✅ Botones "Ignorar" y "✏️ Revisar" en cada badge (ignorar persiste solo en session_state)
- ✅ Inconsistencias detectadas: taco con dress_level relajado, zapatilla deporte formal, mocasín sport, impermeable sport en ocasiones elegantes, buzo/jogger formal, short/mini warmth frío, top liviano warmth frío, prenda abrigada warmth caluroso, "impermeable" en nombre sin waterproof activado

---

### Sesión 7 — abril 2026

**Motor — ajustes de scoring con frío**
- ✅ Boost a jeans con temp <= 10°C según ocasión/mood (casual/salida nocturna: +10, cita/trabajo mood relajado/urbano/cómodo: +8)
- ✅ Boost adicional a jeans +15 cuando temp <= 8°C
- ✅ Penalización faldas midi/larga con temp <= 8°C: +35
- ✅ Penalización pantalón por warmth con temp <= 8°C: caluroso +25, medio +12, frío -15
- ✅ Penalización mocasín con lluvia: +60
- ✅ Boost outerwear abrigado (parka/chaqueta warmth frío) en salida nocturna mood relajado temp <= 8°C: -20

**Motor — reglas de ocasión**
- ✅ Outerwear sport permitido en salida nocturna con mood relajado
- ✅ Outerwear sport permitido en cita con mood relajado
- ✅ Bloqueo sport en salida nocturna y cita evalúa solo style principal (no secondary_styles)
- ✅ Vestido elegante/cóctel bloqueado con mood relajado (todas las ocasiones excepto deporte)
- ✅ Outerwear required cuando temp <= 8°C en todas las ocasiones excepto gala/matrimonio/deporte

**Motor — generación de outfits**
- ✅ Bug resuelto: waterproof-first solo aplica con lluvia, sin lluvia ordena por score puro
- ✅ outer_limit subido de 2 a 3 para más variedad de outerwear
- ✅ max_same_outerwear = 1 sin lluvia para forzar rotación de outerwear por score
- ✅ is_too_similar: outfits con outerwear distinto nunca se consideran demasiado similares
- ✅ Tercera pasada del fallback con umbral mínimo de score (35% del primer outfit)
- ✅ Bug resuelto: 3 outfits garantizados con lluvia — tercera pasada relaja max_same_outerwear
- ✅ Penalización impermeables (subcategory parka/impermeable) sin lluvia independiente del estilo
- ✅ Boost parkas con frío sin lluvia en salida nocturna mood relajado

**Motor — generación con prenda forzada**
- ✅ `generate_outfits_from_selected_garment` respeta `required_categories` (outerwear incluido con lluvia y frío extremo)
- ✅ Penalización +80 vestido elegante/cóctel con mood relajado (en vez de bloqueo duro)

**Motor — calzado y ocasión**
- ✅ `garment_allowed_for_occasion` recibe `mood` y `temp` en todas las llamadas (`app.py`, `recommender.py`)
- ✅ Zapatilla urbana permitida en salida nocturna con mood relajado/cómodo
- ✅ Boost zapatilla urbana salida nocturna mood relajado/cómodo con calor
- ✅ Penalización taco_alto con temp >= 26°C: +20
- ✅ Penalización taco_alto/bajo en salida nocturna mood relajado: +35/+15
- ✅ Penalización mocasín en salida nocturna: relajado/cómodo +45, urbano/elegante/sexy +55

**Fixes de datos**
- ✅ __pycache__/ y wardrobe_images/ agregados a .gitignore

**Pendiente para próximas sesiones**
- ⬜ Pruebas: salida nocturna moods urbano, elegante, sexy, cómodo
- ⬜ Pruebas: salida nocturna con lluvia todos los moods
- ⬜ Pruebas: salida nocturna calor (24-25°C)
- ⬜ Pruebas: matrimonio, gala, deporte
- ⬜ taco_bajo permitido en mood cómodo, penalizado en relajado
- ⬜ taco_alto penalizado en cómodo, bloqueado en relajado
- ⬜ Mayor diversidad de tops en mood urbano

---

### Sesión 8 — abril 2026

**Motor — reglas de ocasión**
- ✅ Zapatilla urbana permitida en salida nocturna con mood urbano (agregado a relajado/cómodo)
- ✅ Buzo/jogger bloqueado en salida nocturna
- ✅ `garment_allowed_for_occasion` recibe mood y temp en `app.py` línea 875 (fix)

**Motor — scoring**
- ✅ Vestido elegante/cóctel penalizado en `garment_base_score` con mood relajado/urbano: -150
- ✅ Boost animal_print/estampado/grafico/floral en mood urbano: +4 → +15
- ✅ Tacos penalizados en salida nocturna mood urbano: taco_alto +35, taco_bajo +20
- ✅ Zapatilla urbana boosteada en salida nocturna mood urbano: -50

**Motor — generación de outfits**
- ✅ Umbral fallback tercera pasada calculado contra mejor score global (no solo tercera pasada)
- ✅ Umbral solo aplica cuando hay 2+ outfits aceptados — garantiza siempre 3 outfits

**Datos — closet.json**
- ✅ Abrigo leopardo (83): agregado tag secundario "urbano" en `secondary_styles`
- ⬜ Top leopardo (63): revisar si necesita tag "urbano" en `secondary_styles`

**Pruebas completadas**
- ✅ Salida nocturna · relajado · frío (6°C) sin lluvia
- ✅ Salida nocturna · relajado · frío (6°C) con lluvia
- ✅ Salida nocturna · relajado · calor (28-29°C)
- ✅ Salida nocturna · relajado · umbral (24-25°C)
- ✅ Salida nocturna · urbano · frío (5°C)

---

### Sesión 10 — abril 2026

**Migración a Supabase**
- ✅ `supabase_client.py` — cliente Supabase con `get_supabase()` y `get_supabase_for_user(access_token)`
- ✅ `storage_cloud.py` — CRUD completo: prendas, feedback, outfits usados, imágenes (Storage)
- ✅ `auth_ui.py` — pantalla de login/registro/logout con Supabase Auth
- ✅ `app.py` — migrado: imports, auth guard, carga de datos, guardado de prendas/feedback/outfits
- ✅ `migrate_local_data.py` — script de migración one-shot (JSON local → Supabase, usa service_role key)
- ✅ Datos migrados: 60 prendas, 65 feedbacks, 21 outfits usados bajo user_id `27f1ddde-...`
- ✅ `upload_garment_image` recibe `access_token` para pasar RLS de Storage
- ✅ `render_garment_image` recibe `user_id` como parámetro explícito
- ✅ Imagen actual en edición migrada de disco local a URL de Supabase Storage
- ✅ `requirements.txt` agrega `supabase`

**UI**
- ✅ Botón cerrar sesión discreto en sidebar (`type="tertiary"`)
- ✅ Feedback 👍/👎 usa `st.toast()` con patrón `pending_toast` en session_state (persiste a través de reruns)
- ✅ Toggle "Modo debug" oculto cuando `LOOKIA_ENV=production`
- ✅ Filtro "🆕 Nuevas" en Mi clóset — filtra prendas con `is_new=True`
- ✅ Límite 5 fotos en subida múltiple — oculta uploader si ya hay 5+ prendas con imagen

**Ramas**
- ✅ `version-sana` sincronizada con `main` (fast-forward)
- ✅ `LOOKIA_ENV=production` configurado en Secrets de Streamlit Cloud (rama version-sana)

---

### Sesión 9 — abril 2026

**Motor — scoring**
- ✅ Penalización zapatilla urbana con lluvia en salida nocturna mood urbano: +15 color oscuro, +30 color claro (no aplica si waterproof=True)
- ✅ Reducción 90% de penalización warmth outerwear "medio" cuando hay midlayer warmth "frio" en el outfit
- ✅ Umbral bloqueo shorts/mini subido de temp <= 10 a temp <= 13 (general) y temp <= 15 para salida nocturna y cita

**UI**
- ✅ Botón "Mostrar de todos modos" aparece siempre que hay prenda seleccionada, bypasea todos los bloqueos de garment_allowed_for_occasion sin excepción

**Datos**
- ✅ Trench (ID 102): dress_level cambiado de "flexible" a "arreglado"
- ✅ version-sana sincronizada con main

**Pendiente para próximas sesiones**
- ⬜ Verificar que el trench aparece en salida nocturna elegante con los cambios aplicados
- ⬜ Renombrar dress_level "flexible" a "intermedio" en refactor futuro (Supabase)
- ⬜ Continuar pruebas: salida nocturna moods sexy y cómodo
- ⬜ Matrimonio, gala, deporte

---

### Sesión 12 — abril 2026

**Perfil de usuario**
- ✅ Tabla `user_profiles` creada en Supabase (user_id, display_name, closet_type, city, frequent_occasions, dominant_style, created_at, updated_at) con RLS habilitado
- ✅ `models.py` — dataclass `UserProfile` agregada
- ✅ `storage_cloud.py` — funciones `load_user_profile_cloud` y `save_user_profile_cloud`
- ✅ `app.py` — onboarding de primera vez (pantalla bloqueante con formulario)
- ✅ `app.py` — botón ⚙️ Mi perfil en sidebar, panel con formulario de edición y botón cancelar
- ✅ Ciudad usa `st.selectbox` con lista `CHILEAN_CITIES` (50 ciudades chilenas) en vez de text_input
- ✅ `CHILEAN_CITIES` agregada a `constants.py`
- ✅ Estilo dominante corregido — lista incluye "formal": ["casual", "formal", "elegante", "urbano", "sport", "mixto"]
- ✅ DEFAULT_CITY reemplazado por `st.session_state.user_profile.city` para clima real

**Fixes**
- ✅ `is_new` al editar — el update llega correctamente a Supabase (estaba funcionando, datos legacy tenían is_new=true)
- ✅ SQL de limpieza ejecutado en Supabase para poner is_new=false en prendas existentes
- ✅ Wardrobe vacío al re-login — fix con flag `just_logged_in` en session_state y auth_ui.py

**Limpieza y reorganización**
- ✅ Archivos legacy eliminados: `storage.py`, `closet.json`, `closet.json.bak`, `feedback.json`, `feedback.json.bak`, `used_outfits.json`, `used_outfits.json.bak`, `migrate_local_data.py`
- ✅ Helpers movidos de `engine/` a `utils/`: `history_utils.py`, `user_profile.py`, `selection_utils.py`
- ✅ Imports actualizados en `recommender.py` y `outfit_generation.py`

**Motor**
- ✅ Penalización jeans con calor: temp >= 30° → +80, temp >= 28° → +50, temp >= 24° → +20
- ✅ Campos irrelevantes ocultos en formularios agregar/editar para accesorios no térmicos (warmth, waterproof, sexiness ocultos cuando category=accessory y subcategory no está en THERMAL_ACCESSORIES)

---

## Pendiente para próximas sesiones

### Pruebas pendientes
- ⬜ Salida nocturna · moods: elegante, sexy, cómodo
- ⬜ Salida nocturna · lluvia con todos los moods
- ⬜ Matrimonio y gala
- ⬜ Deporte
- ⬜ Planificador semanal — polera sin midlayer con frío (bug detectado)

### Motor
- ⬜ Refactor `generate_outfits_from_selected_garment` — alinear lógica completa con `generate_outfits`
- ⬜ taco_bajo → permitido en mood cómodo, penalizado en relajado
- ⬜ taco_alto → penalizado en cómodo, bloqueado en relajado
- ⬜ Calzado plano de trabajo para calor
- ⬜ Mayor diversidad de tops en mood urbano
- ⬜ Planificador — polera sin midlayer con frío extremo

### Clóset
- ⬜ Verificar top leopardo (63) — agregar tag urbano en secondary_styles si corresponde
- ⬜ Agregar sandalias, ballerinas y chalas al clóset
- ⬜ Más bottoms livianos para calor (pantalones de tela, faldas) — motor limitado por clóset

### UI
- ⬜ Formulario editar prenda — scroll automático o inline en galería (pendiente UI definitiva)
- ⬜ Tip de pantys: mostrar máximo una vez por tanda
- ⬜ Persistencia del "Ignorar" en badge de inconsistencias (pendiente Supabase)
- ⬜ Ocasiones frecuentes del perfil ordenadas primero en selectbox del recomendador

### Técnico
- ⬜ **Moderación de fotos** — bloquear nudes/menores/contenido inapropiado en subida (urgente)
- ⬜ **UI definitiva** — migrar de Streamlit a React o similar
- ⬜ Dividir app.py en módulos por tab (pendiente para cuando esté más estable)
- ⬜ Renombrar dress_level "flexible" a "intermedio" en refactor futuro

### Funcionalidades nuevas
- ⬜ Estadísticas en tab "Mi clóset"
- ⬜ Perfil de usuario completo (foto, preferencias avanzadas)
- ⬜ Detección de color automática con Pillow al subir foto
- ⬛ **INTEGRACIÓN IA ANTHROPIC (PRIORITARIO — implementar al terminar de pulir el motor)**
  - Moderación de fotos en subida (nudes, menores, contenido inapropiado) — urgente para más testers
  - Inferencia de atributos desde imagen (categoría, color, subcategoría, patrón, estilo, warmth)
  - Ambas funciones en una sola llamada a Claude Haiku — costo ~$0.002 por foto
  - Reemplaza inferencia actual por nombre que es muy limitada
- ⬜ Ocasiones frecuentes del perfil usadas para ordenar opciones en recomendador


### Sesión 11 — abril 2026

**Infraestructura**
- ✅ `supabase_client.py` — agregado `load_dotenv()` y eliminada anon key hardcodeada
- ✅ SUPABASE_KEY actualizada en `.env`, Streamlit Cloud (main y version-sana)
- ✅ `gotrue` bajado a versión 1.3.0 para compatibilidad con Python 3.14
- ✅ Contraseña de usuario reseteada via SQL directo en Supabase

**UI — Agregar prenda**
- ✅ Límite de 5 fotos corregido — aplica a tanda de subida, no al clóset total
- ✅ Campo "Tipo de accesorio" eliminado de formularios agregar y editar — reemplazado por subcategoría
- ✅ Subcategoría ahora se muestra también para accesorios

**Pendiente para próximas sesiones**
- ⬜ Pruebas salida nocturna: elegante, sexy, cómodo
- ⬜ Pruebas salida nocturna con lluvia todos los moods

---

### Sesión 13 — abril 2026

**Pruebas completadas — Salida nocturna**
- ✅ Elegante · frío (7°C) sin lluvia
- ✅ Elegante · frío (7°C) con lluvia
- ✅ Elegante · calor (28-29°C)
- ✅ Elegante · umbral (24-25°C)
- ✅ Sexy · frío (7°C) sin lluvia
- ✅ Sexy · frío (7°C) con lluvia
- ✅ Sexy · calor (28-29°C)
- ✅ Sexy · umbral (24-25°C)
- ✅ Cómodo · frío (7°C) sin lluvia
- ✅ Cómodo · frío (7°C) con lluvia
- ✅ Cómodo · calor (28-29°C)
- ✅ Cómodo · umbral (24-25°C)

**Motor — scoring_components.py**
- ✅ Jeans penalizados en mood elegante/sexy: relajado +85, flexible +40 (exento si sexiness > 0)
- ✅ Boost bottoms arreglados/elegantes en mood elegante/sexy: -50
- ✅ Boost vestido elegante/cóctel en salida nocturna mood elegante/sexy: -60
- ✅ Penalizaciones vestido elegante: calzado no formal +80, midlayer no blazer +70, outerwear no abrigo/trench +70, gorro +80
- ✅ Boost parka warmth frio en frío extremo mood relajado/cómodo: -10

**Motor — occasion_rules.py**
- ✅ Bloqueo sandalias temp <= 10°C
- ✅ Bloqueo sport en salida nocturna evalúa solo style principal (garment.style, no all_styles)
- ✅ Parka permitida en salida nocturna mood relajado y cómodo

**Motor — category_rules.py**
- ✅ Boost parka warmth frio ocasión salida nocturna mood relajado/cómodo temp <= 8°C: +10

**UI — app.py**
- ✅ Tip paraguas cuando outerwear no impermeable con lluvia
- ✅ Fix subcategoría en formulario edición: key dinámica con category para refrescar al cambiar categoría
- ✅ has_vestido_elegante movido fuera del loop for g in items en practicality_penalty

**Pendiente para próximas sesiones**
- ⬜ Chaleco cuello V — genera combinaciones incoherentes, revisar tags y penalizaciones
- ⬜ Continuar pruebas: matrimonio, gala, deporte
- ⬜ Planificador semanal — polera sin midlayer con frío (bug detectado)
- ⬜ Matrimonio, gala, deporte