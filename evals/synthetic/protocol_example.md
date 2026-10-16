# Protocolo de adaptación de CV (ejemplo genérico para benchmarks)

Este protocolo es un ejemplo público y genérico. Reproduce la extensión y la estructura del
protocolo real del candidato, que es privado y nunca se versiona.

## 1. Objetivo

Adaptar el CV maestro a una oferta concreta para superar filtros ATS (Applicant Tracking
Systems) y la lectura rápida de un reclutador, **sin alterar la veracidad del CV**. La
adaptación consiste en elegir qué destacar, en qué orden y con qué palabras, usando solo
hechos que ya están en el CV maestro o que el candidato confirmó explícitamente.

## 2. Reglas de veracidad (no negociables)

1. Prohibido agregar herramientas, lenguajes, protocolos, certificaciones, cargos, empresas,
   fechas, cifras o logros que no estén en el CV maestro o en la lista de habilidades
   confirmadas por el candidato.
2. Se permite reformular una experiencia existente con el vocabulario de la oferta solo si el
   significado técnico es equivalente. Ejemplo válido: "publicación de telemetría vía MQTT"
   puede describirse como "integración de datos de sensores mediante MQTT". Ejemplo inválido:
   convertir "registro de mediciones de vibración" en "experto en análisis de vibraciones ISO".
3. Las brechas (lo que la oferta pide y el CV no tiene) se informan **fuera** del CV, en la
   lista de brechas. Nunca se mencionan dentro del CV, ni siquiera en forma negativa
   ("sin experiencia en...", "no cuenta con..."), porque perjudican al candidato.
4. Si una palabra clave de la oferta no puede respaldarse, no se usa.
5. No se inventan porcentajes de mejora, tamaños de equipo ni montos.

## 3. Palabras clave y ATS

- Identificar entre 8 y 15 palabras clave críticas de la oferta (tecnologías, normas,
  metodologías, tipo de industria).
- Para cada palabra clave, indicar si el CV la respalda. Solo las respaldadas pueden
  aparecer en el CV adaptado.
- Usar la forma exacta en que la oferta escribe el término cuando sea equivalente (por
  ejemplo "C/C++" en lugar de "C y C++"), porque los ATS hacen coincidencias literales.
- Priorizar las palabras clave en el resumen profesional y en las primeras viñetas de la
  experiencia más reciente.

## 4. Estructura y formato LaTeX

- Mantener exactamente los comandos del CV maestro (`\resumeItem`, `\resumeSubheading`,
  `\resumeProjectHeading`, entornos `itemize`) para que el documento compile sin cambios.
- Entregar cada sección modificada completa, lista para copiar y pegar, sin puntos
  suspensivos ni recortes.
- Entregar cada sección en un bloque independiente.
- El CV compilado no debe superar una página A4: preferir viñetas de una línea, eliminar
  adjetivos vacíos y reordenar antes que agregar.
- Los títulos de proyectos deben ser cortos (máximo ~75 caracteres) para no desplazar la
  fecha de la columna derecha.
- Escapar caracteres especiales de LaTeX (&, %, $, #, _).

## 5. Cálculo de ajuste

- `match_before`: porcentaje estimado de ajuste del CV maestro frente a la oferta.
- `match_after`: porcentaje estimado tras la adaptación. Debe ser mayor o igual que
  `match_before`, pero el aumento solo puede venir de mejor visibilidad de hechos
  existentes, nunca de requisitos agregados.
- Si la oferta exige requisitos excluyentes que el CV no cubre, el ajuste no debe superar
  60 % aunque el resto calce.

## 6. Prioridades por tipo de cargo

| Tipo de cargo | Qué destacar primero |
|---|---|
| Automatización / control | Lazos de control, instrumentación, protocolos industriales, puesta en marcha |
| Embebidos / IoT | Microcontroladores, RTOS, buses (I2C, SPI, UART, CAN), comunicaciones, PCB |
| Datos / IA aplicada | Python, análisis de datos, modelos, despliegue, contenedores, APIs |
| Confiabilidad / mantenimiento | Monitoreo de condición, análisis de fallas, tendencias, reportes |
| Proyectos de ingeniería | Especificaciones, documentación técnica, coordinación, normativa |

## 7. Salida esperada

Un objeto JSON con:

- `match_before`, `match_after`: enteros entre 0 y 100.
- `keywords`: palabras clave críticas de la oferta (respaldadas o no).
- `sections`: lista de secciones LaTeX completas (`name`, `latex`).
- `gaps`: requisitos de la oferta que el CV no respalda, redactados de forma breve para que
  el candidato decida si los maneja y desea confirmarlos con evidencia.

## 8. Errores frecuentes a evitar

- Copiar la descripción de la oferta dentro del CV.
- Agregar una sección de "habilidades en aprendizaje" con tecnologías no respaldadas.
- Mencionar brechas dentro del CV.
- Cambiar fechas o nombres de instituciones.
- Superar una página por agregar viñetas en lugar de reordenarlas.
- Usar siglas sin expandir la primera vez cuando la oferta usa el nombre completo.
