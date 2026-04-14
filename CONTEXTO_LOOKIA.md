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
├── storage.py              # Guardar/cargar JSON con backup automático
├── weather.py              # Conexión OpenWeather (actual + pronóstico semanal)
├── requirements.txt        # streamlit, pillow, pandas, requests, python-dotenv
├── closet.json             # Clóset de la usuaria (~60 prendas)
├── feedback.json           # Historial de likes/dislikes
├── used_outfits.json       # Outfits realmente usados
├── .env                    # Variables de entorno (NO subir a GitHub)
├── .gitignore              # Incluye .env
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
- Rama activa de desarrollo: **main**
- Rama testers: **version-sana**
- Ambas ramas deben estar siempre sincronizadas (idénticas)
- Flujo correcto: desarrollar en main → al terminar sesión, actualizar version-sana igual a main
- Comando para correr la app: `python -m streamlit run app.py`
- Retomar Claude Code: `claude --resume [session_id]` o simplemente `claude` en la carpeta
- **SIEMPRE verificar que .env no esté en el commit antes de hacer push**

---

## Notas técnicas importantes
- La app usa archivos JSON locales — funciona para 1 usuaria, no escala sin refactor
- `wardrobe_images/` contiene fotos de prendas — no va al repositorio (agregar a .gitignore)
- `__pycache__/` tampoco va al repositorio (agregar a .gitignore)
- Claude Code tiende a incluir .env en commits — siempre verificar antes del push
- El "Ignorar" de badges de advertencia en clóset solo persiste en session_state (no en JSON) — al recargar vuelven a aparecer. Pendiente persistencia real cuando se migre a Supabase.

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

## Pendiente para próximas sesiones

### Pruebas pendientes
- ⬜ Salida nocturna moods urbano, elegante, sexy, cómodo
- ⬜ Salida nocturna con lluvia todos los moods
- ⬜ Salida nocturna calor (24-25°C)
- ⬜ Matrimonio y gala
- ⬜ Deporte
- ⬜ Seleccionar prenda específica en distintos escenarios

### Motor
- ⬜ Refactor `generate_outfits_from_selected_garment` — alinear lógica completa con `generate_outfits` (ocasión, mood, temp, required_categories, scoring completo)
- ⬜ taco_bajo → permitido en mood cómodo, penalizado en relajado
- ⬜ taco_alto → penalizado en cómodo, bloqueado en relajado
- ⬜ Calzado plano de trabajo para calor
- ⬜ Mayor diversidad de tops en mood urbano (ajuste fino)

### Clóset
- ⬜ Agregar sandalias, ballerinas y chalas al clóset

### UI
- ⬜ Botón "Mostrar de todos modos" cuando prenda forzada está bloqueada por mood (requiere cambio en app.py)
- ⬜ Tip de pantys: mostrar máximo una vez por tanda (pendiente UI definitiva)
- ⬜ Al hacer clic en "Revisar" prenda, scroll automático al formulario (pendiente UI definitiva)
- ⬜ Persistencia del "Ignorar" en badge de inconsistencias (pendiente Supabase)

### Funcionalidades nuevas
- ⬜ Estadísticas en tab "Mi clóset"
- ⬜ Perfil de usuario completo
- ⬜ Detección de color automática con Pillow al subir foto (antes de IA)
- ⬜ Integración IA Anthropic (foto → atributos, explicaciones con personalidad, modelo virtual)
- ⬜ Login de usuario

### Técnico — próximo gran paso
- ✅ `wardrobe_images/` y `__pycache__/` agregados a `.gitignore`
- ⬜ **Migrar a Supabase** — base de datos real para multi-usuario
- ⬜ **UI definitiva** (React o similar) — reemplazar Streamlit


