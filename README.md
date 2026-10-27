# LSBWebb — Sistema Web de Traducción de Lenguaje de Señas

Proyecto de Sistemas I · Net Bean · Gestión 2 – 2026

Aplicación web para la enseñanza del Lenguaje de Señas Boliviano (LSB) con paneles diferenciados por rol (Estudiante, Profesor, Administrador).

## Instalación rápida

```bash
git clone [https://github.com/loliters/LSB---Netbean.git](https://github.com/loliters/LSB---Netbean.git)
cd LSBWebb
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # completar credenciales
python manage.py migrate
python manage.py loaddata fixtures/catalogos.json
python manage.py createsuperuser
python manage.py runserver