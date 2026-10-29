<div align="center">

<img src="docs/img/logo.svg" alt="Logo de Net Bean" width="110">

# Net Bean

**Aprende lengua de señas practicando con tu cámara.**<br>
Una red neuronal convolucional evalúa tu seña al instante y te dice cómo mejorarla.

[![CI](https://github.com/loliters/LSB---Netbean/actions/workflows/ci.yml/badge.svg)](https://github.com/loliters/LSB---Netbean/actions/workflows/ci.yml)
![Versión](https://img.shields.io/badge/versi%C3%B3n-1.0.0-1E5BB8)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-ORM%20%C2%B7%20Signals-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-3FN-4169E1?logo=postgresql&logoColor=white)
![TensorFlow Lite](https://img.shields.io/badge/TensorFlow%20Lite-EfficientNetB2-FF6F00?logo=tensorflow&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-HandLandmarker-0097A7)
[Funcionalidades](#-funcionalidades) · [Cómo funciona](#-cómo-funciona) · [Inicio rápido](#-inicio-rápido) · [Documentación](#-documentación) · [Equipo](#-equipo)

</div>

---

## 🤟 ¿Qué es Net Bean?

Sistema web de traducción de lenguaje de señas que funciona como **herramienta de enseñanza para personas oyentes**. El estudiante elige una seña, la hace frente a la cámara y el sistema responde con la letra o el número detectado, el porcentaje de coincidencia y orientación para corregir la postura. Cada acierto suma experiencia (XP), mantiene una racha diaria y desbloquea insignias.

Proyecto de **Proyecto de Sistemas I** · Universidad Privada del Valle · Ingeniería de Sistemas Informáticos · gestión 2-2026, desarrollado con la metodología **XP** (Extreme Programming).


## ✨ Funcionalidades

| Rol | Qué puede hacer |
|---|---|
| 🎓 **Estudiante** | Registrarse, iniciar sesión por correo y recuperar su contraseña · recorrer módulos (Alfabeto, Vocales, Números 1-5) · practicar con la cámara con retroalimentación guiada · ganar XP, racha, niveles e insignias · repasar sin XP las señas ya dominadas · ver su perfil y su avance |
| 👩‍🏫 **Profesor** | Elegir a qué estudiantes monitorea · **asignarles módulos, lecciones, letras o números** · ver su avance y quién lleva días sin practicar · gestionar el contenido · reportes en pantalla, Excel y PDF **solo de sus estudiantes** |
| 🛠️ **Administrador** | Gestionar usuarios (alta, edición y desactivación sin perder historial) · decidir qué estudiantes monitorea cada profesor · gestionar módulos, lecciones y señas con su imagen · ver métricas y reportes de todo el sistema |


## 🧠 Cómo funciona

```mermaid
flowchart LR
    subgraph P["Presentación"]
        N["Navegador<br/>cámara + JavaScript"]
    end
    subgraph L["Lógica · Django"]
        V["views"] --> S["services"]
        S --> G["signals"]
    end
    subgraph I["IA · carpeta ia/"]
        D["MediaPipe<br/>detecta la mano"] --> C["EfficientNetB2<br/>TFLite"]
    end
    subgraph DB["Datos"]
        PG[("PostgreSQL")]
    end
    N -- "fotograma (JSON)" --> V
    S -- "predecir" --> D
    S --> PG
    G --> PG
