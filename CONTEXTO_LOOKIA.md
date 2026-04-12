# CONTEXTO PROYECTO LOOKIA
> Pegar este archivo al inicio de cada sesión con Claude para retomar sin repetir contexto.

---

## ¿Qué es Lookia?
App de recomendación de outfits basada en personalidad, ocasión, mood, actividad y clima.
Desarrollada en Python + Streamlit. El usuario no es programador, aprendió con IA.

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
├── closet.json             # Clóset de la usuaria
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
2. **👕 Mi clóset** — Galería de prendas con edición
3. **➕ Agregar prenda** — Subida múltiple (hasta 5 fotos) + formulario individual
4. **📅 Planificador semanal** — Outfits para la semana evitando repetir prendas

---

## Orden de prioridad del motor
1. Ocasión
2. Clima
3. Mood
4. Actividad
5. Ajustes manuales

---

## Filosofía del motor
- El motor sugiere y advierte, pero la usuaria decide (botón "Mostrar de todos modos")
- Las recomendaciones son tan buenas como el clóset que las alimenta
- Flexibilidad sobre rigidez — nunca bloquear sin dar opción de forzar
- Cada cambio en su lugar — las reglas van en el archivo que corresponde según la arquitectura

---

## Cambios realizados (sesión 1 — abril 2026)

### Seguridad
- ✅ API key movida de `app.py` a `.env`
- ✅ `.gitignore` creado con `.env`
- ✅ Ciudad hardcodeada movida a `.env` como `LOOKIA_CITY`

### Motor
- ✅ Ajustes manuales de clima activados
- ✅ Interior + frío: fuerza al menos 1 outfit sin outerwear
- ✅ 24-25°C: mantiene opción de midlayer liviana
- ✅ `generate_outfits_from_selected_garment` reescrita para igualar lógica de `generate_outfits`
- ✅ Filtro `is_too_similar` relajado
- ✅ Gorro/beanie bloqueado en gala y matrimonio

### UI
- ✅ Score eliminado de la UI (reemplazado por modo debug con toggle)
- ✅ Explicaciones con más variedad de lenguaje
- ✅ Tip de pantys con falda + frío/lluvia

---

## Cambios realizados (sesión 2 — abril 2026)

### Motor
- ✅ Tacos penalizados con lluvia (+35) y mood cómodo (+50) en `practicality_penalty`
- ✅ `practicality_penalty` recibe `mood` como parámetro
- ✅ Vestido elegante bloqueado en trabajo + mood cómodo
- ✅ Pantalón buzo bloqueado en cita (salvo mood urbano)
- ✅ Zapatillas deporte bloqueadas en cita (salvo mood urbano)
- ✅ Mini/short bloqueados con temp <= 9°
- ✅ `garment_allowed_for_occasion` recibe `mood` y `temp`
- ✅ `occasion_rules.py` reordenado por ocasión

### UI
- ✅ Tip de pantys extendido a short con frío/lluvia

---

## Cambios realizados (sesión 3 — abril 2026)

### Subcategorías
- ✅ bottom: `falda_corta`, `falda_midi`, `falda_larga`, `short_casual`, `short_elegante`
- ✅ one_piece: `vestido_casual`, `vestido_elegante`, `vestido_coctel`
- ✅ shoes: `zapatilla_urbana`, `zapatilla_deporte`, `taco_bajo`, `taco_alto`
- ✅ `SUBCATEGORY_LABELS_ES` con nombres en español
- ✅ `garment_utils.py` — detectores usan subcategory primero, nombre como fallback
- ✅ Nuevas funciones: `is_shoe_high_heel`, `is_shoe_low_heel`, `is_shoe_sport_sneaker`, `is_bottom_short`
- ✅ `attribute_inference.py` — inferencia específica antes que genérica, "stiletto" agregado
- ✅ 46+ prendas migradas con subcategoría correcta en `closet.json`

### Motor — variedad outerwear (EN PROGRESO - NO SUBIR AÚN)
- ✅ Penalización de outerwear entre tandas aumentada de 10 a 24
- ✅ Control dinámico `max_same_outerwear` según cantidad de impermeables
- ✅ `weather_score` — outerwear impermeable retorna 15 con lluvia
- ⚠️ **BUG PENDIENTE**: impermeable negro no aparece en top_candidates con lluvia
  - Tiene warmth "frio", waterproof True, estilo casual
  - Debug muestra solo 2 impermeables (celeste y azul) en top_candidates
  - Causa desconocida — investigar qué filtro lo descarta
  - **NO hacer git push hasta resolver**

---

## Cambios realizados (sesión 4 — abril 2026)

### UI — Subida múltiple de fotos
- ✅ Nueva sección "📸 Agregar fotos" en tab ➕ Agregar prenda
- ✅ Subida de hasta 5 fotos a la vez (jpg, jpeg, png, webp)
- ✅ Atributos inferidos automáticamente desde nombre del archivo
- ✅ Resumen de prendas agregadas al terminar
- ✅ Formulario individual conservado como "➕ Agregar prenda manualmente"
- ✅ Formulario individual actualizado para aceptar webp también

### UI — Badge "Nueva"
- ✅ `models.py` — campo `is_new: bool = False` agregado a Garment
- ✅ `storage.py` — carga `is_new` desde JSON (default False para prendas existentes)
- ✅ Prendas nuevas (subida múltiple y formulario) se guardan con `is_new=True`
- ✅ Badge "🆕 Nueva" visible en galería "Mi clóset" cuando `is_new=True`
- ✅ Al editar y guardar una prenda, `is_new` cambia a `False`

---

## Pendiente para próximas sesiones

### INMEDIATO — Resolver bug outerwear
- Impermeable negro no aparece en top_candidates con lluvia
- Investigar qué filtro lo descarta antes de llegar a outfit_generation
- Una vez resuelto, hacer git push de todo lo pendiente

### Motor
- ⬜ Continuar pruebas cita (calor, 24-25°) + moods elegante, sexy, urbano, cómodo
- ⬜ Pruebas salida nocturna, casual, matrimonio, gala, deporte

### Subcategorías pendientes
- taco_bajo → permitido en mood cómodo, penalizado en relajado
- taco_alto → penalizado en cómodo, bloqueado en relajado

### Funcionalidades nuevas
- ⬜ Estadísticas en tab "Mi clóset"
- ⬜ Perfil de usuario completo
- ⬜ Integración IA Anthropic (foto → atributos, explicaciones con personalidad, modelo virtual)
- ⬜ Login de usuario
- ⬜ Calzado plano de trabajo para calor

### Técnico
- ⬜ Migrar a base de datos real (Supabase) para multi-usuario

---

## Notas importantes
- La app usa archivos JSON locales — funciona para 1 usuaria, no escala sin refactor
- Rama activa de desarrollo: **main** | Rama testers: **version sana**
- Claude Code tiende a incluir .env en commits — siempre verificar antes del push
- Comando para correr la app: `python -m streamlit run app.py`
- Retomar Claude Code: `claude --resume [session_id]` o simplemente `claude` en la carpeta
- Al sugerir cambios: cada regla va en el archivo que corresponde según arquitectura