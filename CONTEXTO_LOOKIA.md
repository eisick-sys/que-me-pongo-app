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

**Pendiente matrimonio urbano**
- ⬜ Pruebas con lluvia
- ⬜ Pruebas con calor (24-25°C)

---

## Pendiente para próximas sesiones

### Motor
- ⬜ Matrimonio urbano — pruebas pendientes: lluvia y calor (24-25°C)
- ⬜ Accesorios con vestidos en matrimonio — collar/aros no aparecen, investigar `accessory_relevance_penalty` y ranking
- ⬜ Diversidad de tops en matrimonio outfit 3 — blusa amarilla domina (pocos tops elegantes en clóset)
- ⬜ taco_bajo → permitido en mood cómodo, penalizado en relajado
- ⬜ taco_alto → penalizado en cómodo, bloqueado en relajado
- ⬜ Calzado plano de trabajo para calor
- ⬜ Mayor diversidad de tops en mood urbano
- ⬜ Planificador — polera sin midlayer con frío extremo
- ⬜ Chaleco cuello V — genera combinaciones incoherentes, revisar tags y penalizaciones
- ⬜ Pruebas pendientes: gala, deporte

### Clóset
- ⬜ Verificar top leopardo (63) — agregar tag urbano en secondary_styles si corresponde
- ⬜ Agregar sandalias, ballerinas y chalas al clóset
- ⬜ Más bottoms livianos para calor (pantalones de tela, faldas)
- ⬜ Más tops elegantes/formales para matrimonio (blusa amarilla domina por falta de opciones)

### UI
- ⬜ Formulario editar prenda — scroll automático o inline en galería
- ⬜ Tip de pantys: mostrar máximo una vez por tanda
- ⬜ Persistencia del "Ignorar" en badge de inconsistencias (pendiente Supabase)
- ⬜ Ocasiones frecuentes del perfil ordenadas primero en selectbox del recomendador

### Técnico
- ⬜ **Moderación de fotos** — bloquear nudes/menores/contenido inapropiado en subida (urgente)
- ⬜ **UI definitiva** — migrar de Streamlit a React o similar
- ⬜ Dividir app.py en módulos por tab
- ⬜ Renombrar dress_level "flexible" a "intermedio" en refactor futuro

### Funcionalidades nuevas
- ⬜ Estadísticas en tab "Mi clóset"
- ⬜ Perfil de usuario completo (foto, preferencias avanzadas)
- ⬜ Detección de color automática con Pillow al subir foto
- ⬛ **INTEGRACIÓN IA ANTHROPIC (PRIORITARIO)**
  - Moderación de fotos en subida (urgente para más testers)
  - Inferencia de atributos desde imagen (categoría, color, subcategoría, patrón, estilo, warmth)
  - Ambas funciones en una sola llamada a Claude Haiku — costo ~$0.002 por foto
  - Reemplaza inferencia actual por nombre que es muy limitada
- ⬜ Ocasiones frecuentes del perfil usadas para ordenar opciones en recomendador
