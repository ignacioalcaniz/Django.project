# 📈 QuantEdge

**QuantEdge** es una plataforma web desarrollada con **Django** orientada a la simulación y análisis de inversiones financieras. El proyecto integra autenticación de usuarios, gestión de activos bursátiles, dashboards analíticos, consultas asistidas por IA conceptual y herramientas de análisis para ofrecer una experiencia moderna de inversión.

Este proyecto fue desarrollado como aplicación académica con una arquitectura profesional, aplicando buenas prácticas de desarrollo Full Stack, organización modular y principios de escalabilidad.

---

# 🚀 Características principales

### 👤 Gestión de usuarios

- Registro de usuarios
- Inicio y cierre de sesión
- Dashboard privado protegido
- Perfil de usuario
- Sistema de permisos mediante Django Authentication

---

### 📊 Dashboard financiero

- Resumen ejecutivo del portfolio
- Valor total invertido
- Valor actual
- Ganancia/Pérdida
- Rentabilidad total
- Riesgo promedio
- Score promedio QuantEdge
- Activo más rentable

---

### 📈 Portfolio Analytics

Visualización mediante **Chart.js** de:

- Distribución del portfolio
- Rentabilidad por activo
- Score QuantEdge
- Indicadores financieros

---

### ⭐ Watchlist

Los usuarios pueden:

- Agregar activos favoritos
- Eliminarlos
- Consultar recomendaciones
- Acceder rápidamente al detalle de cada activo

---

### 💹 Mercado de activos

Listado dinámico de activos financieros con:

- Búsqueda en tiempo real mediante AJAX
- Filtros por recomendación
- Filtros por riesgo
- Actualización sin recargar la página

---

### 🤖 Asesoramiento IA (Conceptual)

Cada activo puede recibir un análisis conceptual basado en indicadores financieros simulados.

Incluye:

- Historial de consultas
- Detalle de análisis
- Puntaje QuantEdge
- Riesgo
- Recomendación

---

### ⚙️ Panel de administración avanzado

El panel administrativo fue personalizado utilizando Django Admin.

Incluye:

- CRUD completo de activos
- Búsqueda avanzada
- Filtros
- Exportación CSV
- Acciones masivas
- Página intermedia de confirmación para acciones administrativas
- Indicadores visuales
- Vista previa de imágenes
- Badges personalizados
- Panel completamente adaptado al dominio financiero

---

# ✨ Interfaz de usuario

El frontend incorpora:

- Diseño responsive
- Landing page moderna
- Dashboard profesional
- Animaciones GSAP
- ScrollTrigger
- Chart.js
- Bootstrap 5
- Sass
- CSS modular

---

# 🛠 Tecnologías utilizadas

## Backend

- Python
- Django
- MySQL / MariaDB
- Django ORM

## Frontend

- HTML5
- CSS3
- Sass
- Bootstrap 5
- JavaScript ES6
- AJAX

## Librerías

- GSAP
- ScrollTrigger
- Chart.js

---

# 📂 Arquitectura

```text
QuantEdge
│
├── contacto/
├── core/
├── usuarios/
├── vistaprevia/
│
├── templates/
│
├── static_dev/
│   ├── css/
│   ├── js/
│   ├── images/
│
├── media/
├── manage.py
└── requirements.txt
```

---

# 📌 Funcionalidades implementadas

- ✅ Registro de usuarios
- ✅ Login / Logout
- ✅ Dashboard privado
- ✅ Gestión de perfil
- ✅ CRUD de activos
- ✅ Compra simulada de activos
- ✅ Portfolio financiero
- ✅ Watchlist
- ✅ Historial IA
- ✅ Comparador de activos
- ✅ Ranking de activos
- ✅ Notificaciones
- ✅ Panel administrativo profesional
- ✅ Página administrativa intermedia
- ✅ Exportación CSV
- ✅ AJAX
- ✅ Chart.js
- ✅ GSAP
- ✅ ScrollTrigger
- ✅ Bootstrap
- ✅ Sass
- ✅ Responsive Design

---

# 🗄 Base de datos

El proyecto utiliza:

- MariaDB
- MySQL

gestionados mediante el ORM de Django.

---

# ▶ Instalación

Clonar el repositorio

```bash
git clone <repository-url>
```

Entrar al proyecto

```bash
cd QuantEdge
```

Crear entorno virtual

```bash
python -m venv .venv
```

Activarlo

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Instalar dependencias

```bash
pip install -r requirements.txt
```

Aplicar migraciones

```bash
python manage.py migrate
```

Ejecutar servidor

```bash
python manage.py runserver
```

---

# 📸 Capturas

Se recomienda incluir capturas de:

- Landing
- Dashboard
- Portfolio
- Watchlist
- Comparador
- Ranking
- Panel Administrativo

---

# 🎓 Objetivo del proyecto

Este proyecto fue desarrollado como trabajo integrador para la **Diplomatura en Desarrollo Web con Django**, aplicando buenas prácticas de arquitectura, desarrollo backend, interfaces modernas y administración avanzada mediante Django.

---

# 👨‍💻 Autor

**Ignacio Alcañiz**

Full Stack Developer

Python • Django • JavaScript • React • Angular • PHP • Laravel • MySQL • AWS