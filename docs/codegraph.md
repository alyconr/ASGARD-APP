# CodeGraph Usage Policy

Este proyecto tiene CodeGraph inicializado y disponible vía MCP.

## Regla principal
Usar `codegraph_explore` como herramienta principal para exploración y comprensión estructural del código.

## Reglas operativas
1. No releer archivos completos si `codegraph_explore` ya devolvió el fragmento fuente necesario.
2. Usar lectura convencional (`grep`, `glob`, `read`) solo cuando:
   - el archivo esté listado como relevante adicional,
   - el resultado de CodeGraph sea insuficiente,
   - o se necesite validar detalle no devuelto por el grafo.
3. Priorizar navegación por relaciones semánticas:
   - definiciones
   - referencias
   - llamadas
   - imports
   - dependencias
4. Reservar el contexto del modelo para razonamiento sobre fragmentos ya recuperados, no para exploración manual repetitiva.
5. Si CodeGraph no encuentra resultados suficientes, declarar esa limitación explícitamente antes de caer a escaneo convencional.

## Objetivo
Reducir escaneo redundante de archivos, minimizar llamadas de herramientas y favorecer razonamiento guiado por el grafo semántico.