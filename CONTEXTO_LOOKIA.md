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
3. **➕ Agregar prenda** — Formulario con inferencia automática de atributos
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
- ✅ Ajustes manuales de clima activados (sensibilidad térmica, interior/exterior, cielo)
- ✅ Interior + frío: fuerza al menos 1 outfit sin outerwear
- ✅ 24-25°C: mantiene opción de midlayer liviana
- ✅ `generate_outfits_from_selected_garment` reescrita para igualar lógica de `generate_outfits`
- ✅ Filtro `is_too_similar` relajado para evitar congelamiento en tanda 3
- ✅ Gorro/beanie bloqueado en gala y matrimonio

### Advertencias de prenda forzada
- ✅ Mini sexy (sexiness >= 3) en trabajo → advertencia + "Mostrar de todos modos"
- ✅ Outerwear con calor (>= 24°C) → advertencia + "Mostrar de todos modos"

### UI
- ✅ Score eliminado de la UI (reemplazado por modo debug con toggle)
- ✅ Explicaciones de outfits con más variedad de lenguaje y tono (usando random)
- ✅ Explicaciones mostradas en texto normal con separadores `|`
- ✅ Expander "Ajuste manual opcional" siempre cerrado al inicio (`expanded=False`)
- ✅ "No hay prendas suficientes" solo aparece si ya se generó
- ✅ Tip de pantys solo aparece si ya se generó y hay falda + frío/lluvia
- ✅ `CATEGORY_LABELS_ES` duplicado eliminado de `app.py`

---

## Cambios realizados (sesión 2 — abril 2026)

### Motor — penalizaciones y bloqueos
- ✅ Tacos penalizados con lluvia (+35 en `practicality_penalty`)
- ✅ Tacos penalizados en mood cómodo (+50 en `practicality_penalty`)
- ✅ `practicality_penalty` recibe `mood` como parámetro opcional
- ✅ Vestido elegante bloqueado en trabajo + mood cómodo (`occasion_rules.py`)
- ✅ Pantalón buzo bloqueado en cita (salvo mood urbano) (`occasion_rules.py`)
- ✅ Zapatillas deporte bloqueadas en cita (salvo mood urbano) (`occasion_rules.py`)
- ✅ Mini/short bloqueados con temp <= 9° (`occasion_rules.py`)
- ✅ `garment_allowed_for_occasion` recibe `mood` y `temp` como parámetros opcionales
- ✅ Llamadas actualizadas en `recommender.py` para pasar `mood` y `temp`
- ✅ `occasion_rules.py` reordenado por ocasión con comentarios claros

### UI
- ✅ Tip de pantys extendido a short con frío/lluvia (`app.py`)

### Pruebas realizadas
- ✅ Trabajo + sexy (frío, lluvia, calor, 24-25°)
- ✅ Trabajo + cómodo (frío, lluvia, calor, 24-25°)
- ✅ Cita + relajado (frío parcial)

---

## Pendiente para próximas sesiones

### PRIORITARIO — Subcategorías
Necesidad identificada en pruebas. Afecta múltiples archivos:
- `constants.py` — ampliar SUBCATEGORY_OPTIONS
- `models.py` — ya tiene campo subcategory
- `occasion_rules.py` — usar subcategoría en lugar de detectar por nombre
- `garment_utils.py` — actualizar detectores
- `scoring_components.py` — reglas por subcategoría
- `app.py` — formulario de agregar/editar prenda
- `attribute_inference.py` — inferencia automática de subcategoría

Subcategorías prioritarias a implementar:
- **bottom**: falda_corta, falda_midi, falda_larga, short_casual, short_elegante
- **shoes**: taco_bajo, taco_alto, zapatilla_urbana, zapatilla_deporte
- **one_piece**: vestido_casual, vestido_elegante, vestido_coctel

### Motor
- ⬜ Continuar pruebas cita (lluvia, calor, 24-25°) + todos los moods
- ⬜ Pruebas salida nocturna, casual, matrimonio, gala, deporte
- ⬜ Afinar compatibilidad de colores con evidencia de pruebas reales

### Funcionalidades nuevas
- ⬜ Estadísticas en tab "Mi clóset" (prendas más usadas, más gustadas, nunca usadas)
- ⬜ Perfil de usuario completo (ciudad, preferencias, onboarding)
- ⬜ Integración IA Anthropic:
  - Onboarding de prendas por foto (autocompletar atributos)
  - Explicaciones con personalidad generadas por IA
  - Modelo virtual: vestir figura con prendas del clóset
- ⬜ Login de usuario
- ⬜ Calzado plano de trabajo para calor (bailarina, sandalia formal) — clóset

### Técnico
- ⬜ Implementar subcategorías con Claude Code
- ⬜ Migrar a base de datos real (Supabase) para multi-usuario

### Pendiente de subcategorías (tacos)
- taco_bajo (kitten heel 3-5cm) → permitido en mood cómodo, penalizado en relajado
- taco_alto (stiletto 7cm+) → penalizado en cómodo, bloqueado en relajado

---

## Notas importantes
- La app usa archivos JSON locales — funciona para 1 usuaria, no escala sin refactor
- El perfil de usuario completo y la IA de Anthropic van juntos en una misma sesión futura
- Rama activa de desarrollo: **main** | Rama testers: **version sana**
- Al sugerir cambios de código: cada regla va en el archivo que corresponde según arquitectura