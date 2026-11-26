# Diseño de Modelo Conceptual (UML)
## Plataforma Colaborativa de Preguntas y Respuestas (Q&A)
**Materia:** Ingeniería de Software I · **AÑO:** 2026 · **Integrantes:** Gagliardo Brunella, Gonzalez Karina, Urbano Alturria Priscila.
> El repositorio contiene el diagrama de clases UML.
-----
## Objetivo 
Modelar una plataforma de preguntas y respuestas destinada a estudiantes. Utilizando el diseño orientado a objetos, y aplicando patrones de diseño para lograr el mejor modelado posible.

## Requerimientos funcionales

- [x] **Usuarios y autenticación:** registro con email y contraseña, con roles asignados (Admin, Usuario general).
- [x] **Preguntas:** título, cuerpo detallado, fecha de publicación, una categoría obligatoria y múltiples tags.
- [x] **Respuestas y autoría:** múltiples respuestas por pregunta. El autor puede ser un usuario o un agente automático.
- [x] **Agente LLM:** genera respuestas automáticas asistidas por IA para preguntas que incluyan una etiqueta.

## Seguridad de credenciales

- Las contraseñas se almacenan únicamente como hash `scrypt` (`password_hash`); nunca se guardan ni se escriben en logs en texto plano.
- Toda contraseña debe tener al menos 8 caracteres. La validación es compartida por el comando `create-admin` y el modelo `User`.
- La aplicación exige HTTPS: redirecciona HTTP con `308`, envía la cabecera `Strict-Transport-Security` y marca las cookies de sesión como `Secure`.
- Variables de entorno: `FORCE_HTTPS` (por defecto `1`), `HSTS_MAX_AGE` (por defecto `31536000`) y `TRUST_PROXY` (activar solo detrás de un proxy que termine TLS y envíe `X-Forwarded-Proto`).

## Decisiones de diseño
### 1. Patrón Strategy 
- Elegimos el patrón Strategy porque las respuestas automáticas pueden ser generadas por distintos *Proveedores de LLM*. 
- Definimos la interfaz StrategyLLM con un método generate(prompt : String) : String, el cual es implementado por las estrategias concretas OpenAIStrategy, GeminiStrategy y LocalModelStrategy y lo redefinen según su propia implementación.
- Automatic Agent actúa como contexto, ya que mantiene una referencia directa hacia la interfaz y delega en ella la responsabilidad de la generación del texto, sin depender de ninguna estrategia concreta.
- Así, agregar un nuevo proveedor automático no requiere generar cambios en las demás clases, sino crear una nueva estrategia concreta, esto mantiene el sistema extensible y desacoplado.
